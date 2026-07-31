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
    return Evaluation(not failures, {"geometry_components": len(builder.parts), "semantic_part_classes": semantic_count, "material_classes": material_count, "articulation_count": len(builder.articulations), "operation_count": len(builder.operations)}, tuple(failures))


def evaluate_glb(data: bytes, *, minimum_meshes: int, require_animation: bool, root_name: str) -> Evaluation:
    document, binary = parse_glb(data)
    names = {node.get("name") for node in document.get("nodes", [])}
    external_uris = [image.get("uri") for image in document.get("images", []) if image.get("uri")]
    metrics = {"reopened": bool(binary) and bool(document.get("meshes")) and root_name in names, "mesh_count": len(document.get("meshes", [])), "node_count": len(document.get("nodes", [])), "material_count": len(document.get("materials", [])), "embedded_image_count": len(document.get("images", [])), "animation_count": len(document.get("animations", [])), "external_uris": external_uris}
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
    return Evaluation(not failures, metrics, tuple(failures))


def evaluate_diversity(records: list[dict[str, Any]]) -> Evaluation:
    signatures = {(item["family"], item["variant"], item["metrics"]["geometry_components"], item["metrics"]["material_classes"], item["metrics"]["articulation_count"]) for item in records}
    families = {item["family"] for item in records}
    failures = []
    if len(records) != 9:
        failures.append("Scope 1 must deliver nine assets")
    if families != {"lamp", "case", "table"}:
        failures.append("Scope 1 must cover all three families")
    if len(signatures) < 8:
        failures.append("variants are insufficiently distinct")
    return Evaluation(not failures, {"asset_count": len(records), "family_count": len(families), "distinct_signatures": len(signatures)}, tuple(failures))
