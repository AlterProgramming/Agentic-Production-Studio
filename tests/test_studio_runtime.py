from __future__ import annotations

import time
from pathlib import Path

import pytest

from studio_runtime.events import EventBuffer
from studio_runtime.server import StudioRequestError, StudioService


class FakeBuilder:
    def __init__(self, root: Path):
        self.root = root

    def preview(self, plan: dict) -> dict:
        return {
            "plan_id": plan["plan_id"],
            "operations": [
                {"id": item["id"], "type": item["type"], "paths": [item["path"]]}
                for item in plan["operations"]
            ],
            "changes": [{"path": "work/example.txt", "action": "create"}],
            "summary": {"operations": 1, "changed_files": 1, "created": 1, "updated": 0, "deleted": 0},
        }


def wait_for(run, timeout: float = 2.0) -> None:
    deadline = time.time() + timeout
    while run.status in {"queued", "running"} and time.time() < deadline:
        time.sleep(0.01)
    assert run.status not in {"queued", "running"}


def test_event_buffer_replays_in_sequence() -> None:
    buffer = EventBuffer("run-1")
    first = buffer.emit("run.accepted", "framing", "accepted", progress=0.1)
    second = buffer.emit("run.completed", "result", "done", progress=1.0)
    assert first.sequence == 1
    assert second.sequence == 2
    assert [event.type for event in buffer.snapshot(after_sequence=1)] == ["run.completed"]


def test_builder_preview_emits_semantic_result(tmp_path: Path) -> None:
    service = StudioService(ui_root=tmp_path, allowed_roots=[tmp_path], builder_factory=FakeBuilder)
    run = service.create_run(
        {
            "mode": "builder_preview",
            "workspace_root": str(tmp_path),
            "plan": {
                "schema_version": "1.0",
                "plan_id": "test",
                "allowed_paths": ["work/**"],
                "preconditions": [],
                "operations": [
                    {"id": "write", "type": "write_text", "path": "work/example.txt", "content": "hello"}
                ],
                "postconditions": [],
            },
        }
    )
    wait_for(run)
    assert run.status == "completed"
    assert [event.type for event in run.events.snapshot()] == [
        "run.accepted", "intent.interpreted", "operation.evaluated", "artifact.committed"
    ]
    assert run.result["summary"]["changed_files"] == 1


def test_workspace_escape_is_rejected_by_worker(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    service = StudioService(ui_root=tmp_path, allowed_roots=[allowed], builder_factory=FakeBuilder)
    run = service.create_run(
        {
            "mode": "builder_preview",
            "workspace_root": str(tmp_path / "outside"),
            "plan": {"plan_id": "blocked", "operations": []},
        }
    )
    wait_for(run)
    assert run.status == "failed"
    assert "outside configured roots" in run.error


def test_console_refuses_non_loopback_bind(tmp_path: Path) -> None:
    from studio_runtime.server import create_server

    service = StudioService(ui_root=tmp_path, allowed_roots=[tmp_path], builder_factory=FakeBuilder)
    with pytest.raises(StudioRequestError, match="loopback"):
        create_server(service, "0.0.0.0", 0)
