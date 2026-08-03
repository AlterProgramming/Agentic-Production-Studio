from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class IntentEvent:
    run_id: str
    sequence: int
    type: str
    phase: str
    message: str
    progress: float | None = None
    confidence: float | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0"
    kind: str = "studio.intent-event"
    event_id: str = field(default_factory=lambda: str(uuid4()))
    emitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), ensure_ascii=False)


class EventBuffer:
    """Append-only event stream with replay and blocking reads for SSE clients."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._events: list[IntentEvent] = []
        self._condition = threading.Condition()
        self._closed = False

    def emit(
        self,
        event_type: str,
        phase: str,
        message: str,
        *,
        progress: float | None = None,
        confidence: float | None = None,
        payload: dict[str, Any] | None = None,
    ) -> IntentEvent:
        with self._condition:
            event = IntentEvent(
                run_id=self.run_id,
                sequence=len(self._events) + 1,
                type=event_type,
                phase=phase,
                message=message,
                progress=progress,
                confidence=confidence,
                payload=payload or {},
            )
            self._events.append(event)
            self._condition.notify_all()
            return event

    def snapshot(self, after_sequence: int = 0) -> list[IntentEvent]:
        with self._condition:
            return [event for event in self._events if event.sequence > after_sequence]

    def wait(self, after_sequence: int, timeout: float = 15.0) -> tuple[list[IntentEvent], bool]:
        with self._condition:
            if not self._closed and not any(event.sequence > after_sequence for event in self._events):
                self._condition.wait(timeout)
            return (
                [event for event in self._events if event.sequence > after_sequence],
                self._closed,
            )

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()

    @property
    def closed(self) -> bool:
        with self._condition:
            return self._closed
