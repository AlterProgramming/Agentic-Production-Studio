from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import trimesh

from objectforge.delivery_scope4 import build_scope4, build_system_variant
from objectforge.design.language import get_design_language
from objectforge.evaluation.system import evaluate_system_plan
from objectforge.systems.planner import benchmark_system_brief, default_system_planner


def test_scope4_plan_covers_system_goals_and_shared_interfaces() -> None:
    plan = default_system_planner().plan(benchmark_system_brief())
    evaluation = evaluate_system_plan(plan)
    assert evaluation.passed is True
    assert plan.selected_topology == "shared_hub_and_carrier"
    assert len(plan.topology_candidates) == 4
    assert len(plan.objects) == 6
    assert len(plan.standards) == 4
    assert len(plan.endpoints) == 17
    assert len(plan.connections) == 9
    assert sum(1 for item in plan.connections if item.active_in_layout) == 6
    assert len(plan.workflows) == 2
    assert evaluation.metrics["reused_interface_standard_count"] >= 3
    assert evaluation.metrics["orphan_objects"] == []


def test_one_scope4_system_builds_six_compatible_members(tmp_path: Path) -> None:
    plan = default_system_planner().plan(benchmark_system_brief())
    root = tmp_path / "field-service-system"
    result = build_system_variant(plan, get_design_language("field_service"), root)
    assert result["passed"] is True
    assert result["object_count"] == 6
    assert result["system_mesh_count"] >= 300
    assert len(result["object_hashes"]) == 6
    assert len(set(result["object_hashes"].values())) == 6
    assert (root / "system/system.glb").stat().st_size > 1_000_000
    assert (root / "system/system-showcase.glb").stat().st_size > 1_000_000
    compatibility = json.loads((root / "system/compatibility-matrix.json").read_text())
    assert compatibility["all_declared_connections_compatible"] is True
    assert compatibility["orphan_object_count"] == 0
    validation = json.loads((root / "system/validation.json").read_text())
    assert validation["passed"] is True
    assert validation["layout"]["within_declared_footprint"] is True
    assert validation["layout"]["unpermitted_overlap_count"] == 0
    for object_id in result["object_hashes"]:
        member = root / "objects" / object_id
        assert (member / "object/object.glb").stat().st_size > 200_000
        assert json.loads((member / "validation.json").read_text())["passed"] is True
        endpoints = json.loads((member / "interfaces/endpoints.json").read_text())
        assert endpoints["endpoints"]


def test_scope4_builds_two_languages_with_one_system_plan(tmp_path: Path) -> None:
    root = tmp_path / "scope4"
    index = build_scope4(root)
    assert index["status"] == "passed"
    assert index["language_matrix"]["languages"] == 2
    assert index["language_matrix"]["objects_per_system"] == 6
    assert index["language_matrix"]["canonical_object_glbs"] == 12
    assert index["language_matrix"]["canonical_system_glbs"] == 2
    assert index["set_evaluation"]["passed"] is True
    variants = index["system_variants"]
    assert len({item["plan_fingerprint"] for item in variants}) == 1
    assert len({item["system_glb_sha256"] for item in variants}) == 2
    for role_id in variants[0]["object_hashes"]:
        assert variants[0]["object_hashes"][role_id] != variants[1]["object_hashes"][role_id]


def test_scope4_preview_normalizes_geometryless_scene_nodes() -> None:
    pytest.importorskip("cv2")
    from objectforge.smooth_preview import _apply_pose, _normalize_scene_graph

    scene = trimesh.Scene(trimesh.creation.box())
    scene.graph.update(frame_to="group_only", matrix=np.eye(4), geometry=None)

    assert scene.graph.transforms.edge_data[("world", "group_only")]["geometry"] is None
    assert scene.graph.transforms.node_data["group_only"]["geometry"] is None

    _normalize_scene_graph(scene)

    assert "geometry" not in scene.graph.transforms.edge_data[("world", "group_only")]
    assert "geometry" not in scene.graph.transforms.node_data["group_only"]

    _apply_pose(scene, {"group_only": ("x", -30.0)})

    assert "geometry" not in scene.graph.transforms.edge_data[("world", "group_only")]
    assert "geometry" not in scene.graph.transforms.node_data["group_only"]
    assert len(scene.dump(concatenate=False)) == 1
