from __future__ import annotations

import json
import mimetypes
import subprocess
import threading
import traceback
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from .events import EventBuffer


class StudioRequestError(ValueError):
    pass


@dataclass
class StudioRun:
    run_id: str
    mode: str
    events: EventBuffer
    status: str = "queued"
    result: dict[str, Any] | None = None
    error: str | None = None
    artifacts: dict[str, Path] = field(default_factory=dict)

    def public(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "artifacts": {key: f"/api/runs/{self.run_id}/artifacts/{key}" for key in self.artifacts},
        }


class StudioService:
    def __init__(
        self,
        *,
        ui_root: str | Path,
        allowed_roots: list[str | Path] | None = None,
        sceneforge_runner: str | Path | None = None,
        sceneforge_data_directory: str | Path | None = None,
        builder_factory: Callable[[Path], Any] | None = None,
    ) -> None:
        self.ui_root = Path(ui_root).resolve()
        self.allowed_roots = [Path(item).resolve() for item in (allowed_roots or [Path.cwd()])]
        self.sceneforge_runner = Path(sceneforge_runner).resolve() if sceneforge_runner else None
        self.sceneforge_data_directory = Path(sceneforge_data_directory).resolve() if sceneforge_data_directory else None
        self.builder_factory = builder_factory or self._default_builder_factory
        self._runs: dict[str, StudioRun] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _default_builder_factory(root: Path) -> Any:
        from studio_builder import StudioBuilder

        return StudioBuilder(root)

    def resolve_allowed_root(self, value: str | Path) -> Path:
        candidate = Path(value).expanduser().resolve()
        for allowed in self.allowed_roots:
            try:
                candidate.relative_to(allowed)
                return candidate
            except ValueError:
                continue
        raise StudioRequestError(f"Workspace is outside configured roots: {candidate}")

    def get_run(self, run_id: str) -> StudioRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def create_run(self, request: dict[str, Any]) -> StudioRun:
        if not isinstance(request, dict):
            raise StudioRequestError("Request body must be an object")
        mode = request.get("mode")
        if mode not in {"builder_preview", "sceneforge"}:
            raise StudioRequestError("mode must be builder_preview or sceneforge")
        run_id = f"studio-{uuid4()}"
        run = StudioRun(run_id=run_id, mode=mode, events=EventBuffer(run_id))
        with self._lock:
            self._runs[run_id] = run
        target = self._run_builder if mode == "builder_preview" else self._run_sceneforge
        threading.Thread(target=target, args=(run, request), daemon=True).start()
        return run

    def _run_builder(self, run: StudioRun, request: dict[str, Any]) -> None:
        try:
            workspace = self.resolve_allowed_root(request.get("workspace_root", "."))
            plan = request.get("plan")
            if not isinstance(plan, dict):
                raise StudioRequestError("builder_preview requires a plan object")
            run.status = "running"
            run.events.emit(
                "run.accepted", "framing",
                "The builder request is inside the allowed workspace boundary.",
                progress=0.05, confidence=0.95,
                payload={"workspace_root": str(workspace), "plan_id": plan.get("plan_id")},
            )
            run.events.emit(
                "intent.interpreted", "planning",
                "The runtime will simulate the declared operations without mutating the workspace.",
                progress=0.18, confidence=0.98,
                payload={"operation_count": len(plan.get("operations", []))},
            )
            report = self.builder_factory(workspace).preview(plan)
            for index, operation in enumerate(report.get("operations", []), start=1):
                total = max(1, len(report.get("operations", [])))
                run.events.emit(
                    "operation.evaluated", "simulation",
                    f"Evaluated {operation.get('id', 'operation')} as {operation.get('type', 'unknown')}.",
                    progress=0.2 + 0.52 * (index / total), confidence=0.96, payload=operation,
                )
            run.result = report
            run.status = "completed"
            run.events.emit(
                "artifact.committed", "result",
                "The non-mutating builder receipt is ready for inspection.",
                progress=1.0, confidence=0.99,
                payload={"summary": report.get("summary", {}), "report": report},
            )
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)
            run.events.emit(
                "run.failed", "failure", str(exc), progress=1.0, confidence=1.0,
                payload={"traceback": traceback.format_exc(limit=8)},
            )
        finally:
            run.events.close()

    def _run_sceneforge(self, run: StudioRun, request: dict[str, Any]) -> None:
        try:
            if not self.sceneforge_runner or not self.sceneforge_data_directory:
                raise StudioRequestError("SceneForge runner and data directory are not configured")
            scene_request = request.get("request")
            if not isinstance(scene_request, dict):
                raise StudioRequestError("sceneforge requires a request object")
            run.status = "running"
            command = [
                "node", str(self.sceneforge_runner), "--studio-run-id", run.run_id,
                "--data-directory", str(self.sceneforge_data_directory),
            ]
            process = subprocess.Popen(
                command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", bufsize=1,
            )
            assert process.stdin and process.stdout and process.stderr
            process.stdin.write(json.dumps(scene_request))
            process.stdin.close()
            for raw_line in process.stdout:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise StudioRequestError(f"SceneForge runner emitted invalid JSON: {exc}") from exc
                if event.get("kind") != "studio.intent-event":
                    continue
                emitted = run.events.emit(
                    event.get("type", "runtime.event"), event.get("phase", "runtime"),
                    event.get("message", "SceneForge runtime changed state."),
                    progress=event.get("progress"), confidence=event.get("confidence"),
                    payload=event.get("payload") or {},
                )
                if emitted.type == "run.completed":
                    result = emitted.payload.get("result")
                    if isinstance(result, dict):
                        run.result = result
                    raw_artifacts = emitted.payload.get("artifacts")
                    if isinstance(raw_artifacts, dict):
                        for key, raw_path in raw_artifacts.items():
                            path = Path(str(raw_path)).resolve()
                            try:
                                path.relative_to(self.sceneforge_data_directory)
                            except ValueError:
                                continue
                            if path.is_file():
                                run.artifacts[str(key)] = path
            stderr = process.stderr.read().strip()
            return_code = process.wait()
            if return_code != 0:
                raise StudioRequestError(stderr or f"SceneForge runner exited with {return_code}")
            run.status = "completed"
            if run.result is None:
                run.result = {"status": "completed"}
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)
            run.events.emit(
                "run.failed", "failure", str(exc), progress=1.0, confidence=1.0,
                payload={"traceback": traceback.format_exc(limit=8)},
            )
        finally:
            run.events.close()


def create_handler(service: StudioService) -> type[BaseHTTPRequestHandler]:
    class StudioHandler(BaseHTTPRequestHandler):
        server_version = "ProductionStudioIntent/0.1"

        def log_message(self, format: str, *args: Any) -> None:
            print(f"studio-console: {format % args}")

        def send_json(self, status: int, value: Any) -> None:
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def read_json(self) -> Any:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise StudioRequestError("Invalid Content-Length") from exc
            if length <= 0 or length > 1_000_000:
                raise StudioRequestError("Request body is empty or too large")
            try:
                return json.loads(self.rfile.read(length))
            except json.JSONDecodeError as exc:
                raise StudioRequestError(f"Invalid JSON: {exc}") from exc

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/runs":
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            try:
                run = service.create_run(self.read_json())
            except StudioRequestError as exc:
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            self.send_json(HTTPStatus.ACCEPTED, run.public())

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/index.html"}:
                self.serve_file(service.ui_root / "index.html")
                return
            run_status = parsed.path.removeprefix("/api/runs/")
            if run_status and "/" not in run_status:
                run = service.get_run(run_status)
                if not run:
                    self.send_json(HTTPStatus.NOT_FOUND, {"error": "run_not_found"})
                    return
                self.send_json(HTTPStatus.OK, run.public())
                return
            if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/events"):
                run_id = parsed.path[len("/api/runs/") : -len("/events")].strip("/")
                run = service.get_run(run_id)
                if not run:
                    self.send_json(HTTPStatus.NOT_FOUND, {"error": "run_not_found"})
                    return
                after = int(parse_qs(parsed.query).get("after", ["0"])[0] or 0)
                self.stream_events(run, after)
                return
            marker = "/artifacts/"
            if parsed.path.startswith("/api/runs/") and marker in parsed.path:
                left, key = parsed.path.split(marker, 1)
                run_id = left.removeprefix("/api/runs/").strip("/")
                run = service.get_run(run_id)
                path = run.artifacts.get(key) if run else None
                if not path:
                    self.send_json(HTTPStatus.NOT_FOUND, {"error": "artifact_not_found"})
                    return
                self.serve_file(path, private=True)
                return
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def stream_events(self, run: StudioRun, after: int) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            cursor = after
            try:
                while True:
                    events, closed = run.events.wait(cursor, timeout=10.0)
                    if not events:
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
                    for event in events:
                        self.wfile.write(f"id: {event.sequence}\n".encode("ascii"))
                        self.wfile.write(b"event: intent\n")
                        self.wfile.write(b"data: " + event.to_json().encode("utf-8") + b"\n\n")
                        self.wfile.flush()
                        cursor = event.sequence
                    if closed and not events:
                        break
            except (BrokenPipeError, ConnectionResetError):
                return

        def serve_file(self, path: Path, private: bool = False) -> None:
            try:
                value = path.read_bytes()
            except OSError:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "file_not_found"})
                return
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(value)))
            self.send_header("Cache-Control", "private, no-store" if private else "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(value)

    return StudioHandler


def create_server(service: StudioService, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise StudioRequestError("The studio console binds to loopback only")
    return ThreadingHTTPServer((host, port), create_handler(service))
