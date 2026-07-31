from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from objectforge.gltf import parse_glb
from objectforge.grammar.core import GrammarAssetBuilder


@dataclass(frozen=True)
class Evaluation:
    passed: bool
    metrics: dict[str, Any]
    failures: tuple[str, ...]


def evaluate_builder(builder: GrammarAssetBuilder) -> Evaluation:
    failures: list[str] = []
    semantic_count = len({part.semantic_part for part in builder.parts})
    material_count = len({part.material for part in builder.parts})
    if len(builder.parts) < 18:
        failures.append("insufficient inspectable components")
    if semantic_count < 8:
        failures.append("semantic decomposition too shallow")
    if material_count < 4:
        failures.append("material differentiation too shallow")
    if not builder.operations:
        failures.append("missing construction ledger")
    if not builder.recovery.get("rollback", {}).get("preserved_prior_state"):
        failures.append("missing recovery proof")
    return Evaluation(
        passed=not failures,
        metrics={
            "geometry_components": len(builder.parts),
            "semantic_part_classes": semantic_count,
            "material_classes": material_count,
            "articulation_count": len(builder.articulations),
            "operation_count": len(builder.operations),
        },
        failures=tuple(failures),
    )


def evaluate_close_inspection(builder: GrammarAssetBuilder) -> Evaluation:
    """Block functionally valid but visually under-resolved Scope 2 assets."""
    failures: list[str] = []
    semantic = {part.semantic_part for part in builder.parts}
    materials = {part.material for part in builder.parts}
    detail_prefixes = (
        "detail.",
        "joinery.",
        "interface.",
        "closure.",
        "protection.",
        "mechanism.",
        "handle.",
        "organization.",
        "storage.",
        "joint.",
    )
    detail_parts = [part for part in builder.parts if part.semantic_part.startswith(detail_prefixes)]
    underside_or_back = [
        part
        for part in builder.parts
        if any(token in part.semantic_part for token in ("underside", "skid", "foot", "back", "ballast"))
    ]
    controls = [
        part
        for part in builder.parts
        if part.semantic_part.startswith(("interface.", "handle.", "closure.", "organization."))
    ]
    refinement_ops = [
        item for item in builder.operations if item.operator == "refinement.verify_close_inspection"
    ]
    if len(builder.parts) < 48:
        failures.append("fewer than 48 inspectable components")
    if len(semantic) < 14:
        failures.append("fewer than 14 semantic part classes")
    if len(materials) < 6:
        failures.append("fewer than six material classes")
    if len(detail_parts) < 18:
        failures.append("secondary and tertiary detail is too shallow")
    if len(underside_or_back) < 4:
        failures.append("underside or back completion is too shallow")
    if len(controls) < 6:
        failures.append("functional controls or affordances are too shallow")
    if not refinement_ops:
        failures.append("missing close-inspection refinement receipt")
    return Evaluation(
        passed=not failures,
        metrics={
            "geometry_components": len(builder.parts),
            "semantic_part_classes": len(semantic),
            "material_classes": len(materials),
            "detail_components": len(detail_parts),
            "detail_ratio": round(len(detail_parts) / max(len(builder.parts), 1), 4),
            "underside_or_back_components": len(underside_or_back),
            "control_or_affordance_components": len(controls),
            "refinement_receipts": len(refinement_ops),
        },
        failures=tuple(failures),
    )


def evaluate_glb(data: bytes, *, minimum_meshes: int, require_animation: bool, root_name: str) -> Evaluation:
    document, binary = parse_glb(data)
    names = {node.get("name") for node in document.get("nodes", [])}
    external_uris = [image.get("uri") for image in document.get("images", []) if image.get("uri")]
    metrics = {
        "reopened": bool(binary) and bool(document.get("meshes")) and root_name in names,
        "mesh_count": len(document.get("meshes", [])),
        "node_count": len(document.get("nodes", [])),
        "material_count": len(document.get("materials", [])),
        "embedded_image_count": len(document.get("images", [])),
        "animation_count": len(document.get("animations", [])),
        "external_uris": external_uris,
    }
    failures: list[str] = []
    if not metrics["reopened"]:
        failures.append("GLB did not reopen with required root")
    if metrics["mesh_count"] < minimum_meshes:
        failures.append(f"mesh count below {minimum_meshes}")
    if metrics["material_count"] < 4:
        failures.append("fewer than four retained materials")
    if metrics["embedded_image_count"] < 4:
        failures.append("fewer than four embedded procedural textures")
    if require_animation and metrics["animation_count"] < 1:
        failures.append("movable object lacks retained animation")
    if external_uris:
        failures.append("external texture URI present")
    return Evaluation(passed=not failures, metrics=metrics, failures=tuple(failures))


def evaluate_diversity(records: list[dict[str, Any]]) -> Evaluation:
    signatures = {
        (
            item["family"],
            item["variant"],
            item["metrics"]["geometry_components"],
            item["metrics"]["material_classes"],
            item["metrics"]["articulation_count"],
        )
        for item in records
    }
    families = {item["family"] for item in records}
    failures = []
    if len(records) != 9:
        failures.append("Scope 1 must deliver nine assets")
    if families != {"lamp", "case", "table"}:
        failures.append("Scope 1 must cover all three families")
    if len(signatures) < 8:
        failures.append("variants are insufficiently distinct")
    return Evaluation(
        passed=not failures,
        metrics={
            "asset_count": len(records),
            "family_count": len(families),
            "distinct_signatures": len(signatures),
        },
        failures=tuple(failures),
    )
