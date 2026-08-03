from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

from studio_runtime.events import EventBuffer
from studio_runtime.recreation import (
    CommandImageGenerator,
    RatePolicy,
    RecreationConfig,
    RecreationPipeline,
)
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


class FakeTime:
    def __init__(self) -> None:
        self.value = 0.0

    def clock(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += max(0.0, seconds)


def wait_for(run, timeout: float = 8.0) -> None:
    deadline = time.time() + timeout
    while run.status in {"queued", "running"} and time.time() < deadline:
        time.sleep(0.01)
    assert run.status not in {"queued", "running"}


def write_generator(path: Path, *, first_rate_limited: bool = False) -> None:
    path.write_text(
        f"""
import json
from pathlib import Path
import sys

request = json.load(sys.stdin)
output = Path(request['output_directory'])
output.mkdir(parents=True, exist_ok=True)
state = output.parents[2] / 'provider-count.txt'
count = int(state.read_text() if state.exists() else '0') + 1
state.write_text(str(count))
if {str(first_rate_limited)} and count == 1:
    print(json.dumps({{'status': 'rate_limited', 'retry_after': 0, 'error': 'test throttle'}}))
    raise SystemExit(75)
iteration = int(request['iteration'])
index = int(request['candidate_index'])
image = output / 'candidate.png'
reference = Path(request['reference_image']).read_bytes()
image.write_bytes(reference + f'-{{iteration}}-{{index}}'.encode())
base = min(0.96, 0.60 + iteration * 0.12 + index * 0.02)
print(json.dumps({{
    'status': 'completed',
    'image_path': str(image),
    'metrics': {{
        'subject_retention': base,
        'anchor_retention': base,
        'environment_match': base,
        'aesthetic_quality': base,
        'composition_stability': base,
        'drift_penalty': 0.0
    }},
    'notes': ['deterministic test provider']
}}))
""".strip()
        + "\n",
        encoding="utf-8",
    )


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


def test_sceneforge_subprocess_events_and_artifacts_are_relayed(tmp_path: Path) -> None:
    data_directory = tmp_path / "data"
    data_directory.mkdir()
    runner = tmp_path / "runner.mjs"
    runner.write_text(
        """
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
const args = process.argv.slice(2);
const dataDirectory = args[args.indexOf('--data-directory') + 1];
const studioRunId = args[args.indexOf('--studio-run-id') + 1];
const hero = path.join(dataDirectory, 'model-first', 'mf-test', 'renders', 'hero.png');
await mkdir(path.dirname(hero), { recursive: true });
await writeFile(hero, Buffer.from('png'));
process.stdout.write(JSON.stringify({
  schema_version: '1.0', kind: 'studio.intent-event', event_id: 'event-1',
  run_id: studioRunId, sequence: 1, type: 'run.completed', phase: 'result',
  message: 'runtime complete', progress: 1, confidence: 1,
  payload: { result: { run_id: 'mf-test', status: 'completed' }, artifacts: { hero } },
  emitted_at: new Date().toISOString()
}) + '\\n');
""".strip()
        + "\n",
        encoding="utf-8",
    )
    service = StudioService(
        ui_root=tmp_path,
        allowed_roots=[tmp_path],
        sceneforge_runner=runner,
        sceneforge_data_directory=data_directory,
        builder_factory=FakeBuilder,
    )
    run = service.create_run({"mode": "sceneforge", "request": {"prompt": "impact frame"}})
    wait_for(run)
    assert run.status == "completed"
    assert run.result == {"run_id": "mf-test", "status": "completed"}
    assert run.artifacts["hero"].read_bytes() == b"png"
    assert [event.type for event in run.events.snapshot()] == ["run.completed"]


def test_reference_recreation_runs_real_command_and_retains_best(tmp_path: Path) -> None:
    reference = tmp_path / "reference.png"
    reference.write_bytes(b"reference")
    generator = tmp_path / "generator.py"
    write_generator(generator)
    output = tmp_path / "recreation-output"
    service = StudioService(
        ui_root=tmp_path,
        allowed_roots=[tmp_path],
        recreation_output_directory=output,
        image_generator_command=[sys.executable, str(generator)],
        builder_factory=FakeBuilder,
    )
    run = service.create_run(
        {
            "mode": "reference_recreation",
            "request": {
                "reference_image": str(reference),
                "goal": "retain the subject while improving the world",
                "anchors": ["subject", "orb"],
                "preserve": ["identity"],
                "avoid": ["drift"],
                "max_iterations": 3,
                "candidates_per_iteration": 2,
                "target_score": 0.86,
                "patience": 3,
                "rate_policy": {
                    "requests_per_minute": 120,
                    "burst": 2,
                    "max_retries": 1,
                    "base_backoff_seconds": 0,
                    "max_backoff_seconds": 0,
                },
            },
        }
    )
    wait_for(run)
    assert run.status == "completed"
    assert run.result["candidate_count"] >= 2
    assert run.result["best"]["score"] >= 0.86
    assert run.artifacts["hero"].is_file()
    assert run.artifacts["state"].is_file()
    event_types = [event.type for event in run.events.snapshot()]
    assert "candidate.requested" in event_types
    assert "candidate.scored" in event_types
    assert "best.updated" in event_types
    assert event_types[-1] == "run.completed"


def test_rate_limit_is_cooled_down_and_retried(tmp_path: Path) -> None:
    reference = tmp_path / "reference.png"
    reference.write_bytes(b"reference")
    generator_script = tmp_path / "rate-generator.py"
    write_generator(generator_script, first_rate_limited=True)
    fake_time = FakeTime()
    pipeline = RecreationPipeline(
        CommandImageGenerator([sys.executable, str(generator_script)]),
        clock=fake_time.clock,
        sleeper=fake_time.sleep,
    )
    events = EventBuffer("rate-test")
    result = pipeline.run(
        "rate-test",
        RecreationConfig(
            reference_image=reference,
            output_root=tmp_path / "out",
            goal="test rate recovery",
            max_iterations=1,
            candidates_per_iteration=1,
            target_score=1.0,
            patience=1,
            rate_policy=RatePolicy(
                requests_per_minute=120,
                burst=1,
                max_retries=1,
                base_backoff_seconds=0,
                max_backoff_seconds=0,
            ),
        ),
        events,
    )
    assert result["candidate_count"] == 1
    assert "rate.cooldown" in [event.type for event in events.snapshot()]
    assert fake_time.value >= 0.5


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


def test_reference_image_escape_is_rejected_by_worker(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    output = tmp_path / "output"
    service = StudioService(
        ui_root=tmp_path,
        allowed_roots=[allowed],
        recreation_output_directory=output,
        image_generator_command=[sys.executable, "unused.py"],
        builder_factory=FakeBuilder,
    )
    run = service.create_run(
        {
            "mode": "reference_recreation",
            "request": {"reference_image": str(tmp_path / "outside.png"), "goal": "blocked"},
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
