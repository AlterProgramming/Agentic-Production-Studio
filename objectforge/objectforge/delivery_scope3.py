from __future__ import annotations

from pathlib import Path
from typing import Any

import trimesh

from objectforge.delivery_scope1 import viewer_html
from objectforge.design.language import DesignLanguage, apply_design_language, design_languages
from objectforge.evaluation.design import evaluate_design_language, evaluate_language_set
from objectforge.evaluation.functional import evaluate_functional_builder, evaluate_functional_plan
from objectforge.evaluation.quality import evaluate_builder, evaluate_close_inspection, evaluate_glb
from objectforge.functional.refined import build_functional_architecture
from objectforge.geometry import sha256_bytes, write_json
from objectforge.gltf import pack_glb, parse_glb
from objectforge.planning.functional import FunctionalBrief, FunctionalPlan, benchmark_briefs, default_planner
from objectforge.runtime_glb import patch_runtime_glb


def _patch_design_metadata(data: bytes, *, builder, language: DesignLanguage, showcase: bool) -> bytes:
    document, binary = parse_glb(data)
    payload = {
        "language_id": language.language_id,
        "fingerprint": language.fingerprint,
        "contract": "../design/design-language.json",
        "application_receipt": "../design/application-receipt.json",
    }
    document.setdefault("asset", {}).setdefault("extras", {}).setdefault("objectforge", {})["design_language"] = payload
    for node in document.get("nodes", []):
        if node.get("name") == builder.root_name:
            node.setdefault("extras", {}).setdefault("objectforge", {})["design_language"] = payload
            break
    document["buffers"][0]["byteLength"] = len(binary)
    return pack_glb(document, binary)


def _requirement_coverage(plan: FunctionalPlan) -> dict[str, Any]:
    selected = next(item for item in plan.candidates if item.architecture_id == plan.selected_architecture.architecture_id)
    covered = set(selected.covered)
    return {
        "schema_version": "1.0",
        "brief_id": plan.brief.brief_id,
        "selected_architecture": selected.architecture_id,
        "all_mandatory_covered": not selected.missing_mandatory,
        "requirements": [{**item.to_dict(), "covered": item.requirement_id in covered, "evidence": "functional.verify operation and semantic/physics contracts"} for item in plan.brief.requirements],
    }


def build_designed_asset(plan: FunctionalPlan, language: DesignLanguage, output_root: Path) -> dict[str, Any]:
    plan_eval = evaluate_functional_plan(plan)
    if not plan_eval.passed:
        raise ValueError(f"functional plan failed: {plan_eval.failures}")

    builder = build_functional_architecture(plan)
    base_builder_eval = evaluate_builder(builder)
    functional_eval = evaluate_functional_builder(builder, plan)
    base_close_eval = evaluate_close_inspection(builder)
    if not base_builder_eval.passed or not functional_eval.passed or not base_close_eval.passed:
        raise ValueError("base functional builder failed before design-language application: " f"{base_builder_eval.failures + functional_eval.failures + base_close_eval.failures}")

    apply_design_language(builder, language)
    builder_eval = evaluate_builder(builder)
    close_eval = evaluate_close_inspection(builder)
    design_eval = evaluate_design_language(builder, language)
    if not builder_eval.passed or not close_eval.passed or not design_eval.passed:
        raise ValueError(f"designed builder failed: {builder_eval.failures + close_eval.failures + design_eval.failures}")

    object_dir = output_root / "object"
    showcase_dir = output_root / "showcase"
    behavior_dir = output_root / "behavior"
    construction_dir = output_root / "construction"
    design_dir = output_root / "design"
    evaluation_dir = output_root / "evaluation"
    recovery_dir = output_root / "recovery"
    for directory in (object_dir, showcase_dir / "viewer", behavior_dir, construction_dir, design_dir, evaluation_dir, recovery_dir):
        directory.mkdir(parents=True, exist_ok=True)

    operations = builder.operation_jsonl()
    construction_hash = sha256_bytes(operations)
    canonical_raw = trimesh.exchange.gltf.export_glb(builder.build_scene(False), include_normals=True)
    canonical = _patch_design_metadata(patch_runtime_glb(canonical_raw, builder=builder, construction_hash=construction_hash, showcase=False), builder=builder, language=language, showcase=False)
    (object_dir / "object.glb").write_bytes(canonical)
    showcase_raw = trimesh.exchange.gltf.export_glb(builder.build_scene(True), include_normals=True)
    showcase = _patch_design_metadata(patch_runtime_glb(showcase_raw, builder=builder, construction_hash=construction_hash, showcase=True), builder=builder, language=language, showcase=True)
    (showcase_dir / "object-showcase.glb").write_bytes(showcase)

    write_json(object_dir / "semantic-parts.json", builder.semantic_contract())
    write_json(object_dir / "materials.json", builder.material_contract())
    write_json(behavior_dir / "physics.json", builder.physics_contract())
    write_json(behavior_dir / "animations.json", {"schema_version": "1.0", "clips": ([{"name": "functional_demo", "duration_seconds": 6.0, "loop": True, "joints": [item.id for item in builder.articulations]}] if builder.articulations else []), "embedded_in_glb": bool(builder.articulations)})
    write_json(behavior_dir / "interactions.json", builder.interaction)
    (construction_dir / "operations.jsonl").write_bytes(operations)
    write_json(construction_dir / "functional-brief.json", plan.brief.to_dict())
    write_json(construction_dir / "functional-plan.json", plan.to_dict())
    write_json(construction_dir / "candidate-comparison.json", {"schema_version": "1.0", "selected": plan.selected_architecture.architecture_id, "candidates": [item.to_dict() for item in plan.candidates]})
    write_json(design_dir / "design-language.json", language.to_dict())
    write_json(design_dir / "application-receipt.json", {"schema_version": "1.0", "language_id": language.language_id, "fingerprint": language.fingerprint, "selected_architecture": plan.selected_architecture.architecture_id, "material_roles": language.material_roles, "proportion_tokens": language.proportion_tokens, "surface_tokens": language.surface_tokens, "interaction_tokens": language.interaction_tokens, "external_design_provider": False})
    coverage = _requirement_coverage(plan)
    write_json(evaluation_dir / "requirement-coverage.json", coverage)
    write_json(evaluation_dir / "design-language.json", {"passed": design_eval.passed, "metrics": design_eval.metrics, "failures": list(design_eval.failures)})
    write_json(recovery_dir / "receipt.json", {"schema_version": "1.0", **builder.recovery, "construction_sha256": construction_hash, "selected_architecture": plan.selected_architecture.architecture_id, "design_language": language.language_id, "external_finished_model_provider": False})
    (showcase_dir / "viewer" / "index.html").write_text(viewer_html(f"{plan.asset_id}-{language.language_id}"), encoding="utf-8")

    glb_eval = evaluate_glb(canonical, minimum_meshes=max(int(plan.acceptance["minimum_meshes"]), 48), require_animation=bool(builder.articulations), root_name=builder.root_name)
    validation = {
        "passed": plan_eval.passed and functional_eval.passed and builder_eval.passed and close_eval.passed and design_eval.passed and glb_eval.passed and coverage["all_mandatory_covered"],
        "plan": plan_eval.metrics,
        "base_functional": functional_eval.metrics,
        "builder": builder_eval.metrics,
        "close_inspection": close_eval.metrics,
        "design_language": design_eval.metrics,
        "asset": glb_eval.metrics,
        "failures": list(plan_eval.failures + functional_eval.failures + builder_eval.failures + close_eval.failures + design_eval.failures + glb_eval.failures),
    }
    write_json(output_root / "validation.json", validation)

    files = []
    for path in sorted(item for item in output_root.rglob("*") if item.is_file()):
        payload = path.read_bytes()
        files.append({"path": path.relative_to(output_root).as_posix(), "bytes": len(payload), "sha256": sha256_bytes(payload)})
    manifest = {
        "schema_version": "1.0",
        "kind": "objectforge.scope3-designed-functional-asset-manifest",
        "asset_id": plan.asset_id,
        "brief_id": plan.brief.brief_id,
        "object_class_input": None,
        "selected_architecture": plan.selected_architecture.architecture_id,
        "design_language": language.language_id,
        "design_language_fingerprint": language.fingerprint,
        "canonical_model": "object/object.glb",
        "showcase_model": "showcase/object-showcase.glb",
        "viewer": "showcase/viewer/index.html",
        "functional_brief": "construction/functional-brief.json",
        "decision_trace": "construction/candidate-comparison.json",
        "design_contract": "design/design-language.json",
        "design_receipt": "design/application-receipt.json",
        "requirement_coverage": "evaluation/requirement-coverage.json",
        "design_evaluation": "evaluation/design-language.json",
        "physics": "behavior/physics.json",
        "recovery_receipt": "recovery/receipt.json",
        "validation": validation,
        "goal_directed": True,
        "design_language_driven": True,
        "external_finished_model_provider": False,
        "files": files,
    }
    write_json(output_root / "manifest.json", manifest)
    return manifest


def build_scope3(output_root: Path, *, briefs: tuple[FunctionalBrief, ...] | None = None, languages: tuple[DesignLanguage, ...] | None = None) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    planner = default_planner()
    briefs = briefs or benchmark_briefs()
    languages = languages or design_languages()
    records: list[dict[str, Any]] = []

    for language in languages:
        for brief in briefs:
            plan = planner.plan(brief)
            asset_root = output_root / language.language_id / brief.brief_id
            manifest = build_designed_asset(plan, language, asset_root)
            records.append({
                "asset_id": plan.asset_id,
                "brief_id": brief.brief_id,
                "selected_architecture": plan.selected_architecture.architecture_id,
                "language_id": language.language_id,
                "language_fingerprint": language.fingerprint,
                "style_signature_hash": manifest["validation"]["design_language"]["fingerprint"],
                "path": asset_root.relative_to(output_root).as_posix(),
                "passed": manifest["validation"]["passed"],
                "geometry_components": manifest["validation"]["builder"]["geometry_components"],
                "design_motif_components": manifest["validation"]["design_language"]["motif_components"],
                "canonical_sha256": next(item["sha256"] for item in manifest["files"] if item["path"] == "object/object.glb"),
            })

    set_eval = evaluate_language_set(records, languages)
    status = "passed" if all(item["passed"] for item in records) and set_eval.passed else "failed"
    index = {
        "schema_version": "1.0",
        "capability_id": "objectforge.procedural-design-language.v1",
        "scope": "ObjectForge Scope 3",
        "status": status,
        "assets": records,
        "design_languages": [item.to_dict() for item in languages],
        "briefs_without_object_class": all(brief.to_dict()["object_class"] is None for brief in briefs),
        "language_matrix": {"languages": len(languages), "briefs": len(briefs), "assets": len(records)},
        "coherence_evaluation": {"passed": set_eval.passed, "metrics": set_eval.metrics, "failures": list(set_eval.failures)},
        "scope0_scope1_scope2_regression_required": True,
        "external_finished_model_provider": False,
    }
    write_json(output_root / "scope3-index.json", index)
    return index
