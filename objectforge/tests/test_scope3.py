from __future__ import annotations

import json
from pathlib import Path

from objectforge.delivery_scope3 import build_designed_asset, build_scope3
from objectforge.design.language import design_languages
from objectforge.planning.functional import benchmark_briefs, default_planner


def test_scope3_declares_two_distinct_design_languages() -> None:
    languages = design_languages()
    assert len(languages) == 2
    assert len({item.language_id for item in languages}) == 2
    assert len({item.fingerprint for item in languages}) == 2
    assert all(len(item.material_roles) >= 7 for item in languages)
    assert all(item.surface_tokens["fastener_style"] for item in languages)


def test_scope3_applies_language_without_changing_functional_architecture(tmp_path: Path) -> None:
    planner = default_planner()
    brief = benchmark_briefs()[0]
    plan = planner.plan(brief)
    hashes = set()
    for language in design_languages():
        root = tmp_path / language.language_id
        manifest = build_designed_asset(plan, language, root)
        assert manifest["validation"]["passed"] is True
        assert manifest["selected_architecture"] == plan.selected_architecture.architecture_id
        assert manifest["design_language"] == language.language_id
        assert manifest["validation"]["design_language"]["motif_components"] >= 10
        assert manifest["validation"]["design_language"]["role_material_count"] >= 5
        assert manifest["validation"]["close_inspection"]["detail_components"] >= 18
        assert (root / "design/design-language.json").is_file()
        assert (root / "object/object.glb").stat().st_size > 250_000
        validation = json.loads((root / "validation.json").read_text())
        hashes.add(next(item["sha256"] for item in manifest["files"] if item["path"] == "object/object.glb"))
        assert validation["design_language"]["fingerprint"] == language.fingerprint
    assert len(hashes) == 2


def test_scope3_builds_complete_language_by_brief_matrix(tmp_path: Path) -> None:
    index = build_scope3(tmp_path / "scope3")
    assert index["status"] == "passed"
    assert index["capability_id"] == "objectforge.procedural-design-language.v1"
    assert index["language_matrix"] == {"languages": 2, "briefs": 4, "assets": 8}
    assert index["coherence_evaluation"]["passed"] is True
    assert index["coherence_evaluation"]["metrics"]["paired_architecture_invariance"] is True
    assert index["coherence_evaluation"]["metrics"]["paired_model_distinction"] is True
    assert all(item["passed"] for item in index["assets"])
