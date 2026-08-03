from __future__ import annotations

import hashlib
import json
import random
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence


class RecreationError(RuntimeError):
    pass


class ProviderError(RecreationError):
    pass


class RateLimitError(ProviderError):
    def __init__(self, message: str = "provider rate limited the request", retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class EventSink(Protocol):
    def emit(self, event_type: str, phase: str, message: str, *, progress: float | None = None,
             confidence: float | None = None, payload: dict[str, Any] | None = None) -> Any: ...


@dataclass(frozen=True)
class RatePolicy:
    requests_per_minute: float = 4.0
    burst: int = 1
    max_retries: int = 4
    base_backoff_seconds: float = 2.0
    max_backoff_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not 0.1 <= self.requests_per_minute <= 120:
            raise RecreationError("requests_per_minute must be between 0.1 and 120")
        if not 1 <= self.burst <= 16:
            raise RecreationError("burst must be between 1 and 16")
        if not 0 <= self.max_retries <= 10:
            raise RecreationError("max_retries must be between 0 and 10")
        if not 0 <= self.base_backoff_seconds <= self.max_backoff_seconds <= 900:
            raise RecreationError("invalid backoff range")


class TokenBucket:
    def __init__(self, policy: RatePolicy, *, clock: Callable[[], float] = time.monotonic,
                 sleeper: Callable[[float], None] = time.sleep) -> None:
        self.policy, self.clock, self.sleep = policy, clock, sleeper
        self.tokens, self.last = float(policy.burst), clock()

    def acquire(self) -> float:
        waited, refill = 0.0, self.policy.requests_per_minute / 60.0
        while True:
            now = self.clock()
            self.tokens = min(float(self.policy.burst), self.tokens + max(0.0, now - self.last) * refill)
            self.last = now
            if self.tokens >= 1:
                self.tokens -= 1
                return waited
            delay = (1 - self.tokens) / refill
            self.sleep(delay)
            waited += delay


@dataclass(frozen=True)
class RecreationConfig:
    reference_image: Path
    output_root: Path
    goal: str
    anchors: tuple[str, ...] = ()
    preserve: tuple[str, ...] = ()
    avoid: tuple[str, ...] = ()
    max_iterations: int = 6
    candidates_per_iteration: int = 2
    target_score: float = 0.92
    patience: int = 3
    minimum_improvement: float = 0.01
    rate_policy: RatePolicy = field(default_factory=RatePolicy)
    resume_job_id: str | None = None

    def __post_init__(self) -> None:
        if not self.goal.strip():
            raise RecreationError("goal must not be empty")
        if not 1 <= self.max_iterations <= 50 or not 1 <= self.candidates_per_iteration <= 8:
            raise RecreationError("invalid iteration budget")
        if not 0 <= self.target_score <= 1 or not 0 <= self.minimum_improvement <= 1:
            raise RecreationError("scores must be between 0 and 1")
        if not 1 <= self.patience <= 20:
            raise RecreationError("patience must be between 1 and 20")


@dataclass
class Candidate:
    candidate_id: str
    iteration: int
    index: int
    variant: str
    prompt: str
    parent_image: str
    image_path: str
    metrics: dict[str, float]
    score: float
    notes: list[str] = field(default_factory=list)
    artifact_key: str | None = None

    def public(self, *, include_path: bool = False) -> dict[str, Any]:
        value = asdict(self)
        if not include_path:
            value.pop("image_path", None)
            value.pop("parent_image", None)
        return value


class CommandAdapter:
    def __init__(self, command: Sequence[str], *, timeout_seconds: float = 600.0) -> None:
        self.command = tuple(str(x) for x in command if str(x))
        self.timeout_seconds = timeout_seconds
        if not self.command:
            raise RecreationError("provider command must not be empty")

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            done = subprocess.run(self.command, input=json.dumps(payload), text=True, encoding="utf-8",
                                  capture_output=True, timeout=self.timeout_seconds, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ProviderError("provider timed out") from exc
        except OSError as exc:
            raise ProviderError(f"provider could not be started: {exc}") from exc
        response = None
        if done.stdout.strip():
            try:
                parsed = json.loads(done.stdout.strip().splitlines()[-1])
                response = parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError as exc:
                raise ProviderError(f"provider emitted invalid JSON: {exc}") from exc
        if done.returncode == 75 or (response and response.get("status") == "rate_limited"):
            raw = (response or {}).get("retry_after")
            try:
                retry_after = float(raw) if raw is not None else None
            except (TypeError, ValueError):
                retry_after = None
            raise RateLimitError(str((response or {}).get("error") or done.stderr or "rate limited"), retry_after)
        if done.returncode or response is None:
            raise ProviderError(done.stderr.strip() or f"provider exited with {done.returncode}")
        if response.get("status", "completed") not in {"completed", "ok"}:
            raise ProviderError(str(response.get("error") or response.get("status")))
        return response


class CommandImageGenerator:
    def __init__(self, command: Sequence[str], *, timeout_seconds: float = 600.0) -> None:
        self.adapter = CommandAdapter(command, timeout_seconds=timeout_seconds)

    def generate(self, request: dict[str, Any], output_directory: Path) -> dict[str, Any]:
        output_directory = output_directory.resolve()
        output_directory.mkdir(parents=True, exist_ok=True)
        response = self.adapter.invoke({"schema_version": "1.0", "operation": "generate", **request,
                                        "output_directory": str(output_directory)})
        image = Path(str(response.get("image_path", ""))).expanduser().resolve()
        try:
            image.relative_to(output_directory)
        except ValueError as exc:
            raise ProviderError("generator image_path escaped its candidate directory") from exc
        if not image.is_file():
            raise ProviderError(f"generator image_path does not exist: {image}")
        response["image_path"] = str(image)
        return response


class CommandImageEvaluator:
    def __init__(self, command: Sequence[str], *, timeout_seconds: float = 300.0) -> None:
        self.adapter = CommandAdapter(command, timeout_seconds=timeout_seconds)

    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.adapter.invoke({"schema_version": "1.0", "operation": "evaluate", **request})


WEIGHTS = {"subject_retention": .35, "anchor_retention": .20, "environment_match": .20,
           "aesthetic_quality": .15, "composition_stability": .10}


def score_metrics(raw: dict[str, Any] | None) -> tuple[dict[str, float], float, list[str]]:
    raw, metrics, notes = raw or {}, {}, []
    for key in (*WEIGHTS, "drift_penalty"):
        try:
            value = max(0.0, min(1.0, float(raw[key])))
        except (KeyError, TypeError, ValueError):
            value = 0.0
            notes.append(f"missing or invalid metric: {key}")
        metrics[key] = value
    score = sum(metrics[k] * w for k, w in WEIGHTS.items()) - metrics["drift_penalty"]
    return metrics, max(0.0, min(1.0, score)), notes


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RecreationPipeline:
    VARIANTS = (
        ("identity-preservation", "Preserve facial identity, expression, silhouette, and close framing."),
        ("world-integration", "Improve environmental authenticity without letting the world dominate the subject."),
        ("gesture-relationship", "Clarify the spatial relationship between hand, gesture, and focal object."),
        ("material-fidelity", "Increase believable material texture while avoiding plastic sheen and ornamental noise."),
        ("emotional-clarity", "Strengthen the frame's emotional read through light, posture, and negative space."),
    )

    def __init__(self, generator: CommandImageGenerator, *, evaluator: CommandImageEvaluator | None = None,
                 clock: Callable[[], float] = time.monotonic, sleeper: Callable[[float], None] = time.sleep,
                 rng: random.Random | None = None) -> None:
        self.generator, self.evaluator = generator, evaluator
        self.clock, self.sleep, self.rng = clock, sleeper, rng or random.Random()

    @staticmethod
    def _state_path(root: Path, job_id: str) -> Path:
        return root / job_id / "state.json"

    @staticmethod
    def _write(path: Path, state: dict[str, Any]) -> None:
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(path)

    def _retry(self, call: Callable[[], dict[str, Any]], policy: RatePolicy, events: EventSink,
               progress: float, *, paced: TokenBucket | None = None) -> dict[str, Any]:
        for attempt in range(policy.max_retries + 1):
            if paced:
                waited = paced.acquire()
                if waited:
                    events.emit("rate.wait", "rate-control", f"Waited {waited:.2f}s for request capacity.",
                                progress=progress, confidence=1.0, payload={"wait_seconds": waited})
            try:
                return call()
            except RateLimitError as exc:
                if attempt >= policy.max_retries:
                    raise
                backoff = min(policy.max_backoff_seconds,
                              policy.base_backoff_seconds * (2 ** attempt) + self.rng.random())
                delay = max(backoff, exc.retry_after or 0.0)
                if delay <= 0:
                    delay = .5
                events.emit("rate.cooldown", "rate-control", f"Provider throttled; cooling down for {delay:.2f}s.",
                            progress=progress, confidence=1.0,
                            payload={"attempt": attempt + 1, "wait_seconds": delay})
                self.sleep(delay)
        raise ProviderError("retry loop exhausted")

    def _prompt(self, config: RecreationConfig, iteration: int, index: int) -> tuple[str, str]:
        variant, mutation = self.VARIANTS[((iteration - 1) * config.candidates_per_iteration + index - 1) % len(self.VARIANTS)]
        prompt = [config.goal.strip(), mutation, "Treat the supplied parent as retained state, not disposable inspiration."]
        if config.anchors:
            prompt.append("Anchors: " + "; ".join(config.anchors) + ".")
        if config.preserve:
            prompt.append("Preserve: " + "; ".join(config.preserve) + ".")
        if config.avoid:
            prompt.append("Avoid: " + "; ".join(config.avoid) + ".")
        return variant, " ".join(prompt)

    def run(self, job_id: str, config: RecreationConfig, events: EventSink,
            artifact_callback: Callable[[Candidate, bool], str | None] | None = None) -> dict[str, Any]:
        reference, root = config.reference_image.resolve(), config.output_root.resolve()
        if not reference.is_file():
            raise RecreationError(f"reference image does not exist: {reference}")
        root.mkdir(parents=True, exist_ok=True)
        active_job = config.resume_job_id or job_id
        state_path = self._state_path(root, active_job)
        state: dict[str, Any] = {
            "schema_version": "1.0", "job_id": active_job, "goal": config.goal,
            "reference_image": str(reference), "iteration_completed": 0, "candidates": [],
            "best_candidate": None, "non_improving_iterations": 0, "stopped_reason": None,
            "resumed_from": config.resume_job_id,
        }
        if config.resume_job_id:
            if not state_path.is_file():
                raise RecreationError(f"resume state not found: {state_path}")
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if not isinstance(state, dict):
                raise RecreationError("resume state must be an object")
            state["resumed_from"] = config.resume_job_id
        job_dir = root / active_job
        start = int(state.get("iteration_completed", 0)) + 1
        best = Candidate(**state["best_candidate"]) if state.get("best_candidate") else None
        parent = Path(best.image_path).resolve() if best else reference
        bucket = TokenBucket(config.rate_policy, clock=self.clock, sleeper=self.sleep)
        budget = config.max_iterations * config.candidates_per_iteration
        completed = max(0, (start - 1) * config.candidates_per_iteration)
        events.emit("run.accepted", "framing", "The recreation job has a bounded request budget and output directory.",
                    progress=.02, confidence=.99, payload={"job_id": active_job, "request_budget": budget,
                    "requests_per_minute": config.rate_policy.requests_per_minute, "burst": config.rate_policy.burst})
        events.emit("intent.interpreted", "planning", "The runtime will preserve anchors and promote only scored improvements.",
                    progress=.05, confidence=.96, payload={"anchors": list(config.anchors),
                    "preserve": list(config.preserve), "avoid": list(config.avoid)})
        self._write(state_path, state)
        stopped = "budget_exhausted"
        for iteration in range(start, config.max_iterations + 1):
            before = best.score if best else -1.0
            events.emit("iteration.started", "generation", f"Iteration {iteration} started.",
                        progress=min(.94, completed / max(1, budget)), confidence=.9,
                        payload={"iteration": iteration, "parent_image_sha256": sha256(parent)})
            for index in range(1, config.candidates_per_iteration + 1):
                completed += 1
                progress = min(.94, completed / max(1, budget))
                variant, prompt = self._prompt(config, iteration, index)
                cid = f"i{iteration:03d}-c{index:02d}"
                out = job_dir / "iterations" / f"{iteration:03d}" / f"candidate-{index:02d}"
                payload = {"job_id": active_job, "candidate_id": cid, "iteration": iteration,
                           "candidate_index": index, "goal": config.goal, "prompt": prompt, "variant": variant,
                           "reference_image": str(reference), "parent_image": str(parent),
                           "anchors": list(config.anchors), "preserve": list(config.preserve), "avoid": list(config.avoid)}
                events.emit("candidate.requested", "generation", f"Requesting {variant} candidate {cid}.",
                            progress=progress, confidence=.88, payload={"candidate_id": cid, "variant": variant})
                response = self._retry(lambda: self.generator.generate(payload, out), config.rate_policy,
                                       events, progress, paced=bucket)
                image = Path(response["image_path"]).resolve()
                events.emit("candidate.generated", "evaluation", f"Candidate {cid} is ready for evaluation.",
                            progress=progress, confidence=.94, payload={"candidate_id": cid})
                evaluation = response
                if self.evaluator:
                    evaluation = self._retry(lambda: self.evaluator.evaluate({"job_id": active_job,
                        "candidate_id": cid, "goal": config.goal, "reference_image": str(reference),
                        "parent_image": str(parent), "candidate_image": str(image),
                        "anchors": list(config.anchors), "preserve": list(config.preserve),
                        "avoid": list(config.avoid)}), config.rate_policy, events, progress)
                metrics, score, scoring_notes = score_metrics(evaluation.get("metrics"))
                candidate = Candidate(cid, iteration, index, variant, prompt, str(parent), str(image), metrics, score,
                                      [str(x) for x in evaluation.get("notes", [])] + scoring_notes)
                if artifact_callback:
                    candidate.artifact_key = artifact_callback(candidate, False)
                state.setdefault("candidates", []).append(candidate.public(include_path=True))
                events.emit("candidate.scored", "evaluation", f"Candidate {cid} scored {score:.3f}.",
                            progress=progress, confidence=.9 if not scoring_notes else .65,
                            payload={"candidate": candidate.public(), "artifact_key": candidate.artifact_key,
                                     "metrics": metrics})
                if best is None or score >= best.score + config.minimum_improvement:
                    best, parent = candidate, image
                    if artifact_callback:
                        candidate.artifact_key = artifact_callback(candidate, True) or candidate.artifact_key
                    state["best_candidate"] = candidate.public(include_path=True)
                    events.emit("best.updated", "selection", f"Candidate {cid} is the new parent at {score:.3f}.",
                                progress=progress, confidence=.93,
                                payload={"candidate": candidate.public(), "artifact_key": candidate.artifact_key,
                                         "previous_best_score": before})
                self._write(state_path, state)
            state["iteration_completed"] = iteration
            current = best.score if best else -1.0
            state["non_improving_iterations"] = 0 if current >= before + config.minimum_improvement else int(state.get("non_improving_iterations", 0)) + 1
            events.emit("iteration.completed", "selection", f"Iteration {iteration} completed with best score {max(0.0, current):.3f}.",
                        progress=min(.95, completed / max(1, budget)), confidence=.94,
                        payload={"iteration": iteration, "best_score": max(0.0, current),
                                 "non_improving_iterations": state["non_improving_iterations"]})
            self._write(state_path, state)
            if best and best.score >= config.target_score:
                stopped = "target_reached"
                break
            if state["non_improving_iterations"] >= config.patience:
                stopped = "improvement_plateau"
                break
        if best is None:
            raise RecreationError("provider produced no scoreable candidates")
        state["stopped_reason"] = stopped
        state["best_candidate"] = best.public(include_path=True)
        self._write(state_path, state)
        result = {"schema_version": "1.0", "job_id": active_job, "status": "completed",
                  "stopped_reason": stopped, "iterations_completed": state["iteration_completed"],
                  "candidate_count": len(state["candidates"]), "best": best.public(include_path=True),
                  "state_path": str(state_path), "resumed_from": state.get("resumed_from")}
        events.emit("run.completed", "result", f"Committed {best.candidate_id} at score {best.score:.3f}.",
                    progress=1.0, confidence=.97,
                    payload={"result": {**result, "best": best.public(), "state_path": None},
                             "artifact_key": best.artifact_key or "hero"})
        return result
