from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from objectforge.grammar.core import GrammarAssetBuilder
from objectforge.systems.contracts import ObjectRole, SystemPlan


@dataclass(frozen=True)
class SystemEvaluation:
    passed: bool
    metrics: dict[str, Any]
    failures: tuple[str, ...]


def evaluate_system_plan(plan: SystemPlan) -> SystemEvaluation:
    failures: list[str] = []
    object_ids = {item.object_id for item in plan.objects}
    endpoint_by_id = {item.endpoint_id: item for item in plan.endpoints}
    standard_by_id = {item.standard_id: item for item in plan.standards}
    connection_ids = {item.connection_id for item in plan.connections}
    required = set(plan.brief.required_capabilities)
    covered = {capability for item in plan.objects for capability in item.capabilities}

    if len(plan.topology_candidates) < 3:
        failures.append("fewer than three system topologies compared")
    selected = next((item for item in plan.topology_candidates if item.topology_id == plan.selected_topology), None)
    if selected is None:
        failures.append("selected topology is absent from candidate set")
    elif selected.score != max(item.score for item in plan.topology_candidates):
        failures.append("selected topology is not the highest-scoring candidate")
    if len(plan.objects) < int(plan.brief.constraints.get("minimum_object_count", 0)):
        failures.append("system has too few independently useful objects")
    if required - covered:
        failures.append(f"system misses required capabilities: {sorted(required - covered)}")
    if len(plan.standards) < int(plan.brief.constraints.get("minimum_shared_interface_standards", 0)):
        failures.append("too few shared interface standards")
    if sum(1 for item in plan.connections if item.active_in_layout) < int(
        plan.brief.constraints.get("minimum_active_connections", 0)
    ):
        failures.append("too few active operational connections")

    for endpoint in plan.endpoints:
        if endpoint.object_id not in object_ids:
            failures.append(f"endpoint {endpoint.endpoint_id} references unknown object")
        if endpoint.standard_id not in standard_by_id:
            failures.append(f"endpoint {endpoint.endpoint_id} references unknown standard")
    for connection in plan.connections:
        if connection.endpoint_a not in endpoint_by_id or connection.endpoint_b not in endpoint_by_id:
            failures.append(f"connection {connection.connection_id} references unknown endpoint")
            continue
        a = endpoint_by_id[connection.endpoint_a]
        b = endpoint_by_id[connection.endpoint_b]
        if a.standard_id != b.standard_id:
            failures.append(f"connection {connection.connection_id} crosses incompatible standards")
            continue
        standard = standard_by_id[a.standard_id]
        if not standard.compatible(a.polarity, b.polarity):
            failures.append(f"connection {connection.connection_id} has incompatible polarities")
        if a.object_id == b.object_id:
            failures.append(f"connection {connection.connection_id} does not cross object boundaries")

    connected_objects = {item.object_id: set() for item in plan.objects}
    used_standards: dict[str, int] = {}
    for connection in plan.connections:
        a = endpoint_by_id.get(connection.endpoint_a)
        b = endpoint_by_id.get(connection.endpoint_b)
        if a is None or b is None:
            continue
        connected_objects[a.object_id].add(b.object_id)
        connected_objects[b.object_id].add(a.object_id)
        used_standards[a.standard_id] = used_standards.get(a.standard_id, 0) + 1
    orphans = sorted(object_id for object_id, neighbors in connected_objects.items() if not neighbors)
    if orphans:
        failures.append(f"objects have no compatibility edges: {orphans}")
    reusable = {key: count for key, count in used_standards.items() if count >= 2}
    if len(reusable) < 3:
        failures.append("fewer than three interface standards are reused across objects")

    for workflow in plan.workflows:
        missing_objects = set(workflow.required_objects) - object_ids
        missing_connections = set(workflow.required_connections) - connection_ids
        if missing_objects:
            failures.append(f"workflow {workflow.workflow_id} references unknown objects")
        if missing_connections:
            failures.append(f"workflow {workflow.workflow_id} references unknown connections")
        if not workflow.ordered_steps:
            failures.append(f"workflow {workflow.workflow_id} has no ordered steps")
    if set(plan.layout_m) != object_ids:
        failures.append("layout does not place every system object")

    return SystemEvaluation(
        passed=not failures,
        metrics={
            "object_count": len(plan.objects),
            "required_capability_count": len(required),
            "covered_capability_count": len(required & covered),
            "topology_candidate_count": len(plan.topology_candidates),
            "selected_topology": plan.selected_topology,
            "interface_standard_count": len(plan.standards),
            "reused_interface_standard_count": len(reusable),
            "endpoint_count": len(plan.endpoints),
            "connection_count": len(plan.connections),
            "active_connection_count": sum(1 for item in plan.connections if item.active_in_layout),
            "workflow_count": len(plan.workflows),
            "orphan_objects": orphans,
            "plan_fingerprint": plan.fingerprint,
        },
        failures=tuple(failures),
    )


def evaluate_system_member(
    builder: GrammarAssetBuilder,
    role: ObjectRole,
    *,
    expected_endpoint_count: int,
    language_id: str,
    language_fingerprint: str,
) -> SystemEvaluation:
    failures: list[str] = []
    endpoint_metadata = builder.functional_metadata.get("system_interface_endpoints", [])
    interface_parts = [part for part in builder.parts if part.semantic_part.startswith("system_interface.")]
    role_ops = [item for item in builder.operations if item.operator == "system.role_complete"]
    interface_ops = [item for item in builder.operations if item.operator == "system.interface.instantiate"]
    if builder.capability_id != "objectforge.multi-object-coherent-systems.v1":
        failures.append("member does not advertise Scope 4 capability")
    if builder.functional_metadata.get("system_role") != role.object_id:
        failures.append("member role metadata differs from the system plan")
    if builder.functional_metadata.get("design_language") != language_id:
        failures.append("member design language differs from system language")
    if builder.functional_metadata.get("design_language_fingerprint") != language_fingerprint:
        failures.append("member design-language fingerprint differs from system language")
    if len(endpoint_metadata) != expected_endpoint_count:
        failures.append("member endpoint metadata count differs from system plan")
    if len(interface_ops) != expected_endpoint_count:
        failures.append("member did not instantiate every declared interface")
    if len(interface_parts) < expected_endpoint_count * 4:
        failures.append("member interface geometry is too shallow")
    if not role_ops:
        failures.append("member lacks a completed system-role operation")
    if set(builder.functional_metadata.get("system_capabilities", [])) != set(role.capabilities):
        failures.append("member capability metadata differs from planned role")
    return SystemEvaluation(
        passed=not failures,
        metrics={
            "system_role": role.object_id,
            "declared_endpoint_count": expected_endpoint_count,
            "interface_operation_count": len(interface_ops),
            "interface_geometry_components": len(interface_parts),
            "geometry_components": len(builder.parts),
            "operation_count": len(builder.operations),
            "language_id": language_id,
        },
        failures=tuple(failures),
    )


def evaluate_built_system(
    plan: SystemPlan,
    records: list[dict[str, Any]],
    *,
    language_id: str,
    language_fingerprint: str,
    system_glb_metrics: dict[str, Any],
    compatibility_matrix: dict[str, Any],
    layout_metrics: dict[str, Any],
) -> SystemEvaluation:
    failures: list[str] = []
    planned_roles = {item.object_id for item in plan.objects}
    built_roles = {item["object_id"] for item in records}
    if planned_roles != built_roles:
        failures.append("built object set differs from planned object set")
    if not all(item.get("passed") for item in records):
        failures.append("one or more system members failed validation")
    if {item.get("language_id") for item in records} != {language_id}:
        failures.append("system members do not share one design language")
    if {item.get("language_fingerprint") for item in records} != {language_fingerprint}:
        failures.append("system members do not share one design-language fingerprint")
    if not system_glb_metrics.get("reopened"):
        failures.append("combined system GLB did not reopen")
    if system_glb_metrics.get("mesh_count", 0) < 300:
        failures.append("combined system scene is missing expected retained geometry")
    if not compatibility_matrix.get("all_declared_connections_compatible"):
        failures.append("compatibility matrix contains an invalid declared connection")
    if compatibility_matrix.get("orphan_object_count", 1) != 0:
        failures.append("compatibility matrix contains orphan objects")
    if not layout_metrics.get("within_declared_footprint"):
        failures.append("system layout exceeds the declared footprint")
    if layout_metrics.get("unpermitted_overlap_count", 1) != 0:
        failures.append("system layout has unpermitted object overlaps")
    return SystemEvaluation(
        passed=not failures,
        metrics={
            "object_count": len(records),
            "canonical_object_count": sum(1 for item in records if item.get("canonical_sha256")),
            "language_id": language_id,
            "language_fingerprint": language_fingerprint,
            "system_mesh_count": system_glb_metrics.get("mesh_count", 0),
            "system_node_count": system_glb_metrics.get("node_count", 0),
            "compatible_connection_count": compatibility_matrix.get("compatible_connection_count", 0),
            "workflow_count": len(plan.workflows),
            "layout_width_m": layout_metrics.get("width_m"),
            "layout_depth_m": layout_metrics.get("depth_m"),
        },
        failures=tuple(failures),
    )


def evaluate_system_set(records: list[dict[str, Any]]) -> SystemEvaluation:
    failures: list[str] = []
    languages = {item["language_id"] for item in records}
    if languages != {"field_service", "precision_lab"}:
        failures.append("Scope 4 benchmark must cover both canonical design languages")
    if len(records) != 2:
        failures.append("Scope 4 benchmark must build two system-language variants")
    if len({item["plan_fingerprint"] for item in records}) != 1:
        failures.append("language variants do not share the same system plan")
    if len({item["system_glb_sha256"] for item in records}) != len(records):
        failures.append("language variants produced identical combined system GLBs")
    role_sets = {tuple(sorted(item["object_hashes"])) for item in records}
    if len(role_sets) != 1:
        failures.append("language variants do not contain the same object roles")
    if len(records) == 2:
        first, second = records
        for role_id in first["object_hashes"]:
            if first["object_hashes"][role_id] == second["object_hashes"][role_id]:
                failures.append(f"paired object {role_id} did not change under the second design language")
    return SystemEvaluation(
        passed=not failures,
        metrics={
            "system_variant_count": len(records),
            "language_count": len(languages),
            "shared_plan_fingerprint": records[0]["plan_fingerprint"] if records else None,
            "distinct_system_glb_count": len({item["system_glb_sha256"] for item in records}),
            "paired_role_count": len(records[0]["object_hashes"]) if records else 0,
        },
        failures=tuple(failures),
    )
