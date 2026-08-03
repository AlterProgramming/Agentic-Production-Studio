from __future__ import annotations

import sys
import time
from pathlib import Path

from studio_runtime.events import EventBuffer
from studio_runtime.video import (CommandVideoEvaluator, CommandVideoGenerator, ShotSpec,
                                  VideoProjectConfig, VideoProjectPipeline, VideoRatePolicy)
from studio_runtime.video_service import StudioService


class FakeTime:
    def __init__(self): self.value = 0.0
    def clock(self): return self.value
    def sleep(self, seconds): self.value += seconds


def wait_for(run, timeout: float = 8.0) -> None:
    deadline = time.time() + timeout
    while run.status in {"queued", "running"} and time.time() < deadline:
        time.sleep(0.01)
    assert run.status not in {"queued", "running"}


def write_generator(path: Path, rate_limit_once: bool = False) -> None:
    path.write_text(f'''\
import json, pathlib, sys
req=json.load(sys.stdin)
out=pathlib.Path(req["output_directory"]); out.mkdir(parents=True, exist_ok=True)
marker=out.parent / "rate.marker"
if {rate_limit_once!r} and not marker.exists():
    marker.write_text("1")
    print(json.dumps({{"status":"rate_limited","retry_after":0.5,"error":"slow down"}}))
    raise SystemExit(75)
path=out / "candidate.mp4"; path.write_bytes((req["operation"]+req["candidate_id"]).encode())
print(json.dumps({{"status":"completed","video_path":str(path),"provider_job_id":"job-"+req["candidate_id"]}}))
''', encoding='utf-8')


def write_evaluator(path: Path) -> None:
    path.write_text('''\
import json, sys
req=json.load(sys.stdin)
id=req["candidate_id"]
score=0.92 if id.startswith("r") else (0.84 if id=="c02" else 0.72)
metrics={k:score for k in ["identity_stability","temporal_consistency","motion_quality","camera_intent","composition","world_continuity","orb_hand_continuity"]}
metrics["artifact_penalty"]=0.02
print(json.dumps({"status":"completed","metrics":metrics,"notes":["fake evaluator"]}))
''', encoding='utf-8')


def test_multi_shot_graph_repairs_and_persists_state(tmp_path: Path) -> None:
    ref = tmp_path / "ref.png"; ref.write_bytes(b"png")
    generator = tmp_path / "generator.py"; evaluator = tmp_path / "evaluator.py"
    write_generator(generator); write_evaluator(evaluator)
    shots = (
        ShotSpec("shot-a", "A", "first shot", ref, candidates=2, repair_budget=1, target_score=.88),
        ShotSpec("shot-b", "B", "second shot", ref, dependencies=("shot-a",), candidates=1, repair_budget=1, target_score=.88),
    )
    config = VideoProjectConfig("project", tmp_path / "runs", shots,
        VideoRatePolicy(120, 2, 1, 0, 0))
    pipeline = VideoProjectPipeline(
        CommandVideoGenerator([sys.executable, str(generator)]),
        CommandVideoEvaluator([sys.executable, str(evaluator)]),
    )
    events = EventBuffer("project")
    result = pipeline.run(config, events)
    assert result["status"] == "completed"
    assert list(result["shots"]) == ["shot-a", "shot-b"]
    assert result["shots"]["shot-a"]["best"]["candidate_id"] == "r01"
    assert result["shots"]["shot-a"]["best"]["score"] > .88
    assert Path(result["state_path"]).is_file()
    types = [event.type for event in events.snapshot()]
    assert "video.repair.requested" in types
    assert types[-1] == "video.project.completed"


def test_rate_limit_cools_down_and_retries(tmp_path: Path) -> None:
    ref = tmp_path / "ref.png"; ref.write_bytes(b"png")
    generator = tmp_path / "generator.py"; evaluator = tmp_path / "evaluator.py"
    write_generator(generator, True); write_evaluator(evaluator)
    fake = FakeTime()
    config = VideoProjectConfig("rate-project", tmp_path / "runs",
        (ShotSpec("shot", "Shot", "prompt", ref, candidates=1, repair_budget=0, target_score=.1),),
        VideoRatePolicy(120, 1, 1, 0, 0))
    pipeline = VideoProjectPipeline(
        CommandVideoGenerator([sys.executable, str(generator)]),
        CommandVideoEvaluator([sys.executable, str(evaluator)]),
        clock=fake.clock, sleeper=fake.sleep,
    )
    events = EventBuffer("rate-project")
    result = pipeline.run(config, events)
    assert result["status"] == "completed"
    assert fake.value >= .5
    assert "video.rate.cooldown" in [event.type for event in events.snapshot()]


def test_resume_retains_completed_shots(tmp_path: Path) -> None:
    ref = tmp_path / "ref.png"; ref.write_bytes(b"png")
    generator = tmp_path / "generator.py"; evaluator = tmp_path / "evaluator.py"
    write_generator(generator); write_evaluator(evaluator)
    shot = ShotSpec("shot", "Shot", "prompt", ref, candidates=1, repair_budget=0, target_score=.1)
    pipeline = VideoProjectPipeline(CommandVideoGenerator([sys.executable, str(generator)]),
                                    CommandVideoEvaluator([sys.executable, str(evaluator)]))
    first = VideoProjectConfig("source", tmp_path / "runs", (shot,), VideoRatePolicy(120, 1, 0, 0, 0))
    pipeline.run(first, EventBuffer("source"))
    resumed = VideoProjectConfig("continued", tmp_path / "runs", (shot,), VideoRatePolicy(120, 1, 0, 0, 0),
                                 resume_project_id="source")
    events = EventBuffer("continued")
    result = pipeline.run(resumed, events)
    assert result["shots"]["shot"]["status"] == "completed"
    assert "video.shot.resumed" in [event.type for event in events.snapshot()]


def test_studio_service_streams_video_project_and_retains_artifacts(tmp_path: Path) -> None:
    ref = tmp_path / "ref.png"; ref.write_bytes(b"png")
    generator = tmp_path / "generator.py"; evaluator = tmp_path / "evaluator.py"
    write_generator(generator); write_evaluator(evaluator)
    output = tmp_path / "video-output"
    service = StudioService(
        ui_root=tmp_path,
        allowed_roots=[tmp_path],
        video_generator_command=[sys.executable, str(generator)],
        video_evaluator_command=[sys.executable, str(evaluator)],
        video_output_directory=output,
    )
    run = service.create_run({
        "mode": "video_project",
        "request": {
            "project_id": "service-project",
            "rate_policy": {"requests_per_minute": 120, "burst": 1, "max_retries": 0},
            "shots": [{
                "shot_id": "shot",
                "title": "Shot",
                "prompt": "controlled motion",
                "reference_image": str(ref),
                "candidates": 1,
                "repair_budget": 0,
                "target_score": 0.1,
            }],
        },
    })
    wait_for(run)
    assert run.status == "completed"
    assert run.artifacts["hero"].is_file()
    assert run.artifacts["state"].is_file()
    assert "video_path" not in run.result["shots"]["shot"]["best"]
    assert run.result["shots"]["shot"]["best"]["artifact_key"] == "best-shot"
    assert [event.type for event in run.events.snapshot()][-1] == "run.completed"
