#!/usr/bin/env python3
"""Validate the mnemonic body-artifact separation contract without dependencies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_LAYERS = {"embodied", "artifacts", "interactions", "provenance", "hypotheses"}
SOURCE_CLASSES = {"embodied", "artifact", "environmental", "inferred", "conflicting"}
HYPOTHESIS_MODES = {"body_dominant", "artifact_dominant", "unresolved", "conservative"}


def validate_scene(scene: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    layers = scene.get("layers")
    if not isinstance(scene.get("scene_id"), str) or not scene["scene_id"].strip():
        errors.append("scene_id is required")
    if not isinstance(layers, dict):
        return errors + ["layers must be an object"]
    missing = REQUIRED_LAYERS - set(layers)
    if missing:
        errors.append(f"missing layers: {sorted(missing)}")
        return errors

    embodied = layers.get("embodied")
    artifacts = layers.get("artifacts")
    interactions = layers.get("interactions")
    provenance = layers.get("provenance")
    hypotheses = layers.get("hypotheses")
    for name, value, minimum in (
        ("embodied", embodied, 1),
        ("artifacts", artifacts, 1),
        ("interactions", interactions, 0),
        ("provenance", provenance, 1),
        ("hypotheses", hypotheses, 1),
    ):
        if not isinstance(value, list) or len(value) < minimum:
            errors.append(f"{name} must be an array with at least {minimum} item(s)")

    if errors:
        return errors

    def ids(items: list[dict[str, Any]], label: str) -> set[str]:
        values: set[str] = set()
        for index, item in enumerate(items):
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                errors.append(f"{label}[{index}].id is required")
                continue
            if item["id"] in values:
                errors.append(f"duplicate {label} id: {item['id']}")
            values.add(item["id"])
        return values

    body_ids = ids(embodied, "embodied")
    artifact_ids = ids(artifacts, "artifacts")
    if body_ids & artifact_ids:
        errors.append(f"body and artifact ids must be disjoint: {sorted(body_ids & artifact_ids)}")
    object_ids = body_ids | artifact_ids

    for index, item in enumerate(interactions):
        if not isinstance(item, dict):
            errors.append(f"interactions[{index}] must be an object")
            continue
        body_ref = item.get("body_ref")
        artifact_ref = item.get("artifact_ref")
        if body_ref not in body_ids:
            errors.append(f"interactions[{index}].body_ref is unknown: {body_ref}")
        if artifact_ref not in artifact_ids:
            errors.append(f"interactions[{index}].artifact_ref is unknown: {artifact_ref}")

    covered: set[str] = set()
    for index, item in enumerate(provenance):
        if not isinstance(item, dict):
            errors.append(f"provenance[{index}] must be an object")
            continue
        object_ref = item.get("object_ref")
        if object_ref not in object_ids:
            errors.append(f"provenance[{index}].object_ref is unknown: {object_ref}")
        else:
            covered.add(object_ref)
        if item.get("source_class") not in SOURCE_CLASSES:
            errors.append(f"provenance[{index}].source_class is invalid")
        confidence = item.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            errors.append(f"provenance[{index}].confidence must be between 0 and 1")
    missing_provenance = object_ids - covered
    if missing_provenance:
        errors.append(f"objects missing provenance: {sorted(missing_provenance)}")

    modes: set[str] = set()
    for index, item in enumerate(hypotheses):
        if not isinstance(item, dict):
            errors.append(f"hypotheses[{index}] must be an object")
            continue
        mode = item.get("mode")
        if mode not in HYPOTHESIS_MODES:
            errors.append(f"hypotheses[{index}].mode is invalid")
        else:
            modes.add(mode)
        disputed = item.get("disputed_properties")
        if not isinstance(disputed, list):
            errors.append(f"hypotheses[{index}].disputed_properties must be an array")
    if "unresolved" not in modes and len(modes) < 2:
        errors.append("preserve an unresolved hypothesis or at least two alternative modes")

    checks = scene.get("reuse_checks")
    if not isinstance(checks, dict):
        errors.append("reuse_checks must be an object")
    else:
        for key in ("reopen", "alternate_pose", "alternate_garment_state", "alternate_camera"):
            if checks.get(key) is not True:
                errors.append(f"reuse_checks.{key} must be true")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scene", type=Path)
    args = parser.parse_args()
    scene = json.loads(args.scene.read_text(encoding="utf-8"))
    errors = validate_scene(scene)
    if errors:
        for error in errors:
            print(f"mnemonic-scene error: {error}")
        return 1
    print(f"mnemonic scene valid: {scene['scene_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
