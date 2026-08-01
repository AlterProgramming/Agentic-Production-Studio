from __future__ import annotations

from objectforge.grammar.core import GrammarAssetBuilder
from objectforge.systems.contracts import ObjectRole

from .system import (
    SystemEvaluation,
    evaluate_built_system,
    evaluate_system_plan,
    evaluate_system_set,
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
    design_metadata = builder.functional_metadata.get("design_language") or {}
    if builder.capability_id != "objectforge.multi-object-coherent-systems.v1":
        failures.append("member does not advertise Scope 4 capability")
    if builder.functional_metadata.get("system_role") != role.object_id:
        failures.append("member role metadata differs from the system plan")
    if design_metadata.get("language_id") != language_id:
        failures.append("member design language differs from system language")
    if design_metadata.get("fingerprint") != language_fingerprint:
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


__all__ = [
    "SystemEvaluation",
    "evaluate_built_system",
    "evaluate_system_member",
    "evaluate_system_plan",
    "evaluate_system_set",
]
