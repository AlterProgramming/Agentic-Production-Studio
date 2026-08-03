#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio_runtime.events import EventBuffer
from studio_runtime.video import (CommandVideoEvaluator, CommandVideoGenerator, ShotSpec,
                                  VideoProjectConfig, VideoProjectPipeline, VideoRatePolicy)


def strings(value):
    return tuple(str(x) for x in value or [])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a retained multi-shot video project")
    parser.add_argument("plan")
    parser.add_argument("--generator-command", required=True)
    parser.add_argument("--evaluator-command")
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    base = Path(args.plan).resolve().parent
    shots = tuple(ShotSpec(
        shot_id=item["shot_id"], title=item["title"], prompt=item["prompt"],
        reference_image=(base / item["reference_image"]).resolve(),
        seconds=int(item.get("seconds", 4)), size=item.get("size", "1280x720"),
        model=item.get("model", "sora-2"), dependencies=strings(item.get("dependencies")),
        preserve=strings(item.get("preserve")), motion=strings(item.get("motion")),
        avoid=strings(item.get("avoid")), candidates=int(item.get("candidates", 2)),
        repair_budget=int(item.get("repair_budget", 2)), target_score=float(item.get("target_score", .86)),
    ) for item in plan["shots"])
    rate = plan.get("rate_policy") or {}
    config = VideoProjectConfig(
        project_id=plan.get("project_id") or f"video-{uuid4()}",
        output_root=(base / plan.get("output_root", "video-runs")).resolve(), shots=shots,
        rate_policy=VideoRatePolicy(float(rate.get("requests_per_minute", 2)), int(rate.get("burst", 1)),
                                    int(rate.get("max_retries", 4)), float(rate.get("base_backoff_seconds", 3)),
                                    float(rate.get("max_backoff_seconds", 90))),
        resume_project_id=plan.get("resume_project_id"),
    )
    evaluator = CommandVideoEvaluator(shlex.split(args.evaluator_command)) if args.evaluator_command else None
    pipeline = VideoProjectPipeline(CommandVideoGenerator(shlex.split(args.generator_command)), evaluator)
    events = EventBuffer(config.project_id)
    result = pipeline.run(config, events)
    for event in events.snapshot():
        print(event.to_json())
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
