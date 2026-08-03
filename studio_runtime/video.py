from __future__ import annotations

import json
import math
import random
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from .events import EventBuffer


class VideoRuntimeError(RuntimeError):
    pass


class VideoRateLimited(VideoRuntimeError):
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass(frozen=True)
class VideoRatePolicy:
    requests_per_minute: float = 2.0
    burst: int = 1
    max_retries: int = 4
    base_backoff_seconds: float = 3.0
    max_backoff_seconds: float = 90.0

    def validate(self) -> None:
        if self.requests_per_minute <= 0:
            raise VideoRuntimeError("requests_per_minute must be positive")
        if self.burst < 1:
            raise VideoRuntimeError("burst must be at least 1")
        if self.max_retries < 0:
            raise VideoRuntimeError("max_retries cannot be negative")
        if self.base_backoff_seconds < 0 or self.max_backoff_seconds < 0:
            raise VideoRuntimeError("backoff values cannot be negative")


@dataclass(frozen=True)
class ShotSpec:
    shot_id: str
    title: str
    prompt: str
    reference_image: Path
    seconds: int = 4
    size: str = "1280x720"
    model: str = "sora-2"
    dependencies: tuple[str, ...] = ()
    preserve: tuple[str, ...] = ()
    motion: tuple[str, ...] = ()
    avoid: tuple[str, ...] = ()
    candidates: int = 2
    repair_budget: int = 2
    target_score: float = 0.86

    def validate(self) -> None:
        if not self.shot_id or any(ch.isspace() for ch in self.shot_id):
            raise VideoRuntimeError("shot_id must be non-empty and contain no whitespace")
        if not self.reference_image.is_file():
            raise VideoRuntimeError(f"reference image does not exist: {self.reference_image}")
        if self.seconds not in {4, 8, 12}:
            raise VideoRuntimeError("seconds must be 4, 8, or 12")
        if self.size not in {"720x1280", "1280x720", "1024x1792", "1792x1024"}:
            raise VideoRuntimeError("unsupported video size")
        if self.candidates < 1 or self.repair_budget < 0:
            raise VideoRuntimeError("candidate and repair budgets are invalid")
        if not 0 <= self.target_score <= 1:
            raise VideoRuntimeError("target_score must be between 0 and 1")


@dataclass(frozen=True)
class VideoProjectConfig:
    project_id: str
    output_root: Path
    shots: tuple[ShotSpec, ...]
    rate_policy: VideoRatePolicy = field(default_factory=VideoRatePolicy)
    resume_project_id: str | None = None

    def validate(self) -> None:
        if not self.project_id:
            raise VideoRuntimeError("project_id is required")
        self.rate_policy.validate()
        ids = [shot.shot_id for shot in self.shots]
        if len(ids) != len(set(ids)):
            raise VideoRuntimeError("shot IDs must be unique")
        for shot in self.shots:
            shot.validate()
            missing = sorted(set(shot.dependencies) - set(ids))
            if missing:
                raise VideoRuntimeError(f"shot {shot.shot_id} has unknown dependencies: {missing}")
        _topological_order(self.shots)


@dataclass
class VideoCandidate:
    candidate_id: str
    shot_id: str
    video_path: Path
    provider_job_id: str | None = None
    parent_candidate_id: str | None = None
    repair_index: int = 0
    metrics: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    score: float = 0.0

    def public(self) -> dict[str, Any]:
        value = asdict(self)
        value["video_path"] = str(self.video_path)
        return value


class VideoGenerator(Protocol):
    def generate(self, request: dict[str, Any], event_callback: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]: ...
    def repair(self, request: dict[str, Any], event_callback: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]: ...


class VideoEvaluator(Protocol):
    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]: ...


class TokenBucket:
    def __init__(self, policy: VideoRatePolicy, *, clock: Callable[[], float] = time.monotonic,
                 sleeper: Callable[[float], None] = time.sleep):
        self.policy = policy
        self.clock = clock
        self.sleeper = sleeper
        self.tokens = float(policy.burst)
        self.last = clock()

    def acquire(self) -> float:
        rate = self.policy.requests_per_minute / 60.0
        waited = 0.0
        while True:
            now = self.clock()
            elapsed = max(0.0, now - self.last)
            self.last = now
            self.tokens = min(float(self.policy.burst), self.tokens + elapsed * rate)
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return waited
            delay = max(0.01, (1.0 - self.tokens) / rate)
            self.sleeper(delay)
            waited += delay


def _run_json_command(command: Sequence[str], request: dict[str, Any], *, timeout: float = 1800.0,
                      event_callback: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    process = subprocess.Popen(
        list(command), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", bufsize=1,
    )
    assert process.stdin and process.stdout and process.stderr
    process.stdin.write(json.dumps(request, ensure_ascii=False))
    process.stdin.close()
    result: dict[str, Any] | None = None
    lines: list[str] = []
    deadline = time.monotonic() + timeout
    while True:
        if time.monotonic() > deadline:
            process.kill()
            raise VideoRuntimeError("video adapter timed out")
        raw = process.stdout.readline()
        if raw:
            line = raw.strip()
            if not line:
                continue
            lines.append(line)
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                process.kill()
                raise VideoRuntimeError(f"video adapter emitted invalid JSON: {exc}") from exc
            if value.get("kind") == "video.adapter-event":
                if event_callback:
                    event_callback(value)
                continue
            result = value
            break
        if process.poll() is not None:
            break
        time.sleep(0.01)
    stderr = process.stderr.read().strip()
    code = process.wait()
    if result and result.get("status") == "rate_limited":
        raise VideoRateLimited(str(result.get("error") or "provider rate limit"), _float_or_none(result.get("retry_after")))
    if code == 75:
        retry_after = _float_or_none(result.get("retry_after")) if result else None
        raise VideoRateLimited(stderr or "provider rate limit", retry_after)
    if code != 0:
        message = (result or {}).get("error") if isinstance(result, dict) else None
        raise VideoRuntimeError(str(message or stderr or f"video adapter exited with {code}"))
    if not isinstance(result, dict):
        raise VideoRuntimeError(f"video adapter returned no result; output={lines[-3:]}")
    return result


class CommandVideoGenerator:
    def __init__(self, command: Sequence[str], *, timeout: float = 1800.0):
        if not command:
            raise VideoRuntimeError("video generator command cannot be empty")
        self.command = tuple(command)
        self.timeout = timeout

    def generate(self, request: dict[str, Any], event_callback=None) -> dict[str, Any]:
        return _run_json_command(self.command, {**request, "operation": "generate_video"}, timeout=self.timeout,
                                 event_callback=event_callback)

    def repair(self, request: dict[str, Any], event_callback=None) -> dict[str, Any]:
        return _run_json_command(self.command, {**request, "operation": "repair_video"}, timeout=self.timeout,
                                 event_callback=event_callback)


class CommandVideoEvaluator:
    def __init__(self, command: Sequence[str], *, timeout: float = 600.0):
        if not command:
            raise VideoRuntimeError("video evaluator command cannot be empty")
        self.command = tuple(command)
        self.timeout = timeout

    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        return _run_json_command(self.command, {**request, "operation": "evaluate_video"}, timeout=self.timeout)


METRIC_WEIGHTS = {
    "identity_stability": 0.22,
    "temporal_consistency": 0.20,
    "motion_quality": 0.16,
    "camera_intent": 0.12,
    "composition": 0.10,
    "world_continuity": 0.10,
    "orb_hand_continuity": 0.10,
}


def score_metrics(metrics: dict[str, Any]) -> tuple[float, list[str]]:
    notes: list[str] = []
    total = 0.0
    for name, weight in METRIC_WEIGHTS.items():
        value = _bounded_metric(metrics.get(name), name, notes)
        total += weight * value
    penalty = _bounded_metric(metrics.get("artifact_penalty", 0.0), "artifact_penalty", notes)
    return max(0.0, min(1.0, total - penalty)), notes


def _bounded_metric(value: Any, name: str, notes: list[str]) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        notes.append(f"missing or invalid metric: {name}")
        return 0.0
    if not 0.0 <= number <= 1.0:
        notes.append(f"metric clipped to [0,1]: {name}")
    return max(0.0, min(1.0, number))


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _topological_order(shots: Sequence[ShotSpec]) -> list[ShotSpec]:
    by_id = {shot.shot_id: shot for shot in shots}
    temporary: set[str] = set()
    permanent: set[str] = set()
    ordered: list[ShotSpec] = []

    def visit(shot_id: str) -> None:
        if shot_id in permanent:
            return
        if shot_id in temporary:
            raise VideoRuntimeError("shot dependency graph contains a cycle")
        temporary.add(shot_id)
        for dependency in by_id[shot_id].dependencies:
            visit(dependency)
        temporary.remove(shot_id)
        permanent.add(shot_id)
        ordered.append(by_id[shot_id])

    for shot in shots:
        visit(shot.shot_id)
    return ordered


class VideoProjectPipeline:
    def __init__(self, generator: VideoGenerator, evaluator: VideoEvaluator | None = None, *,
                 clock: Callable[[], float] = time.monotonic,
                 sleeper: Callable[[float], None] = time.sleep,
                 random_source: random.Random | None = None):
        self.generator = generator
        self.evaluator = evaluator
        self.clock = clock
        self.sleeper = sleeper
        self.random = random_source or random.Random()

    def run(self, config: VideoProjectConfig, events: EventBuffer,
            artifact_callback: Callable[[VideoCandidate, bool], str | None] | None = None) -> dict[str, Any]:
        config.validate()
        project_dir = config.output_root.expanduser().resolve() / config.project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        state_path = project_dir / "state.json"
        state = self._load_state(config, state_path)
        bucket = TokenBucket(config.rate_policy, clock=self.clock, sleeper=self.sleeper)
        ordered = _topological_order(config.shots)
        completed_shots: dict[str, dict[str, Any]] = dict(state.get("shots") or {})

        events.emit("video.project.started", "video-planning", "The video project graph is ready for execution.",
                    progress=0.01, confidence=0.99,
                    payload={"project_id": config.project_id, "shot_order": [s.shot_id for s in ordered],
                             "resumed": bool(config.resume_project_id)})

        for shot_index, shot in enumerate(ordered):
            if completed_shots.get(shot.shot_id, {}).get("status") == "completed":
                events.emit("video.shot.resumed", "video-resume", f"Retained completed shot {shot.shot_id}.",
                            progress=(shot_index + 0.1) / max(1, len(ordered)), confidence=1.0,
                            payload={"shot_id": shot.shot_id})
                continue
            best = self._run_shot(config, shot, project_dir, completed_shots, bucket, events, artifact_callback,
                                  shot_index, len(ordered))
            completed_shots[shot.shot_id] = {
                "status": "completed",
                "best": best.public(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            state = self._state(config, completed_shots, "running")
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

        state = self._state(config, completed_shots, "completed")
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        result = {
            "schema_version": "1.0",
            "project_id": config.project_id,
            "status": "completed",
            "shot_count": len(completed_shots),
            "shots": completed_shots,
            "state_path": str(state_path),
        }
        events.emit("video.project.completed", "video-result", "All shots reached a retained best candidate.",
                    progress=1.0, confidence=0.99, payload=result)
        return result

    def _load_state(self, config: VideoProjectConfig, state_path: Path) -> dict[str, Any]:
        if config.resume_project_id:
            source = config.output_root.expanduser().resolve() / config.resume_project_id / "state.json"
            if not source.is_file():
                raise VideoRuntimeError(f"resume state does not exist: {source}")
            return json.loads(source.read_text(encoding="utf-8"))
        if state_path.is_file():
            return json.loads(state_path.read_text(encoding="utf-8"))
        return {}

    @staticmethod
    def _state(config: VideoProjectConfig, shots: dict[str, Any], status: str) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "project_id": config.project_id,
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "resume_project_id": config.resume_project_id,
            "shots": shots,
        }

    def _run_shot(self, config: VideoProjectConfig, shot: ShotSpec, project_dir: Path,
                  completed_shots: dict[str, dict[str, Any]], bucket: TokenBucket, events: EventBuffer,
                  artifact_callback: Callable[[VideoCandidate, bool], str | None] | None,
                  shot_index: int, shot_total: int) -> VideoCandidate:
        shot_dir = project_dir / "shots" / shot.shot_id
        shot_dir.mkdir(parents=True, exist_ok=True)
        dependency_artifacts = {
            dependency: completed_shots[dependency]["best"]["video_path"] for dependency in shot.dependencies
        }
        events.emit("video.shot.started", "video-generation", f"Started shot {shot.shot_id}: {shot.title}.",
                    progress=shot_index / max(1, shot_total), confidence=0.98,
                    payload={"shot_id": shot.shot_id, "dependencies": dependency_artifacts,
                             "candidate_budget": shot.candidates, "repair_budget": shot.repair_budget})

        best: VideoCandidate | None = None
        all_candidates: list[VideoCandidate] = []
        for candidate_index in range(1, shot.candidates + 1):
            candidate_id = f"c{candidate_index:02d}"
            output_dir = shot_dir / candidate_id
            output_dir.mkdir(parents=True, exist_ok=True)
            request = self._request(config, shot, output_dir, candidate_id, dependency_artifacts)
            events.emit("video.candidate.requested", "video-generation",
                        f"Requested candidate {candidate_id} for {shot.shot_id}.",
                        progress=(shot_index + 0.15) / max(1, shot_total), confidence=0.96,
                        payload={"shot_id": shot.shot_id, "candidate_id": candidate_id})
            response = self._call_with_rate_limit(
                lambda callback: self.generator.generate(request, callback), bucket, config.rate_policy, events,
                shot.shot_id, candidate_id,
            )
            candidate = self._candidate_from_response(shot, candidate_id, response, output_dir)
            self._evaluate(candidate, shot, events)
            all_candidates.append(candidate)
            if artifact_callback:
                artifact_callback(candidate, False)
            if best is None or candidate.score > best.score:
                best = candidate
                if artifact_callback:
                    artifact_callback(candidate, True)
                events.emit("video.best.updated", "video-evaluation",
                            f"Candidate {candidate_id} is the strongest retained result for {shot.shot_id}.",
                            progress=(shot_index + 0.45) / max(1, shot_total), confidence=0.93,
                            payload={"shot_id": shot.shot_id, "candidate": candidate.public()})
            if best.score >= shot.target_score:
                break

        assert best is not None
        for repair_index in range(1, shot.repair_budget + 1):
            if best.score >= shot.target_score:
                break
            issues = self._repair_issues(best.metrics)
            repair_id = f"r{repair_index:02d}"
            output_dir = shot_dir / repair_id
            output_dir.mkdir(parents=True, exist_ok=True)
            request = self._request(config, shot, output_dir, repair_id, dependency_artifacts)
            request.update({
                "parent_video": str(best.video_path),
                "parent_candidate_id": best.candidate_id,
                "provider_job_id": best.provider_job_id,
                "repair_issues": issues,
            })
            events.emit("video.repair.requested", "video-repair",
                        f"Requested repair {repair_id} for {shot.shot_id}: {', '.join(issues)}.",
                        progress=(shot_index + 0.6) / max(1, shot_total), confidence=0.9,
                        payload={"shot_id": shot.shot_id, "repair_id": repair_id,
                                 "parent_candidate_id": best.candidate_id, "issues": issues})
            response = self._call_with_rate_limit(
                lambda callback: self.generator.repair(request, callback), bucket, config.rate_policy, events,
                shot.shot_id, repair_id,
            )
            repaired = self._candidate_from_response(shot, repair_id, response, output_dir,
                                                     parent_candidate_id=best.candidate_id,
                                                     repair_index=repair_index)
            self._evaluate(repaired, shot, events)
            all_candidates.append(repaired)
            if artifact_callback:
                artifact_callback(repaired, False)
            if repaired.score > best.score:
                best = repaired
                if artifact_callback:
                    artifact_callback(repaired, True)
                events.emit("video.best.updated", "video-repair",
                            f"Repair {repair_id} improved the retained result for {shot.shot_id}.",
                            progress=(shot_index + 0.82) / max(1, shot_total), confidence=0.93,
                            payload={"shot_id": shot.shot_id, "candidate": repaired.public()})

        manifest = {
            "schema_version": "1.0",
            "shot_id": shot.shot_id,
            "best_candidate_id": best.candidate_id,
            "best_score": best.score,
            "target_score": shot.target_score,
            "candidates": [candidate.public() for candidate in all_candidates],
        }
        (shot_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        events.emit("video.shot.completed", "video-result",
                    f"Shot {shot.shot_id} completed with score {best.score:.3f}.",
                    progress=(shot_index + 1) / max(1, shot_total), confidence=0.96,
                    payload={"shot_id": shot.shot_id, "best": best.public(),
                             "target_reached": best.score >= shot.target_score})
        return best

    @staticmethod
    def _request(config: VideoProjectConfig, shot: ShotSpec, output_dir: Path, candidate_id: str,
                 dependency_artifacts: dict[str, str]) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "project_id": config.project_id,
            "shot_id": shot.shot_id,
            "candidate_id": candidate_id,
            "title": shot.title,
            "prompt": shot.prompt,
            "reference_image": str(shot.reference_image.resolve()),
            "output_directory": str(output_dir.resolve()),
            "model": shot.model,
            "seconds": shot.seconds,
            "size": shot.size,
            "preserve": list(shot.preserve),
            "motion": list(shot.motion),
            "avoid": list(shot.avoid),
            "dependency_artifacts": dependency_artifacts,
        }

    def _call_with_rate_limit(self, call: Callable[[Callable[[dict[str, Any]], None]], dict[str, Any]],
                              bucket: TokenBucket, policy: VideoRatePolicy, events: EventBuffer,
                              shot_id: str, candidate_id: str) -> dict[str, Any]:
        for attempt in range(policy.max_retries + 1):
            waited = bucket.acquire()
            if waited:
                events.emit("video.rate.waited", "video-rate", f"Waited {waited:.2f}s for video request capacity.",
                            confidence=1.0, payload={"shot_id": shot_id, "candidate_id": candidate_id,
                                                     "wait_seconds": waited})

            def relay(value: dict[str, Any]) -> None:
                events.emit("video.provider.progress", "video-provider",
                            str(value.get("message") or "Video provider changed state."),
                            progress=_float_or_none(value.get("progress")), confidence=0.95,
                            payload={"shot_id": shot_id, "candidate_id": candidate_id, **value})

            try:
                return call(relay)
            except VideoRateLimited as exc:
                if attempt >= policy.max_retries:
                    raise
                exponential = min(policy.max_backoff_seconds,
                                  policy.base_backoff_seconds * math.pow(2, attempt))
                delay = max(exc.retry_after or 0.0, exponential)
                delay += self.random.uniform(0.0, max(0.01, delay * 0.12))
                events.emit("video.rate.cooldown", "video-rate",
                            f"Provider throttled the video request; cooling down for {delay:.2f}s.",
                            confidence=1.0, payload={"shot_id": shot_id, "candidate_id": candidate_id,
                                                     "attempt": attempt + 1, "wait_seconds": delay})
                self.sleeper(delay)
        raise AssertionError("unreachable")

    @staticmethod
    def _candidate_from_response(shot: ShotSpec, candidate_id: str, response: dict[str, Any], output_dir: Path,
                                 parent_candidate_id: str | None = None, repair_index: int = 0) -> VideoCandidate:
        if response.get("status") != "completed":
            raise VideoRuntimeError(str(response.get("error") or "video generation did not complete"))
        raw_path = response.get("video_path")
        if not isinstance(raw_path, str):
            raise VideoRuntimeError("video adapter did not return video_path")
        path = Path(raw_path).expanduser().resolve()
        try:
            path.relative_to(output_dir.resolve())
        except ValueError as exc:
            raise VideoRuntimeError("video adapter output escaped its candidate directory") from exc
        if not path.is_file():
            raise VideoRuntimeError(f"video adapter output is missing: {path}")
        return VideoCandidate(
            candidate_id=candidate_id,
            shot_id=shot.shot_id,
            video_path=path,
            provider_job_id=str(response["provider_job_id"]) if response.get("provider_job_id") else None,
            parent_candidate_id=parent_candidate_id,
            repair_index=repair_index,
            metrics=dict(response.get("metrics") or {}),
            notes=[str(note) for note in response.get("notes") or []],
        )

    def _evaluate(self, candidate: VideoCandidate, shot: ShotSpec, events: EventBuffer) -> None:
        if self.evaluator:
            value = self.evaluator.evaluate({
                "schema_version": "1.0",
                "shot_id": shot.shot_id,
                "candidate_id": candidate.candidate_id,
                "video_path": str(candidate.video_path),
                "reference_image": str(shot.reference_image),
                "prompt": shot.prompt,
                "preserve": list(shot.preserve),
                "motion": list(shot.motion),
                "avoid": list(shot.avoid),
            })
            if value.get("status") != "completed":
                raise VideoRuntimeError(str(value.get("error") or "video evaluation failed"))
            candidate.metrics.update(value.get("metrics") or {})
            candidate.notes.extend(str(note) for note in value.get("notes") or [])
        candidate.score, score_notes = score_metrics(candidate.metrics)
        candidate.notes.extend(score_notes)
        events.emit("video.candidate.scored", "video-evaluation",
                    f"Scored {candidate.candidate_id} for {shot.shot_id} at {candidate.score:.3f}.",
                    confidence=0.9, payload={"shot_id": shot.shot_id, "candidate": candidate.public()})

    @staticmethod
    def _repair_issues(metrics: dict[str, Any]) -> list[str]:
        targets = [
            ("identity stability", metrics.get("identity_stability")),
            ("temporal consistency", metrics.get("temporal_consistency")),
            ("motion quality", metrics.get("motion_quality")),
            ("orb-hand continuity", metrics.get("orb_hand_continuity")),
            ("artifact suppression", 1.0 - float(metrics.get("artifact_penalty", 1.0))),
        ]
        ranked = sorted(targets, key=lambda item: float(item[1]) if item[1] is not None else -1.0)
        return [name for name, _ in ranked[:2]]
