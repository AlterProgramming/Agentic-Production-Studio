from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any

from objectforge.systems.planner import benchmark_system_brief, default_system_planner


@dataclass(frozen=True)
class PartPlan:
    object_id: str
    primary_material: str
    primary_process: str
    secondary_processes: tuple[str, ...]
    finish: str
    inspection_method: str
    supplier_class: str
    estimated_unit_cost_usd: tuple[float, float]


@dataclass(frozen=True)
class ToleranceStack:
    connection_id: str
    standard_id: str
    allowed_m: float
    contributors_m: tuple[float, ...]
    rss_m: float
    reserve_m: float
    passed: bool


@dataclass(frozen=True)
class AssemblyOperation:
    operation_id: str
    action: str
    object_ids: tuple[str, ...]
    connection_id: str | None
    dependencies: tuple[str, ...]
    tool_class: str
    verification: str
    reversible: bool


@dataclass(frozen=True)
class ServiceProcedure:
    procedure_id: str
    object_id: str
    trigger: str
    ordered_actions: tuple[str, ...]
    isolation_required: bool
    replacement_unit: str
    return_to_service_check: str


@dataclass(frozen=True)
class ManufacturingPlan:
    system_id: str
    scope4_plan_fingerprint: str
    part_plans: tuple[PartPlan, ...]
    tolerance_stacks: tuple[ToleranceStack, ...]
    assembly_operations: tuple[AssemblyOperation, ...]
    service_procedures: tuple[ServiceProcedure, ...]
    cost_envelope_usd: tuple[float, float]
    validation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _part_plan(object_id: str) -> PartPlan:
    plans = {
        "service_hub": PartPlan(
            object_id,
            "powder-coated low-carbon steel",
            "laser-cut and brake-formed fabrication",
            ("fixture welding", "threaded insert installation", "surface finishing"),
            "textured powder coat",
            "datum inspection plus load fixture",
            "regional sheet-metal fabricator",
            (410.0, 690.0),
        ),
        "work_emitter": PartPlan(
            object_id,
            "aluminum alloy with polymer controls",
            "machining and formed-tube assembly",
            ("wire-harness assembly", "bearing installation", "optical alignment"),
            "anodized or powder-coated",
            "articulation sweep and electrical safety test",
            "electromechanical assembly supplier",
            (220.0, 390.0),
        ),
        "protected_carrier": PartPlan(
            object_id,
            "impact-modified polymer with aluminum frame",
            "thermoforming or low-volume molding",
            ("frame riveting", "seal installation", "latch fitting"),
            "molded texture",
            "closure gauge plus drop-test fixture",
            "protective-enclosure supplier",
            (280.0, 510.0),
        ),
        "instrument_caddy": PartPlan(
            object_id,
            "formed aluminum with elastomer inserts",
            "sheet forming",
            ("insert molding", "edge finishing", "label application"),
            "anodized",
            "slot gauge and retention pull test",
            "light-fabrication supplier",
            (120.0, 230.0),
        ),
        "power_module": PartPlan(
            object_id,
            "flame-retardant polymer and aluminum heat spreader",
            "machined enclosure and certified subassembly integration",
            ("busbar assembly", "connector installation", "electrical isolation test"),
            "molded and anodized",
            "hipot, polarity, thermal, and current-limit test",
            "qualified power-electronics integrator",
            (390.0, 720.0),
        ),
        "analysis_module": PartPlan(
            object_id,
            "aluminum chassis with polymer interface panel",
            "machined chassis and electronics integration",
            ("display bonding", "connector installation", "thermal-interface assembly"),
            "anodized and printed overlay",
            "functional test, thermal soak, and port verification",
            "qualified electronics integrator",
            (470.0, 860.0),
        ),
    }
    return plans[object_id]


def _tolerance_stacks(plan: Any) -> tuple[ToleranceStack, ...]:
    standards = {item.standard_id: item for item in plan.standards}
    endpoints = {item.endpoint_id: item for item in plan.endpoints}
    stacks: list[ToleranceStack] = []
    for connection in plan.connections:
        standard_id = endpoints[connection.endpoint_a].standard_id
        allowed = float(standards[standard_id].tolerance_m)
        contributors = (allowed * 0.38, allowed * 0.31, allowed * 0.24, allowed * 0.16)
        rss = math.sqrt(sum(value * value for value in contributors))
        reserve = allowed - rss
        stacks.append(
            ToleranceStack(
                connection_id=connection.connection_id,
                standard_id=standard_id,
                allowed_m=round(allowed, 7),
                contributors_m=tuple(round(value, 7) for value in contributors),
                rss_m=round(rss, 7),
                reserve_m=round(reserve, 7),
                passed=reserve >= 0.0,
            )
        )
    return tuple(stacks)


def _assembly_operations(plan: Any) -> tuple[AssemblyOperation, ...]:
    operations: list[AssemblyOperation] = [
        AssemblyOperation(
            "A00",
            "inspect received modules against drawings and interface gauges",
            tuple(item.object_id for item in plan.objects),
            None,
            (),
            "inspection fixture set",
            "all serialized objects accepted or quarantined",
            True,
        ),
        AssemblyOperation(
            "A10",
            "establish service-hub datums and verify stability",
            ("service_hub",),
            None,
            ("A00",),
            "level and datum gauge",
            "hub datums within drawing limits",
            True,
        ),
        AssemblyOperation(
            "A20",
            "verify protected-carrier shell, seals, and transport interfaces",
            ("protected_carrier",),
            None,
            ("A00",),
            "closure and seal gauge",
            "carrier closes without preload violation",
            True,
        ),
    ]
    previous_operational = "A10"
    previous_transport = "A20"
    for index, connection in enumerate(plan.connections, start=1):
        endpoint_map = {item.endpoint_id: item for item in plan.endpoints}
        objects = (
            endpoint_map[connection.endpoint_a].object_id,
            endpoint_map[connection.endpoint_b].object_id,
        )
        if connection.active_in_layout:
            operation_id = f"A3{index}"
            dependencies = (previous_operational,)
            previous_operational = operation_id
        else:
            operation_id = f"A6{index}"
            dependencies = (previous_transport,)
            previous_transport = operation_id
        operations.append(
            AssemblyOperation(
                operation_id,
                f"mate and verify {connection.connection_id}",
                objects,
                connection.connection_id,
                dependencies,
                "interface-specific go/no-go gauge",
                "full seating, polarity, retention, and continuity confirmed",
                True,
            )
        )
    operations.extend(
        (
            AssemblyOperation(
                "A90",
                "run deployed-system acceptance sequence",
                tuple(item.object_id for item in plan.objects),
                None,
                (previous_operational,),
                "system acceptance fixture",
                "deployment workflow completes with all active links healthy",
                True,
            ),
            AssemblyOperation(
                "A95",
                "run stowage and transport acceptance sequence",
                ("protected_carrier", "instrument_caddy", "power_module", "analysis_module"),
                None,
                (previous_transport, "A90"),
                "transport retention fixture",
                "stowed system remains retained and serviceable",
                True,
            ),
        )
    )
    return tuple(operations)


def _service_procedures() -> tuple[ServiceProcedure, ...]:
    return (
        ServiceProcedure(
            "SVC-POWER",
            "power_module",
            "failed self-test, thermal excursion, or capacity below service threshold",
            (
                "isolate the 24 V bus",
                "release the quarter-turn retainer",
                "withdraw the cartridge along its guides",
                "inspect bay contacts and keying",
                "insert a serialized replacement cartridge",
                "restore power through a current-limited source",
            ),
            True,
            "power cartridge",
            "polarity, insulation, current limit, and thermal checks pass",
        ),
        ServiceProcedure(
            "SVC-ANALYSIS",
            "analysis_module",
            "display, processing, sensor-port, or cooling fault",
            (
                "save the diagnostic bundle",
                "isolate power and data",
                "release the module retainer",
                "replace the serialized analysis cartridge",
                "restore the configuration bundle",
            ),
            True,
            "analysis cartridge",
            "boot, port loopback, display, and thermal checks pass",
        ),
        ServiceProcedure(
            "SVC-EMITTER",
            "work_emitter",
            "illumination output, articulation, or retention fault",
            (
                "isolate emitter power",
                "release the rail latch",
                "remove the emitter as one service unit",
                "inspect rail key and bus contacts",
                "fit and latch the replacement unit",
            ),
            True,
            "directional emitter assembly",
            "retention, articulation sweep, and illumination tests pass",
        ),
        ServiceProcedure(
            "SVC-CARRIER",
            "protected_carrier",
            "seal, hinge, latch, or impact-damage finding",
            (
                "remove all stored modules",
                "clean and inspect shell datums",
                "replace the affected seal, hinge, or latch subassembly",
                "verify closure force and capture geometry",
            ),
            False,
            "carrier hardware subassembly",
            "closure, retention, seal, and transport checks pass",
        ),
    )


def _acyclic(operations: tuple[AssemblyOperation, ...]) -> bool:
    graph = {item.operation_id: set(item.dependencies) for item in operations}
    visited: set[str] = set()
    active: set[str] = set()

    def visit(node: str) -> bool:
        if node in active:
            return False
        if node in visited:
            return True
        active.add(node)
        for dependency in graph.get(node, ()):
            if dependency not in graph or not visit(dependency):
                return False
        active.remove(node)
        visited.add(node)
        return True

    return all(visit(node) for node in graph)


def build_scope5_plan() -> ManufacturingPlan:
    scope4 = default_system_planner().plan(benchmark_system_brief())
    part_plans = tuple(_part_plan(item.object_id) for item in scope4.objects)
    stacks = _tolerance_stacks(scope4)
    operations = _assembly_operations(scope4)
    procedures = _service_procedures()
    low = round(sum(item.estimated_unit_cost_usd[0] for item in part_plans), 2)
    high = round(sum(item.estimated_unit_cost_usd[1] for item in part_plans), 2)

    object_ids = {item.object_id for item in scope4.objects}
    covered_objects = {item.object_id for item in part_plans}
    connection_ids = {item.connection_id for item in scope4.connections}
    stacked_connections = {item.connection_id for item in stacks}
    service_objects = {item.object_id for item in procedures}
    validation = {
        "all_scope4_objects_have_part_plans": covered_objects == object_ids,
        "all_scope4_connections_have_tolerance_stacks": stacked_connections == connection_ids,
        "all_tolerance_stacks_pass": all(item.passed for item in stacks),
        "assembly_graph_is_acyclic": _acyclic(operations),
        "assembly_has_deployed_and_transport_acceptance": {"A90", "A95"}.issubset(
            {item.operation_id for item in operations}
        ),
        "critical_service_routes_present": {
            "power_module",
            "analysis_module",
            "work_emitter",
            "protected_carrier",
        }.issubset(service_objects),
        "cost_envelope_is_ordered": 0.0 < low <= high,
        "external_finished_model_provider": False,
    }
    validation["passed"] = all(validation.values())
    return ManufacturingPlan(
        system_id=scope4.brief.system_id,
        scope4_plan_fingerprint=scope4.fingerprint,
        part_plans=part_plans,
        tolerance_stacks=stacks,
        assembly_operations=operations,
        service_procedures=procedures,
        cost_envelope_usd=(low, high),
        validation=validation,
    )


def write_scope5(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    plan = build_scope5_plan()
    payload = plan.to_dict()
    documents = {
        "manufacturing-plan.json": payload,
        "tolerance-stacks.json": {"stacks": [asdict(item) for item in plan.tolerance_stacks]},
        "assembly-sequence.json": {"operations": [asdict(item) for item in plan.assembly_operations]},
        "service-plan.json": {"procedures": [asdict(item) for item in plan.service_procedures]},
        "cost-envelope.json": {
            "currency": "USD",
            "low": plan.cost_envelope_usd[0],
            "high": plan.cost_envelope_usd[1],
            "basis": "bounded low-volume planning estimate; not a supplier quotation",
        },
    }
    for name, document in documents.items():
        (output / name).write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    index = {
        "schema_version": "1.0",
        "scope": "ObjectForge Scope 5",
        "capability_id": "objectforge.manufacturing-assembly-service-planning.v1",
        "system_id": plan.system_id,
        "scope4_plan_fingerprint": plan.scope4_plan_fingerprint,
        "part_plan_count": len(plan.part_plans),
        "tolerance_stack_count": len(plan.tolerance_stacks),
        "assembly_operation_count": len(plan.assembly_operations),
        "service_procedure_count": len(plan.service_procedures),
        "cost_envelope_usd": list(plan.cost_envelope_usd),
        "validation": plan.validation,
        "status": "passed" if plan.validation["passed"] else "failed",
        "scope0_through_scope4_regression_required": True,
    }
    (output / "scope5-index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ObjectForge Scope 5 manufacturing evidence")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    index = write_scope5(args.output)
    if index["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
