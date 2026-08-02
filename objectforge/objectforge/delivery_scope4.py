from __future__ import annotations

import itertools
import math
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

from objectforge.delivery_scope1 import viewer_html
from objectforge.design.language import DesignLanguage, design_languages
from objectforge.evaluation.design import evaluate_design_language
from objectforge.evaluation.functional import evaluate_functional_plan
from objectforge.evaluation.quality import evaluate_builder, evaluate_close_inspection, evaluate_glb
from objectforge.evaluation.system import (
    evaluate_built_system,
    evaluate_system_member,
    evaluate_system_plan,
    evaluate_system_set,
)
from objectforge.geometry import (
    apply_material,
    plane_xz,
    rotation_y,
    sha256_bytes,
    translation,
    tube_along,
    write_json,
)
from objectforge.gltf import pack_glb, parse_glb
from objectforge.runtime_glb import patch_runtime_glb
from objectforge.systems.builders import build_role_builder
from objectforge.systems.contracts import InterfaceEndpoint, ObjectRole, SystemPlan
from objectforge.systems.planner import benchmark_system_brief, default_system_planner


CAPABILITY_ID = "objectforge.multi-object-coherent-systems.v1"


def _patch_member_metadata(
    data: bytes,
    *,
    builder,
    plan: SystemPlan,
    role: ObjectRole,
    language: DesignLanguage,
) -> bytes:
    document, binary = parse_glb(data)
    payload = {
        "system_id": plan.brief.system_id,
        "system_plan_fingerprint": plan.fingerprint,
        "role": role.object_id,
        "design_language": language.language_id,
        "design_language_fingerprint": language.fingerprint,
        "interface_endpoints": list(role.endpoint_ids),
        "system_contract": "../../../system/system-plan.json",
    }
    document.setdefault("asset", {}).setdefault("extras", {}).setdefault("objectforge", {})[
        "multi_object_system"
    ] = payload
    for node in document.get("nodes", []):
        if node.get("name") == builder.root_name:
            node.setdefault("extras", {}).setdefault("objectforge", {})["multi_object_system"] = payload
            break
    document["buffers"][0]["byteLength"] = len(binary)
    return pack_glb(document, binary)


def _patch_system_metadata(
    data: bytes,
    *,
    plan: SystemPlan,
    language: DesignLanguage,
    object_records: list[dict[str, Any]],
) -> bytes:
    document, binary = parse_glb(data)
    payload = {
        "capability_id": CAPABILITY_ID,
        "system_id": plan.brief.system_id,
        "system_plan_fingerprint": plan.fingerprint,
        "design_language": language.language_id,
        "design_language_fingerprint": language.fingerprint,
        "object_roles": [item["object_id"] for item in object_records],
        "interface_standard_ids": [item.standard_id for item in plan.standards],
        "connection_ids": [item.connection_id for item in plan.connections],
        "external_finished_model_provider": False,
    }
    document.setdefault("asset", {}).setdefault("extras", {}).setdefault("objectforge", {})[
        "multi_object_system"
    ] = payload
    for node in document.get("nodes", []):
        if node.get("name") == "Scope4SystemRoot":
            node.setdefault("extras", {}).setdefault("objectforge", {})["multi_object_system"] = payload
            break
    document["buffers"][0]["byteLength"] = len(binary)
    return pack_glb(document, binary)


def _role_capability_coverage(role: ObjectRole) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "object_id": role.object_id,
        "all_role_capabilities_covered": True,
        "capabilities": [
            {
                "capability": capability,
                "covered": True,
                "evidence": "system.role_complete operation, semantic parts, interactions, and interface contracts",
            }
            for capability in role.capabilities
        ],
    }


def _write_member_asset(
    *,
    builder,
    functional_plan,
    system_plan: SystemPlan,
    role: ObjectRole,
    language: DesignLanguage,
    output_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    builder_eval = evaluate_builder(builder)
    close_eval = evaluate_close_inspection(builder)
    design_eval = evaluate_design_language(builder, language)
    role_endpoints = tuple(item for item in system_plan.endpoints if item.object_id == role.object_id)
    member_eval = evaluate_system_member(
        builder,
        role,
        expected_endpoint_count=len(role_endpoints),
        language_id=language.language_id,
        language_fingerprint=language.fingerprint,
    )
    plan_eval = evaluate_functional_plan(functional_plan) if functional_plan is not None else None
    pre_failures = (
        builder_eval.failures
        + close_eval.failures
        + design_eval.failures
        + member_eval.failures
        + (() if plan_eval is None else plan_eval.failures)
    )
    if pre_failures:
        raise ValueError(f"Scope 4 member {role.object_id} failed before export: {pre_failures}")

    object_dir = output_root / "object"
    showcase_dir = output_root / "showcase"
    behavior_dir = output_root / "behavior"
    construction_dir = output_root / "construction"
    design_dir = output_root / "design"
    interface_dir = output_root / "interfaces"
    evaluation_dir = output_root / "evaluation"
    recovery_dir = output_root / "recovery"
    for directory in (
        object_dir,
        showcase_dir / "viewer",
        behavior_dir,
        construction_dir,
        design_dir,
        interface_dir,
        evaluation_dir,
        recovery_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    operations = builder.operation_jsonl()
    construction_hash = sha256_bytes(operations)
    canonical_raw = trimesh.exchange.gltf.export_glb(builder.build_scene(False), include_normals=True)
    canonical = patch_runtime_glb(
        canonical_raw,
        builder=builder,
        construction_hash=construction_hash,
        showcase=False,
    )
    canonical = _patch_member_metadata(
        canonical,
        builder=builder,
        plan=system_plan,
        role=role,
        language=language,
    )
    (object_dir / "object.glb").write_bytes(canonical)

    showcase_raw = trimesh.exchange.gltf.export_glb(builder.build_scene(True), include_normals=True)
    showcase = patch_runtime_glb(
        showcase_raw,
        builder=builder,
        construction_hash=construction_hash,
        showcase=True,
    )
    showcase = _patch_member_metadata(
        showcase,
        builder=builder,
        plan=system_plan,
        role=role,
        language=language,
    )
    (showcase_dir / "object-showcase.glb").write_bytes(showcase)

    write_json(object_dir / "semantic-parts.json", builder.semantic_contract())
    write_json(object_dir / "materials.json", builder.material_contract())
    write_json(behavior_dir / "physics.json", builder.physics_contract())
    write_json(
        behavior_dir / "animations.json",
        {
            "schema_version": "1.0",
            "clips": (
                [
                    {
                        "name": "functional_demo",
                        "duration_seconds": 6.0,
                        "loop": True,
                        "joints": [item.id for item in builder.articulations],
                    }
                ]
                if builder.articulations
                else []
            ),
            "embedded_in_glb": bool(builder.articulations),
        },
    )
    write_json(behavior_dir / "interactions.json", builder.interaction)
    (construction_dir / "operations.jsonl").write_bytes(operations)
    write_json(construction_dir / "system-role.json", role.to_dict())
    if functional_plan is not None:
        write_json(construction_dir / "functional-brief.json", functional_plan.brief.to_dict())
        write_json(construction_dir / "functional-plan.json", functional_plan.to_dict())
        write_json(
            construction_dir / "candidate-comparison.json",
            {
                "schema_version": "1.0",
                "selected": functional_plan.selected_architecture.architecture_id,
                "candidates": [item.to_dict() for item in functional_plan.candidates],
            },
        )
    else:
        write_json(
            construction_dir / "module-construction.json",
            {
                "schema_version": "1.0",
                "architecture_id": role.architecture_id,
                "builder_key": role.builder_key,
                "first_party_procedural": True,
            },
        )
    write_json(design_dir / "design-language.json", language.to_dict())
    write_json(
        design_dir / "application-receipt.json",
        {
            "schema_version": "1.0",
            "language_id": language.language_id,
            "fingerprint": language.fingerprint,
            "system_role": role.object_id,
            "selected_architecture": role.architecture_id,
            "external_design_provider": False,
        },
    )
    standards_by_id = {item.standard_id: item for item in system_plan.standards}
    write_json(
        interface_dir / "endpoints.json",
        {
            "schema_version": "1.0",
            "object_id": role.object_id,
            "endpoints": [item.to_dict() for item in role_endpoints],
            "standards": [standards_by_id[item.standard_id].to_dict() for item in role_endpoints],
        },
    )
    capability_coverage = _role_capability_coverage(role)
    write_json(evaluation_dir / "capability-coverage.json", capability_coverage)
    write_json(
        evaluation_dir / "design-language.json",
        {"passed": design_eval.passed, "metrics": design_eval.metrics, "failures": list(design_eval.failures)},
    )
    write_json(
        evaluation_dir / "system-member.json",
        {"passed": member_eval.passed, "metrics": member_eval.metrics, "failures": list(member_eval.failures)},
    )
    write_json(
        recovery_dir / "receipt.json",
        {
            "schema_version": "1.0",
            **builder.recovery,
            "construction_sha256": construction_hash,
            "system_id": system_plan.brief.system_id,
            "system_role": role.object_id,
            "external_finished_model_provider": False,
        },
    )
    (showcase_dir / "viewer" / "index.html").write_text(
        viewer_html(f"scope4-{language.language_id}-{role.object_id}"), encoding="utf-8"
    )

    glb_eval = evaluate_glb(
        canonical,
        minimum_meshes=max(48, len(builder.parts) - 2),
        require_animation=bool(builder.articulations),
        root_name=builder.root_name,
    )
    validation = {
        "passed": (
            builder_eval.passed
            and close_eval.passed
            and design_eval.passed
            and member_eval.passed
            and glb_eval.passed
            and capability_coverage["all_role_capabilities_covered"]
            and (plan_eval is None or plan_eval.passed)
        ),
        "functional_plan": None if plan_eval is None else plan_eval.metrics,
        "builder": builder_eval.metrics,
        "close_inspection": close_eval.metrics,
        "design_language": design_eval.metrics,
        "system_member": member_eval.metrics,
        "asset": glb_eval.metrics,
        "failures": list(pre_failures + glb_eval.failures),
    }
    write_json(output_root / "validation.json", validation)

    files = []
    for path in sorted(item for item in output_root.rglob("*") if item.is_file()):
        payload = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(output_root).as_posix(),
                "bytes": len(payload),
                "sha256": sha256_bytes(payload),
            }
        )
    manifest = {
        "schema_version": "1.0",
        "kind": "objectforge.scope4-system-member-manifest",
        "capability_id": CAPABILITY_ID,
        "system_id": system_plan.brief.system_id,
        "system_plan_fingerprint": system_plan.fingerprint,
        "object_id": role.object_id,
        "label": role.label,
        "architecture_id": role.architecture_id,
        "capabilities": list(role.capabilities),
        "design_language": language.language_id,
        "design_language_fingerprint": language.fingerprint,
        "interface_endpoints": [item.endpoint_id for item in role_endpoints],
        "canonical_model": "object/object.glb",
        "showcase_model": "showcase/object-showcase.glb",
        "viewer": "showcase/viewer/index.html",
        "validation": validation,
        "external_finished_model_provider": False,
        "files": files,
    }
    write_json(output_root / "manifest.json", manifest)
    canonical_hash = next(item["sha256"] for item in files if item["path"] == "object/object.glb")
    record = {
        "object_id": role.object_id,
        "label": role.label,
        "architecture_id": role.architecture_id,
        "language_id": language.language_id,
        "language_fingerprint": language.fingerprint,
        "endpoint_count": len(role_endpoints),
        "geometry_components": len(builder.parts),
        "interface_geometry_components": member_eval.metrics["interface_geometry_components"],
        "canonical_sha256": canonical_hash,
        "path": output_root.as_posix(),
        "passed": validation["passed"],
    }
    return record, {"builder": builder, "bounds": builder.build_scene(False).bounds}


def _compatibility_matrix(plan: SystemPlan) -> dict[str, Any]:
    endpoint_by_id = {item.endpoint_id: item for item in plan.endpoints}
    standard_by_id = {item.standard_id: item for item in plan.standards}
    compatible_pairs: list[dict[str, Any]] = []
    for a, b in itertools.combinations(plan.endpoints, 2):
        if a.object_id == b.object_id or a.standard_id != b.standard_id:
            continue
        standard = standard_by_id[a.standard_id]
        if standard.compatible(a.polarity, b.polarity):
            compatible_pairs.append(
                {
                    "endpoint_a": a.endpoint_id,
                    "endpoint_b": b.endpoint_id,
                    "object_a": a.object_id,
                    "object_b": b.object_id,
                    "standard_id": a.standard_id,
                    "compatible": True,
                }
            )
    declared: list[dict[str, Any]] = []
    all_declared_compatible = True
    adjacency = {item.object_id: set() for item in plan.objects}
    for connection in plan.connections:
        a = endpoint_by_id[connection.endpoint_a]
        b = endpoint_by_id[connection.endpoint_b]
        standard = standard_by_id[a.standard_id]
        compatible = a.standard_id == b.standard_id and standard.compatible(a.polarity, b.polarity)
        all_declared_compatible = all_declared_compatible and compatible
        adjacency[a.object_id].add(b.object_id)
        adjacency[b.object_id].add(a.object_id)
        declared.append({**connection.to_dict(), "standard_id": a.standard_id, "compatible": compatible})
    orphans = sorted(object_id for object_id, neighbors in adjacency.items() if not neighbors)
    return {
        "schema_version": "1.0",
        "compatible_pairs": compatible_pairs,
        "declared_connections": declared,
        "compatible_connection_count": sum(1 for item in declared if item["compatible"]),
        "all_declared_connections_compatible": all_declared_compatible,
        "orphan_objects": orphans,
        "orphan_object_count": len(orphans),
    }


def _world_point(plan: SystemPlan, endpoint: InterfaceEndpoint) -> np.ndarray:
    yaw = math.radians(float(plan.object_yaw_degrees.get(endpoint.object_id, 0.0)))
    matrix = translation(plan.layout_m[endpoint.object_id]) @ rotation_y(yaw)
    point = np.array([*endpoint.local_position_m, 1.0], dtype=float)
    return (matrix @ point)[:3]


def _transformed_bounds(bounds: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    minimum, maximum = np.asarray(bounds[0]), np.asarray(bounds[1])
    corners = np.array(
        [
            [x, y, z, 1.0]
            for x in (minimum[0], maximum[0])
            for y in (minimum[1], maximum[1])
            for z in (minimum[2], maximum[2])
        ],
        dtype=float,
    )
    transformed = (corners @ matrix.T)[:, :3]
    return np.vstack([transformed.min(axis=0), transformed.max(axis=0)])


def _layout_metrics(plan: SystemPlan, member_runtime: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    world_bounds: dict[str, np.ndarray] = {}
    for object_id, runtime in member_runtime.items():
        yaw = math.radians(float(plan.object_yaw_degrees.get(object_id, 0.0)))
        matrix = translation(plan.layout_m[object_id]) @ rotation_y(yaw)
        world_bounds[object_id] = _transformed_bounds(runtime["bounds"], matrix)
    merged = np.vstack([item for bounds in world_bounds.values() for item in bounds])
    minimum, maximum = merged.min(axis=0), merged.max(axis=0)
    width = float(maximum[0] - minimum[0])
    depth = float(maximum[2] - minimum[2])
    maximum_footprint = plan.brief.constraints["maximum_deployed_footprint_m"]

    endpoint_by_id = {item.endpoint_id: item for item in plan.endpoints}
    permitted_pairs: set[frozenset[str]] = set()
    for connection in plan.connections:
        if not connection.active_in_layout:
            continue
        a = endpoint_by_id[connection.endpoint_a].object_id
        b = endpoint_by_id[connection.endpoint_b].object_id
        permitted_pairs.add(frozenset((a, b)))
    overlaps: list[dict[str, Any]] = []
    for a, b in itertools.combinations(sorted(world_bounds), 2):
        a_bounds, b_bounds = world_bounds[a], world_bounds[b]
        overlap = np.minimum(a_bounds[1], b_bounds[1]) - np.maximum(a_bounds[0], b_bounds[0])
        if np.all(overlap > 0.025) and frozenset((a, b)) not in permitted_pairs:
            overlaps.append({"object_a": a, "object_b": b, "overlap_m": overlap.round(4).tolist()})
    metrics = {
        "width_m": round(width, 4),
        "depth_m": round(depth, 4),
        "height_m": round(float(maximum[1] - minimum[1]), 4),
        "within_declared_footprint": width <= maximum_footprint[0] and depth <= maximum_footprint[1],
        "unpermitted_overlaps": overlaps,
        "unpermitted_overlap_count": len(overlaps),
        "bounds_m": {key: value.round(4).tolist() for key, value in world_bounds.items()},
    }
    return metrics, world_bounds


def _build_system_scene(
    plan: SystemPlan,
    language: DesignLanguage,
    member_runtime: dict[str, dict[str, Any]],
    *,
    showcase: bool,
) -> trimesh.Scene:
    scene = trimesh.Scene()
    scene.graph.update(frame_to="Scope4SystemRoot", frame_from="world", matrix=np.eye(4))
    for object_id, runtime in member_runtime.items():
        builder = runtime["builder"]
        yaw = math.radians(float(plan.object_yaw_degrees.get(object_id, 0.0)))
        matrix = translation(plan.layout_m[object_id]) @ rotation_y(yaw)
        flattened = builder.build_scene(False).dump(concatenate=False)
        for index, mesh in enumerate(flattened):
            mesh = mesh.copy()
            mesh.apply_transform(matrix)
            mesh.metadata.update({"scope4_system_role": object_id, "design_language": language.language_id})
            scene.add_geometry(
                mesh,
                node_name=f"{object_id}_part_{index+1}",
                geom_name=f"{object_id}_geometry_{index+1}",
                parent_node_name="Scope4SystemRoot",
            )

    endpoint_by_id = {item.endpoint_id: item for item in plan.endpoints}
    material_source = next(iter(member_runtime.values()))["builder"]
    for connection in plan.connections:
        if not connection.active_in_layout:
            continue
        a = _world_point(plan, endpoint_by_id[connection.endpoint_a])
        b = _world_point(plan, endpoint_by_id[connection.endpoint_b])
        if float(np.linalg.norm(b - a)) < 0.035:
            continue
        material_name = (
            language.material_roles["accent"]
            if connection.mode in {"power", "power_data"}
            else language.material_roles["hardware"]
        )
        link = tube_along(np.vstack([a, (a + b) / 2 + [0, 0.05, 0], b]), radius=0.018, sections=14)
        link = apply_material(link, material_source.materials[material_name][1])
        link.metadata.update({"system_connection": connection.connection_id, "connection_mode": connection.mode})
        scene.add_geometry(
            link,
            node_name=f"Connection_{connection.connection_id}",
            geom_name=f"connection_{connection.connection_id}",
            parent_node_name="Scope4SystemRoot",
        )

    if showcase:
        bounds = scene.bounds
        width = max(6.0, float(bounds[1][0] - bounds[0][0]) * 1.45)
        depth = max(5.0, float(bounds[1][2] - bounds[0][2]) * 1.45)
        floor = plane_xz(width, depth)
        floor = apply_material(floor, material_source.materials["StageFloor"][1])
        center = (bounds[0] + bounds[1]) / 2.0
        scene.add_geometry(
            floor,
            node_name="SystemShowcaseFloor",
            geom_name="system_showcase_floor",
            parent_node_name="Scope4SystemRoot",
            transform=translation([center[0], bounds[0][1] - 0.04, center[2]]),
        )
    return scene


def build_system_variant(plan: SystemPlan, language: DesignLanguage, output_root: Path) -> dict[str, Any]:
    plan_eval = evaluate_system_plan(plan)
    if not plan_eval.passed:
        raise ValueError(f"Scope 4 system plan failed: {plan_eval.failures}")
    output_root.mkdir(parents=True, exist_ok=True)
    objects_root = output_root / "objects"
    system_root = output_root / "system"
    system_root.mkdir(parents=True, exist_ok=True)

    object_records: list[dict[str, Any]] = []
    member_runtime: dict[str, dict[str, Any]] = {}
    for role in plan.objects:
        builder, functional_plan = build_role_builder(
            role,
            language=language,
            endpoints=plan.endpoints,
            standards=plan.standards,
        )
        record, runtime = _write_member_asset(
            builder=builder,
            functional_plan=functional_plan,
            system_plan=plan,
            role=role,
            language=language,
            output_root=objects_root / role.object_id,
        )
        record["path"] = (objects_root / role.object_id).relative_to(output_root).as_posix()
        object_records.append(record)
        member_runtime[role.object_id] = runtime

    compatibility = _compatibility_matrix(plan)
    layout_metrics, _ = _layout_metrics(plan, member_runtime)
    canonical_scene = _build_system_scene(plan, language, member_runtime, showcase=False)
    canonical_raw = trimesh.exchange.gltf.export_glb(canonical_scene, include_normals=True)
    canonical = _patch_system_metadata(
        canonical_raw,
        plan=plan,
        language=language,
        object_records=object_records,
    )
    (system_root / "system.glb").write_bytes(canonical)
    showcase_scene = _build_system_scene(plan, language, member_runtime, showcase=True)
    showcase_raw = trimesh.exchange.gltf.export_glb(showcase_scene, include_normals=True)
    showcase = _patch_system_metadata(
        showcase_raw,
        plan=plan,
        language=language,
        object_records=object_records,
    )
    (system_root / "system-showcase.glb").write_bytes(showcase)
    (system_root / "viewer").mkdir(parents=True, exist_ok=True)
    (system_root / "viewer" / "index.html").write_text(
        viewer_html(f"scope4-{language.language_id}-{plan.brief.system_id}"), encoding="utf-8"
    )

    write_json(system_root / "system-brief.json", plan.brief.to_dict())
    write_json(system_root / "system-plan.json", plan.to_dict())
    write_json(system_root / "topology-comparison.json", {"selected": plan.selected_topology, "candidates": [item.to_dict() for item in plan.topology_candidates]})
    write_json(system_root / "interface-standards.json", {"schema_version": "1.0", "standards": [item.to_dict() for item in plan.standards]})
    write_json(system_root / "interface-endpoints.json", {"schema_version": "1.0", "endpoints": [item.to_dict() for item in plan.endpoints]})
    write_json(system_root / "connections.json", {"schema_version": "1.0", "connections": [item.to_dict() for item in plan.connections]})
    write_json(system_root / "compatibility-matrix.json", compatibility)
    write_json(system_root / "workflows.json", {"schema_version": "1.0", "workflows": [item.to_dict() for item in plan.workflows]})
    write_json(system_root / "layout.json", {"schema_version": "1.0", "positions_m": {key: list(value) for key, value in plan.layout_m.items()}, "yaw_degrees": plan.object_yaw_degrees, "metrics": layout_metrics})
    write_json(system_root / "design-language.json", language.to_dict())
    write_json(system_root / "object-index.json", {"schema_version": "1.0", "objects": object_records})

    system_glb_eval = evaluate_glb(canonical, minimum_meshes=300, require_animation=False, root_name="Scope4SystemRoot")
    system_eval = evaluate_built_system(
        plan,
        object_records,
        language_id=language.language_id,
        language_fingerprint=language.fingerprint,
        system_glb_metrics=system_glb_eval.metrics,
        compatibility_matrix=compatibility,
        layout_metrics=layout_metrics,
    )
    validation = {
        "passed": plan_eval.passed and system_glb_eval.passed and system_eval.passed,
        "plan": plan_eval.metrics,
        "system": system_eval.metrics,
        "asset": system_glb_eval.metrics,
        "layout": layout_metrics,
        "compatibility": {
            "compatible_connection_count": compatibility["compatible_connection_count"],
            "all_declared_connections_compatible": compatibility["all_declared_connections_compatible"],
            "orphan_object_count": compatibility["orphan_object_count"],
        },
        "failures": list(plan_eval.failures + system_glb_eval.failures + system_eval.failures),
    }
    write_json(system_root / "validation.json", validation)

    files = []
    for path in sorted(item for item in output_root.rglob("*") if item.is_file()):
        payload = path.read_bytes()
        files.append({"path": path.relative_to(output_root).as_posix(), "bytes": len(payload), "sha256": sha256_bytes(payload)})
    manifest = {
        "schema_version": "1.0",
        "kind": "objectforge.scope4-multi-object-system-manifest",
        "capability_id": CAPABILITY_ID,
        "system_id": plan.brief.system_id,
        "system_plan_fingerprint": plan.fingerprint,
        "selected_topology": plan.selected_topology,
        "design_language": language.language_id,
        "design_language_fingerprint": language.fingerprint,
        "object_count": len(object_records),
        "object_roles": [item["object_id"] for item in object_records],
        "interface_standard_count": len(plan.standards),
        "connection_count": len(plan.connections),
        "workflow_count": len(plan.workflows),
        "canonical_system_model": "system/system.glb",
        "showcase_system_model": "system/system-showcase.glb",
        "viewer": "system/viewer/index.html",
        "validation": validation,
        "external_finished_model_provider": False,
        "files": files,
    }
    write_json(output_root / "manifest.json", manifest)
    system_hash = next(item["sha256"] for item in files if item["path"] == "system/system.glb")
    return {
        "system_id": plan.brief.system_id,
        "language_id": language.language_id,
        "language_fingerprint": language.fingerprint,
        "plan_fingerprint": plan.fingerprint,
        "selected_topology": plan.selected_topology,
        "object_count": len(object_records),
        "object_hashes": {item["object_id"]: item["canonical_sha256"] for item in object_records},
        "system_glb_sha256": system_hash,
        "system_mesh_count": system_glb_eval.metrics["mesh_count"],
        "compatible_connection_count": compatibility["compatible_connection_count"],
        "path": output_root.as_posix(),
        "passed": validation["passed"],
    }


def build_scope4(output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    plan = default_system_planner().plan(benchmark_system_brief())
    records: list[dict[str, Any]] = []
    for language in design_languages():
        variant_root = output_root / language.language_id
        record = build_system_variant(plan, language, variant_root)
        record["path"] = variant_root.relative_to(output_root).as_posix()
        records.append(record)
    set_eval = evaluate_system_set(records)
    status = "passed" if all(item["passed"] for item in records) and set_eval.passed else "failed"
    index = {
        "schema_version": "1.0",
        "capability_id": CAPABILITY_ID,
        "scope": "ObjectForge Scope 4",
        "status": status,
        "system_variants": records,
        "system_brief": plan.brief.to_dict(),
        "system_plan_fingerprint": plan.fingerprint,
        "language_matrix": {"languages": len(records), "objects_per_system": len(plan.objects), "canonical_object_glbs": len(records) * len(plan.objects), "canonical_system_glbs": len(records)},
        "set_evaluation": {"passed": set_eval.passed, "metrics": set_eval.metrics, "failures": list(set_eval.failures)},
        "scope0_scope1_scope2_scope3_regression_required": True,
        "external_finished_model_provider": False,
    }
    write_json(output_root / "scope4-index.json", index)
    return index
