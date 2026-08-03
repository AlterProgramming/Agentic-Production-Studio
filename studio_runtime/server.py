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
from typing import Any, Callable, Sequence
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from .events import EventBuffer
from .recreation import Candidate, CommandImageEvaluator, CommandImageGenerator, RatePolicy, RecreationConfig, RecreationPipeline


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
        return {"run_id": self.run_id, "mode": self.mode, "status": self.status,
                "result": self.result, "error": self.error,
                "artifacts": {k: f"/api/runs/{self.run_id}/artifacts/{k}" for k in self.artifacts}}


class StudioService:
    def __init__(self, *, ui_root: str | Path, allowed_roots: list[str | Path] | None = None,
                 sceneforge_runner: str | Path | None = None,
                 sceneforge_data_directory: str | Path | None = None,
                 image_generator_command: Sequence[str] | None = None,
                 image_evaluator_command: Sequence[str] | None = None,
                 recreation_output_directory: str | Path | None = None,
                 builder_factory: Callable[[Path], Any] | None = None,
                 recreation_pipeline_factory: Callable[[], RecreationPipeline] | None = None) -> None:
        self.ui_root = Path(ui_root).resolve()
        self.allowed_roots = [Path(x).resolve() for x in (allowed_roots or [Path.cwd()])]
        self.sceneforge_runner = Path(sceneforge_runner).resolve() if sceneforge_runner else None
        self.sceneforge_data_directory = Path(sceneforge_data_directory).resolve() if sceneforge_data_directory else None
        self.image_generator_command = tuple(image_generator_command or ())
        self.image_evaluator_command = tuple(image_evaluator_command or ())
        self.recreation_output_directory = Path(recreation_output_directory).expanduser().resolve() if recreation_output_directory else None
        self.builder_factory = builder_factory or self._default_builder_factory
        self.recreation_pipeline_factory = recreation_pipeline_factory
        self._runs: dict[str, StudioRun] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _default_builder_factory(root: Path) -> Any:
        from studio_builder import StudioBuilder
        return StudioBuilder(root)

    def resolve_allowed_root(self, value: str | Path) -> Path:
        candidate = Path(value).expanduser().resolve()
        for root in self.allowed_roots:
            try:
                candidate.relative_to(root)
                return candidate
            except ValueError:
                pass
        raise StudioRequestError(f"Workspace is outside configured roots: {candidate}")

    def get_run(self, run_id: str) -> StudioRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def create_run(self, request: dict[str, Any]) -> StudioRun:
        if not isinstance(request, dict):
            raise StudioRequestError("Request body must be an object")
        mode = request.get("mode")
        workers = {"builder_preview": self._run_builder, "sceneforge": self._run_sceneforge,
                   "reference_recreation": self._run_recreation}
        if mode not in workers:
            raise StudioRequestError("mode must be builder_preview, sceneforge, or reference_recreation")
        run = StudioRun(f"studio-{uuid4()}", str(mode), EventBuffer("pending"))
        run.events = EventBuffer(run.run_id)
        with self._lock:
            self._runs[run.run_id] = run
        threading.Thread(target=workers[mode], args=(run, request), daemon=True).start()
        return run

    @staticmethod
    def _fail(run: StudioRun, exc: Exception) -> None:
        run.status, run.error = "failed", str(exc)
        run.events.emit("run.failed", "failure", str(exc), progress=1.0, confidence=1.0,
                        payload={"traceback": traceback.format_exc(limit=8)})

    def _run_builder(self, run: StudioRun, request: dict[str, Any]) -> None:
        try:
            workspace = self.resolve_allowed_root(request.get("workspace_root", "."))
            plan = request.get("plan")
            if not isinstance(plan, dict):
                raise StudioRequestError("builder_preview requires a plan object")
            run.status = "running"
            run.events.emit("run.accepted", "framing", "The builder request is inside the allowed workspace boundary.",
                            progress=.05, confidence=.95,
                            payload={"workspace_root": str(workspace), "plan_id": plan.get("plan_id")})
            run.events.emit("intent.interpreted", "planning", "The runtime will simulate operations without mutating the workspace.",
                            progress=.18, confidence=.98,
                            payload={"operation_count": len(plan.get("operations", []))})
            report = self.builder_factory(workspace).preview(plan)
            operations = report.get("operations", [])
            for i, operation in enumerate(operations, 1):
                run.events.emit("operation.evaluated", "simulation",
                                f"Evaluated {operation.get('id', 'operation')} as {operation.get('type', 'unknown')}.",
                                progress=.2 + .52 * i / max(1, len(operations)), confidence=.96, payload=operation)
            run.result, run.status = report, "completed"
            run.events.emit("artifact.committed", "result", "The non-mutating builder receipt is ready.",
                            progress=1.0, confidence=.99,
                            payload={"summary": report.get("summary", {}), "report": report})
        except Exception as exc:
            self._fail(run, exc)
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
            process = subprocess.Popen(["node", str(self.sceneforge_runner), "--studio-run-id", run.run_id,
                                        "--data-directory", str(self.sceneforge_data_directory)],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, encoding="utf-8", bufsize=1)
            assert process.stdin and process.stdout and process.stderr
            process.stdin.write(json.dumps(scene_request)); process.stdin.close()
            for raw in process.stdout:
                if not raw.strip():
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise StudioRequestError(f"SceneForge runner emitted invalid JSON: {exc}") from exc
                if event.get("kind") != "studio.intent-event":
                    continue
                emitted = run.events.emit(event.get("type", "runtime.event"), event.get("phase", "runtime"),
                                          event.get("message", "SceneForge runtime changed state."),
                                          progress=event.get("progress"), confidence=event.get("confidence"),
                                          payload=event.get("payload") or {})
                if emitted.type == "run.completed":
                    if isinstance(emitted.payload.get("result"), dict):
                        run.result = emitted.payload["result"]
                    for key, raw_path in (emitted.payload.get("artifacts") or {}).items():
                        path = Path(str(raw_path)).resolve()
                        try:
                            path.relative_to(self.sceneforge_data_directory)
                        except ValueError:
                            continue
                        if path.is_file():
                            run.artifacts[str(key)] = path
            error, code = process.stderr.read().strip(), process.wait()
            if code:
                raise StudioRequestError(error or f"SceneForge runner exited with {code}")
            run.status = "completed"
            run.result = run.result or {"status": "completed"}
        except Exception as exc:
            self._fail(run, exc)
        finally:
            run.events.close()

    @staticmethod
    def _strings(value: Any, name: str) -> tuple[str, ...]:
        if value is None:
            return ()
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            raise StudioRequestError(f"{name} must be an array of strings")
        return tuple(x.strip() for x in value if x.strip())

    def _pipeline(self) -> RecreationPipeline:
        if self.recreation_pipeline_factory:
            return self.recreation_pipeline_factory()
        if not self.image_generator_command:
            raise StudioRequestError("Reference recreation requires an image generator command")
        evaluator = CommandImageEvaluator(self.image_evaluator_command) if self.image_evaluator_command else None
        return RecreationPipeline(CommandImageGenerator(self.image_generator_command), evaluator=evaluator)

    def _run_recreation(self, run: StudioRun, request: dict[str, Any]) -> None:
        try:
            if not self.recreation_output_directory:
                raise StudioRequestError("Reference recreation output directory is not configured")
            body = request.get("request")
            if not isinstance(body, dict):
                raise StudioRequestError("reference_recreation requires a request object")
            raw_reference, goal = body.get("reference_image"), body.get("goal")
            if not isinstance(raw_reference, str) or not raw_reference.strip():
                raise StudioRequestError("reference_image must be a non-empty path")
            reference = self.resolve_allowed_root(raw_reference)
            if not reference.is_file():
                raise StudioRequestError(f"Reference image does not exist: {reference}")
            if not isinstance(goal, str) or not goal.strip():
                raise StudioRequestError("goal must be a non-empty string")
            raw_rate = body.get("rate_policy") or {}
            if not isinstance(raw_rate, dict):
                raise StudioRequestError("rate_policy must be an object")
            policy = RatePolicy(float(raw_rate.get("requests_per_minute", 4)), int(raw_rate.get("burst", 1)),
                                int(raw_rate.get("max_retries", 4)), float(raw_rate.get("base_backoff_seconds", 2)),
                                float(raw_rate.get("max_backoff_seconds", 60)))
            config = RecreationConfig(reference, self.recreation_output_directory, goal,
                self._strings(body.get("anchors"), "anchors"), self._strings(body.get("preserve"), "preserve"),
                self._strings(body.get("avoid"), "avoid"), int(body.get("max_iterations", 6)),
                int(body.get("candidates_per_iteration", 2)), float(body.get("target_score", .92)),
                int(body.get("patience", 3)), float(body.get("minimum_improvement", .01)), policy,
                str(body["resume_job_id"]).strip() if body.get("resume_job_id") else None)
            run.status = "running"

            def retain(candidate: Candidate, best: bool) -> str:
                path = Path(candidate.image_path).resolve()
                try:
                    path.relative_to(self.recreation_output_directory)
                except ValueError as exc:
                    raise StudioRequestError("Recreation candidate escaped the configured output directory") from exc
                key = f"candidate-{candidate.candidate_id}"
                run.artifacts[key] = path
                if best:
                    run.artifacts["hero"] = path
                    return "hero"
                return key

            result = self._pipeline().run(run.run_id, config, run.events, artifact_callback=retain)
            state = Path(result["state_path"]).resolve(); state.relative_to(self.recreation_output_directory)
            run.artifacts["state"] = state
            best = dict(result["best"]); best.pop("image_path", None); best.pop("parent_image", None)
            best["artifact_key"] = "hero"
            run.result = {k: result[k] for k in ("schema_version", "job_id", "status", "stopped_reason",
                                                  "iterations_completed", "candidate_count", "resumed_from")}
            run.result["best"] = best
            run.status = "completed"
        except Exception as exc:
            self._fail(run, exc)
        finally:
            run.events.close()


def create_handler(service: StudioService) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "ProductionStudioIntent/0.2"

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"studio-console: {fmt % args}")

        def send_json(self, status: int, value: Any) -> None:
            data = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data))); self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(data)

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
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            try:
                run = service.create_run(self.read_json())
            except StudioRequestError as exc:
                return self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            self.send_json(HTTPStatus.ACCEPTED, run.public())

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/index.html"}:
                return self.serve_file(service.ui_root / "index.html")
            relative = parsed.path.removeprefix("/api/runs/")
            if relative and "/" not in relative:
                run = service.get_run(relative)
                return self.send_json(HTTPStatus.OK, run.public()) if run else self.send_json(404, {"error": "run_not_found"})
            if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/events"):
                run_id = parsed.path[len("/api/runs/"):-len("/events")].strip("/")
                run = service.get_run(run_id)
                if not run:
                    return self.send_json(404, {"error": "run_not_found"})
                try:
                    after = int(parse_qs(parsed.query).get("after", ["0"])[0] or 0)
                except ValueError:
                    return self.send_json(400, {"error": "invalid_after"})
                return self.stream_events(run, after)
            if parsed.path.startswith("/api/runs/") and "/artifacts/" in parsed.path:
                left, key = parsed.path.split("/artifacts/", 1)
                run = service.get_run(left.removeprefix("/api/runs/").strip("/"))
                path = run.artifacts.get(key) if run else None
                return self.serve_file(path, private=True) if path else self.send_json(404, {"error": "artifact_not_found"})
            self.send_json(404, {"error": "not_found"})

        def stream_events(self, run: StudioRun, after: int) -> None:
            self.send_response(200); self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store"); self.send_header("Connection", "keep-alive"); self.end_headers()
            cursor = after
            try:
                while True:
                    events, closed = run.events.wait(cursor, timeout=10)
                    if not events:
                        self.wfile.write(b": keep-alive\n\n"); self.wfile.flush()
                    for event in events:
                        self.wfile.write(f"id: {event.sequence}\nevent: intent\ndata: {event.to_json()}\n\n".encode())
                        self.wfile.flush(); cursor = event.sequence
                    if closed and not events:
                        break
            except (BrokenPipeError, ConnectionResetError):
                pass

        def serve_file(self, path: Path, private: bool = False) -> None:
            try:
                data = path.read_bytes()
            except OSError:
                return self.send_json(404, {"error": "file_not_found"})
            self.send_response(200); self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data))); self.send_header("Cache-Control", "private, no-store" if private else "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(data)

    return Handler


def create_server(service: StudioService, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise StudioRequestError("The studio console binds to loopback only")
    return ThreadingHTTPServer((host, port), create_handler(service))
