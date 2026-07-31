from __future__ import annotations

import json
from pathlib import Path

from objectforge.delivery_scope1 import build_asset, build_scope1
from objectforge.planning.planner import Scope1Planner


def test_scope1_planner_exposes_three_families_and_nine_variants() -> None:
    variants = Scope1Planner.variants()
    assert len(variants) == 9
    assert {family for family, _ in variants} == {"lamp", "case", "table"}
    assert all(len(Scope1Planner.resolve(*key).grammars) >= 4 for key in variants)


def test_one_variant_per_family_builds_detailed_standalone_glb(tmp_path: Path) -> None:
    for family, variant in (("lamp", "compact"), ("case", "tool"), ("table", "four_leg")):
        manifest = build_asset(Scope1Planner.resolve(family, variant), tmp_path / family)
        assert manifest["validation"]["passed"] is True
        assert manifest["validation"]["builder"]["geometry_components"] >= 18
        assert (tmp_path / family / "object/object.glb").stat().st_size > 100_000
        assert (tmp_path / family / "showcase/object-showcase.glb").stat().st_size > 100_000
        receipt = json.loads((tmp_path / family / "recovery/receipt.json").read_text())
        assert receipt["rollback"]["preserved_prior_state"] is True


def test_scope1_builds_all_variants_and_reuses_grammars(tmp_path: Path) -> None:
    index = build_scope1(tmp_path / "scope1")
    assert index["status"] == "passed"
    assert len(index["assets"]) == 9
    assert index["diversity"]["passed"] is True
    assert len(index["grammar_reuse"]["support"]) >= 5
    assert len(index["grammar_reuse"]["shell"]) >= 6
    assert all(item["passed"] for item in index["assets"])
