from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable, Sequence
from uuid import uuid4

from .events import EventBuffer
from .server import StudioRequestError, StudioRun, StudioService as BaseStudioService
from .video import (
    CommandVideoEvaluator,
    CommandVideoGenerator,
    ShotSpec,
    VideoCandidate,
    VideoProjectConfig,
    VideoProjectPipeline,
    VideoRatePolicy,
)


class StudioService(BaseStudioService):
    """Extends the live studio with retained multi-shot video projects."""

    def __init__(
        self,
        *,
        video_generator_command: Sequence[str] | None = None,
        video_evaluator_command: Sequence[str] | None = None,
        video_output_directory: str | Path | None = None,
        video_pipeline_factory: Callable[[], VideoProjectPipeline] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.video_generator_command = tuple(video_generator_command or ())
        self.video_evaluator_command = tuple(video_evaluator_command or ())
        self.video_output_directory = (
            Path(video_output_directory).expanduser().resolve() if video_output_directory else None
        )
        self.video_pipeline_factory = video_pipeline_factory

    def create_run(self, request: dict[str, Any]) -> StudioRun:
        if not isinstance(request, dict):
            raise StudioRequestError("Request body must be an object")
        if request.get("mode") != "video_project":
            return super().create_run(request)
        run = StudioRun(f"studio-{uuid4()}", "video_project", EventBuffer("pending"))
        run.events = EventBuffer(run.run_id)
        with self._lock:
            self._runs[run.run_id] = run
        threading.Thread(target=self._run_video_project, args=(run, request), daemon=True).start()
        return run

    def _video_pipeline(self) -> VideoProjectPipeline:
        if self.video_pipeline_factory:
            return self.video_pipeline_factory()
        if not self.video_generator_command:
            raise StudioRequestError("Video projects require a video generator command")
        evaluator = (
            CommandVideoEvaluator(self.video_evaluator_command)
            if self.video_evaluator_command
            else None
        )
        return VideoProjectPipeline(CommandVideoGenerator(self.video_generator_command), evaluator)

    def _shot(self, value: Any) -> ShotSpec:
        if not isinstance(value, dict):
            raise StudioRequestError("each video shot must be an object")
        raw_reference = value.get("reference_image")
        if not isinstance(raw_reference, str) or not raw_reference.strip():
            raise StudioRequestError("each video shot requires reference_image")
        reference = self.resolve_allowed_root(raw_reference)
        if not reference.is_file():
            raise StudioRequestError(f"Video reference image does not exist: {reference}")
        for field in ("shot_id", "title", "prompt"):
            if not isinstance(value.get(field), str) or not value[field].strip():
                raise StudioRequestError(f"each video shot requires non-empty {field}")
        return ShotSpec(
            shot_id=value["shot_id"].strip(),
            title=value["title"].strip(),
            prompt=value["prompt"].strip(),
            reference_image=reference,
            seconds=int(value.get("seconds", 4)),
            size=str(value.get("size", "1280x720")),
            model=str(value.get("model", "sora-2")),
            dependencies=self._strings(value.get("dependencies"), "dependencies"),
            preserve=self._strings(value.get("preserve"), "preserve"),
            motion=self._strings(value.get("motion"), "motion"),
            avoid=self._strings(value.get("avoid"), "avoid"),
            candidates=int(value.get("candidates", 2)),
            repair_budget=int(value.get("repair_budget", 2)),
            target_score=float(value.get("target_score", 0.86)),
        )

    def _run_video_project(self, run: StudioRun, request: dict[str, Any]) -> None:
        try:
            if not self.video_output_directory:
                raise StudioRequestError("Video project output directory is not configured")
            body = request.get("request")
            if not isinstance(body, dict):
                raise StudioRequestError("video_project requires a request object")
            raw_shots = body.get("shots")
            if not isinstance(raw_shots, list) or not raw_shots:
                raise StudioRequestError("video_project requires a non-empty shots array")
            raw_rate = body.get("rate_policy") or {}
            if not isinstance(raw_rate, dict):
                raise StudioRequestError("rate_policy must be an object")
            policy = VideoRatePolicy(
                float(raw_rate.get("requests_per_minute", 2)),
                int(raw_rate.get("burst", 1)),
                int(raw_rate.get("max_retries", 4)),
                float(raw_rate.get("base_backoff_seconds", 3)),
                float(raw_rate.get("max_backoff_seconds", 90)),
            )
            project_id = str(body.get("project_id") or run.run_id).strip()
            config = VideoProjectConfig(
                project_id=project_id,
                output_root=self.video_output_directory,
                shots=tuple(self._shot(value) for value in raw_shots),
                rate_policy=policy,
                resume_project_id=(
                    str(body["resume_project_id"]).strip()
                    if body.get("resume_project_id")
                    else None
                ),
            )
            run.status = "running"
            best_keys: dict[str, str] = {}

            def retain(candidate: VideoCandidate, best: bool) -> str:
                path = candidate.video_path.resolve()
                try:
                    path.relative_to(self.video_output_directory)
                except ValueError as exc:
                    raise StudioRequestError(
                        "Video candidate escaped the configured output directory"
                    ) from exc
                key = f"video-{candidate.shot_id}-{candidate.candidate_id}"
                run.artifacts[key] = path
                if best:
                    best_key = f"best-{candidate.shot_id}"
                    run.artifacts[best_key] = path
                    run.artifacts["hero"] = path
                    best_keys[candidate.shot_id] = best_key
                    return best_key
                return key

            result = self._video_pipeline().run(
                config, run.events, artifact_callback=retain
            )
            state = Path(result["state_path"]).resolve()
            try:
                state.relative_to(self.video_output_directory)
            except ValueError as exc:
                raise StudioRequestError(
                    "Video state escaped the configured output directory"
                ) from exc
            run.artifacts["state"] = state
            public_shots: dict[str, Any] = {}
            for shot_id, shot_state in result["shots"].items():
                public_state = dict(shot_state)
                best = dict(public_state["best"])
                best.pop("video_path", None)
                best["artifact_key"] = best_keys.get(shot_id, f"best-{shot_id}")
                public_state["best"] = best
                public_shots[shot_id] = public_state
            run.result = {
                "schema_version": result["schema_version"],
                "project_id": result["project_id"],
                "status": result["status"],
                "shot_count": result["shot_count"],
                "shots": public_shots,
            }
            run.status = "completed"
            run.events.emit(
                "run.completed",
                "video-result",
                "The retained video project is ready for inspection.",
                progress=1.0,
                confidence=0.99,
                payload={"result": run.result, "artifacts": list(run.artifacts)},
            )
        except Exception as exc:
            self._fail(run, exc)
        finally:
            run.events.close()
