#!/usr/bin/env python3
"""Normalize and gate recoverable project intake records using only stdlib."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

VALID_STATES = {
    "DISCOVERED", "TRIAGED", "SPECIFIED", "READY", "ACTIVE",
    "VERIFYING", "RELEASED", "RECOVERING", "BLOCKED", "ARCHIVED",
}

REQUIRED_TOP = {
    "schema_version", "kind", "project_id", "state", "release_target",
    "evidence", "unknowns", "next_action",
}


def fail(message: str) -> None:
    raise ValueError(message)


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("intake record must be a JSON object")
    return data


def validate(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_TOP - record.keys())
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")
    if record.get("schema_version") != "1.0.0":
        errors.append("schema_version must be 1.0.0")
    if record.get("kind") != "studio.project-intake":
        errors.append("kind must be studio.project-intake")
    if record.get("state") not in VALID_STATES:
        errors.append(f"invalid state: {record.get('state')!r}")

    target = record.get("release_target")
    if not isinstance(target, dict) or not target.get("period") or not target.get("outcome"):
        errors.append("release_target.period and release_target.outcome are required")

    evidence = record.get("evidence")
    if not isinstance(evidence, list):
        errors.append("evidence must be a list")
    else:
        for i, item in enumerate(evidence):
            if not isinstance(item, dict):
                errors.append(f"evidence[{i}] must be an object")
                continue
            for key in ("observed_at", "kind", "ref", "claim"):
                if not item.get(key):
                    errors.append(f"evidence[{i}].{key} is required")
            if item.get("observed_at"):
                try:
                    datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00"))
                except Exception:
                    errors.append(f"evidence[{i}].observed_at is not ISO-8601")

    unknowns = record.get("unknowns")
    if not isinstance(unknowns, list):
        errors.append("unknowns must be a list")

    next_action = record.get("next_action")
    if not isinstance(next_action, dict) or not next_action.get("action") or not next_action.get("justification"):
        errors.append("next_action.action and next_action.justification are required")

    if record.get("state") == "RECOVERING":
        recovery = record.get("recovery")
        if not isinstance(recovery, dict):
            errors.append("RECOVERING requires recovery record")
        else:
            for key in ("status", "timeline", "last_defensible_state", "contradictions", "unresolved", "smallest_repair"):
                if key not in recovery:
                    errors.append(f"recovery.{key} is required")

    return errors


def classify(record: dict[str, Any]) -> dict[str, Any]:
    errors = validate(record)
    blocking_unknowns = [
        u.get("question", "unnamed unknown")
        for u in record.get("unknowns", [])
        if isinstance(u, dict) and u.get("required_for_next_action") is True
    ]
    recovery = record.get("recovery") if isinstance(record.get("recovery"), dict) else {}
    recovery_status = recovery.get("status", "NOT_REQUIRED")

    if errors:
        disposition = "INVALID"
    elif recovery_status in {"REQUIRED", "IN_PROGRESS"} or record.get("state") == "RECOVERING":
        disposition = "RECOVER"
    elif blocking_unknowns:
        disposition = "BLOCKED_ON_REQUIRED_UNKNOWN"
    elif record.get("state") in {"READY", "ACTIVE", "VERIFYING"}:
        disposition = "ACTIONABLE"
    elif record.get("state") == "RELEASED":
        disposition = "VERIFY_RELEASE"
    elif record.get("state") == "ARCHIVED":
        disposition = "NO_ACTION"
    else:
        disposition = "TRIAGE"

    return {
        "project_id": record.get("project_id"),
        "state": record.get("state"),
        "disposition": disposition,
        "blocking_unknowns": blocking_unknowns,
        "validation_errors": errors,
        "next_action": record.get("next_action"),
        "principle": "ignore non-required unknowns; act only from supported evidence",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and classify a recoverable project intake record")
    parser.add_argument("record", type=Path)
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args()

    try:
        result = classify(load(args.record))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"intake error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['project_id']}: {result['disposition']} ({result['state']})")
        if result["validation_errors"]:
            for error in result["validation_errors"]:
                print(f"  error: {error}")
        for unknown in result["blocking_unknowns"]:
            print(f"  blocking unknown: {unknown}")
        action = result.get("next_action") or {}
        if action.get("action"):
            print(f"  next: {action['action']}")

    return 1 if result["validation_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
