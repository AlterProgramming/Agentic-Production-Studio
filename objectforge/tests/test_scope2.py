from __future__ import annotations

import json
from pathlib import Path

from objectforge.delivery_scope2 import build_functional_asset, build_scope2
from objectforge.planning.functional import benchmark_briefs, default_planner


def test_scope2_plans_without_object_classes_and_compares_alternatives() -> None:
    planner = default_planner()
    plans = [planner.plan(brief) for brief in benchmark_briefs()]
    assert len(plans) == 4
    assert all(plan.brief.to_dict()["object_class"] is None for plan in plans)
    assert len({plan.selected_architecture.architecture_id for plan in plans}) == 4
    assert all(len(plan.candidates) >= 8 for plan in plans)
    assert all(not next(item for item in plan.candidates if item.architecture_id == plan.selected_architecture.architecture_id).missing_mandatory for plan in plans)


def test_each_functional_brief_builds_standalone_goal_trace(tmp_path: Path) -> None:
    planner = default_planner()
    for brief in benchmark_briefs():
        root = tmp_path / brief.brief_id
        manifest = build_functional_asset(planner.plan(brief), root)
        assert manifest["validation"]["passed"] is True
        assert manifest["object_class_input"] is None
        assert manifest["validation"]["builder"]["geometry_components"] >= 28
        assert (root / "object/object.glb").stat().st_size > 100_000
        assert (root / "showcase/object-showcase.glb").stat().st_size > 100_000
        coverage = json.loads((root / "evaluation/requirement-coverage.json").read_text())
        assert coverage["all_mandatory_covered"] is True
        receipt = json.loads((root / "recovery/receipt.json").read_text())
        assert len(receipt["alternative_comparison"]) >= 2
        assert receipt["rollback"]["preserved_prior_state"] is True


def test_scope2_builds_four_distinct_goal_directed_assets(tmp_path: Path) -> None:
    index = build_scope2(tmp_path / "scope2")
    assert index["status"] == "passed"
    assert len(index["assets"]) == 4
    assert index["briefs_without_object_class"] is True
    assert index["distinct_selected_architectures"] == 4
    assert index["candidate_comparisons_per_brief"] >= 8
