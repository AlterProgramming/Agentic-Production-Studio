from __future__ import annotations

import json
from pathlib import Path

from objectforge.gltf import parse_glb
from objectforge.task_lamp import build_package


def test_scope0_builds_standalone_detailed_asset(tmp_path: Path) -> None:
    manifest = build_package(tmp_path / "run")
    assert manifest["validation"]["passed"] is True
    document, binary = parse_glb((tmp_path / "run/object/object.glb").read_bytes())
    assert binary
    assert len(document.get("meshes", [])) >= 25
    assert len(document.get("materials", [])) >= 7
    assert len(document.get("images", [])) >= 6
    assert document.get("animations")
    assert "KHR_lights_punctual" in document.get("extensionsUsed", [])
    assert not [image for image in document.get("images", []) if image.get("uri")]


def test_recovery_preserves_failed_attempt_and_rolls_back(tmp_path: Path) -> None:
    build_package(tmp_path / "run")
    receipt = json.loads((tmp_path / "run/recovery/receipt.json").read_text())
    assert receipt["status"] == "recovered"
    assert receipt["forced_failure"]["metrics"]["stable"] is False
    assert receipt["rollback"]["replacement_metrics"]["stable"] is True
    assert receipt["source_overwritten"] is False


def test_physics_and_semantics_are_retained(tmp_path: Path) -> None:
    build_package(tmp_path / "run")
    physics = json.loads((tmp_path / "run/behavior/physics.json").read_text())
    semantic = json.loads((tmp_path / "run/object/semantic-parts.json").read_text())
    assert len(physics["constraints"]) == 3
    assert len(physics["bodies"]) == 4
    assert "shade.outer_shell" in semantic["semantic_parts"]
    assert "joint.base_fastener" in semantic["semantic_parts"]
