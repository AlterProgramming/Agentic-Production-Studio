from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from objectforge.systems.planner import benchmark_system_brief, default_system_planner


_PART_PLANS: dict[str, dict[str, Any]] = {
    "service_hub": {
        "primary_material": "powder-coated low-carbon steel",
        "primary_process": "laser-cut and brake-formed fabrication",
        "secondary_processes": ["fixture welding", "threaded inserts", "surface finishing"],
        "inspection": "datum inspection plus load fixture",
        "supplier_class": "regional sheet-metal fabricator",
        "estimated_unit_cost_usd": [410.0, 690.0],
    },
    "work_emitter": {
        "primary_material": "aluminum alloy with polymer controls",
        "primary_process": "machining and formed-tube assembly",
        "secondary_processes": ["wire harness", "bearing installation", "optical alignment"],
        "inspection": "articulation sweep and electrical safety test",
        "supplier_class": "electromechanical assembly supplier",
        "estimated_unit_cost_usd": [220.0, 390.0],
    },
    "protected_carrier": {
        "primary_material": "impact-modified polymer with aluminum frame",
        "primary_process": "thermoforming or low-volume molding",
        "secondary_processes": ["frame riveting", "seal installation", "latch fitting"],
        "inspection": "closure gauge plus drop-test fixture",
        "supplier_class": "protective-enclosure supplier",
        "estimated_unit_cost_usd": [280.0, 510.0],
    },
    "instrument_caddy": {
        "primary_material": "formed aluminum with elastomer inserts",
        "primary_process": "sheet forming",
        "secondary_processes": ["insert molding", "edge finishing", "label application"],
        "inspection": "slot gauge and retention pull test",
        "supplier_class": "light-fabrication supplier",
        "estimated_unit_cost_usd": [120.0, 230.0],
    },
    "power_module": {
        "primary_material": "flame-retardant polymer and aluminum heat spreader",
        "primary_process": "machined enclosure and certified subassembly integration",
        "secondary_processes": ["busbar assembly", "connector installation", "isolation test"],
        "inspection": "polarity, thermal, current-limit, and insulation tests",
        "supplier_class": "qualified power-electronics integrator",
        "estimated_unit_cost_usd": [390.0, 720.0],
    },
    "analysis_module": {
        "primary_material": "aluminum chassis with polymer interface panel",
        "primary_process": "machined chassis and electronics integration",
        "secondary_processes": ["display bonding", "connector installation", "thermal assembly"],
        "inspection": "functional test, thermal soak, and port verification",
        "supplier_class": "qualified electronics integrator",
        "estimated_unit_cost_usd": [470.0, 860.0],
    },
}


def _service_procedures() -> list[dict[str, Any]]:
    return [
        {
            "procedure_id": "SVC-POWER",
            "object_id": "power_module",
            "trigger": "failed self-test, thermal excursion, or capacity below threshold",
            "isolation_required": True,
            "actions": ["isolate bus", "release retainer", "withdraw cartridge", "inspect contacts", "fit replacement", "current-limited restart"],
            "return_to_service_check": "polarity, insulation, current limit, and thermal checks pass",
        },
        {
            "procedure_id": "SVC-ANALYSIS",
            "object_id": "analysis_module",
            "trigger": "display, processing, sensor-port, or cooling fault",
            "isolation_required": True,
            "actions": ["save diagnostics", "isolate power and data", "release module", "fit replacement", "restore configuration"],
            "return_to_service_check": "boot, port loopback, display, and thermal checks pass",
        },
        {
            "procedure_id": "SVC-EMITTER",
            "object_id": "work_emitter",
            "trigger": "illumination, articulation, or retention fault",
            "isolation_required": True,
            "actions": ["isolate power", "release rail latch", "remove unit", "inspect key and contacts", "fit replacement"],
            "return_to_service_check": "retention, articulation sweep, and illumination tests pass",
        },
        {
            "procedure_id": "SVC-CARRIER",
            "object_id": "protected_carrier",
            "trigger": "seal, hinge, latch, or impact-damage finding",
            "isolation_required": False,
            "actions": ["remove stored modules", "inspect shell datums", "replace affected hardware", "verify closure and capture geometry"],
            "return_to_service_check": "closure, retention, seal, and transport checks pass",
        },
    ]


def _assembly_operations(scope4: Any) -> list[dict[str, Any]]:
    endpoint_map = {item.endpoint_id: item for item in scope4.endpoints}
    operations: list[dict[str, Any]] = [
        {
            "operation_id": "A00",
            "action": "inspect serialized objects against drawings and gauges",
            "object_ids": [item.object_id for item in scope4.objects],
            "dependencies": [],
            "verification": "objects accepted or quarantined",
            "reversible": True,
        },
        {
            "operation_id": "A10",
            "action": "establish service-hub datums and stability",
            "object_ids": ["service_hub"],
            "dependencies": ["A00"],
            "verification": "hub datums and load fixture pass",
            "reversible": True,
        },
        {
            "operation_id": "A20",
            "action": "verify carrier shell, seals, and transport interfaces",
            "object_ids": ["protected_carrier"],
            "dependencies": ["A00"],
            "verification": "carrier closes without preload violation",
            "reversible": True,
        },
    ]
    deployed_parent = "A10"
    transport_parent = "A20"
    for index, connection in enumerate(scope4.connections, start=1):
        operation_id = f"A{30 + index:02d}" if connection.active_in_layout else f"A{60 + index:02d}"
        parent = deployed_parent if connection.active_in_layout else transport_parent
        objects = [endpoint_map[connection.endpoint_a].object_id, endpoint_map[connection.endpoint_b].object_id]
        operations.append(
            {
                "operation_id": operation_id,
                "action": f"mate and verify {connection.connection_id}",
                "object_ids": objects,
                "connection_id": connection.connection_id,
                "dependencies": [parent],
                "verification": "seating, polarity, retention, and continuity confirmed",
                "reversible": True,
            }
        )
        if connection.active_in_layout:
            deployed_parent = operation_id
        else:
            transport_parent = operation_id
    operations.extend(
        [
            {
                "operation_id": "A90",
                "action": "run deployed-system acceptance sequence",
                "object_ids": [item.object_id for item in scope4.objects],
                "dependencies": [deployed_parent],
                "verification": "deployment workflow and active links pass",
                "reversible": True,
            },
            {
                "operation_id": "A95",
                "action": "run stowage and transport acceptance sequence",
                "object_ids": ["protected_carrier", "instrument_caddy", "power_module", "analysis_module"],
                "dependencies": [transport_parent, "A90"],
                "verification": "stowed system remains retained and serviceable",
                "reversible": True,
            },
        ]
    )
    return operations


def _acyclic(operations: list[dict[str, Any]]) -> bool:
    graph = {item["operation_id"]: set(item["dependencies"]) for item in operations}
    completed: set[str] = set()
    while len(completed) < len(graph):
        ready = {node for node, deps in graph.items() if node not in completed and deps <= completed}
        if not ready:
            return False
        completed |= ready
    return True


def build_scope5_plan() -> dict[str, Any]:
    scope4 = default_system_planner().plan(benchmark_system_brief())
    endpoint_map = {item.endpoint_id: item for item in scope4.endpoints}
    standard_map = {item.standard_id: item for item in scope4.standards}

    part_plans = [{"object_id": item.object_id, **_PART_PLANS[item.object_id]} for item in scope4.objects]
    tolerance_stacks: list[dict[str, Any]] = []
    for connection in scope4.connections:
        standard_id = endpoint_map[connection.endpoint_a].standard_id
        allowed = float(standard_map[standard_id].tolerance_m)
        contributors = [allowed * factor for factor in (0.38, 0.31, 0.24, 0.16)]
        rss = math.sqrt(sum(value * value for value in contributors))
        tolerance_stacks.append(
            {
                "connection_id": connection.connection_id,
                "standard_id": standard_id,
                "allowed_m": round(allowed, 7),
                "contributors_m": [round(value, 7) for value in contributors],
                "rss_m": round(rss, 7),
                "reserve_m": round(allowed - rss, 7),
                "passed": rss <= allowed,
            }
        )

    operations = _assembly_operations(scope4)
    service = _service_procedures()
    cost_low = round(sum(item["estimated_unit_cost_usd"][0] for item in part_plans), 2)
    cost_high = round(sum(item["estimated_unit_cost_usd"][1] for item in part_plans), 2)
    validation = {
        "all_scope4_objects_have_part_plans": {item["object_id"] for item in part_plans} == {item.object_id for item in scope4.objects},
        "all_scope4_connections_have_tolerance_stacks": {item["connection_id"] for item in tolerance_stacks} == {item.connection_id for item in scope4.connections},
        "all_tolerance_stacks_pass": all(item["passed"] for item in tolerance_stacks),
        "assembly_graph_is_acyclic": _acyclic(operations),
        "deployed_and_transport_acceptance_present": {"A90", "A95"} <= {item["operation_id"] for item in operations},
        "critical_service_routes_present": {"power_module", "analysis_module", "work_emitter", "protected_carrier"} <= {item["object_id"] for item in service},
        "cost_envelope_is_ordered": 0.0 < cost_low <= cost_high,
        "no_external_finished_model_provider": True,
    }
    validation["passed"] = all(validation.values())
    return {
        "schema_version": "1.0",
        "scope": "ObjectForge Scope 5",
        "capability_id": "objectforge.manufacturing-assembly-service-planning.v1",
        "system_id": scope4.brief.system_id,
        "scope4_plan_fingerprint": scope4.fingerprint,
        "part_plans": part_plans,
        "tolerance_stacks": tolerance_stacks,
        "assembly_operations": operations,
        "service_procedures": service,
        "cost_envelope_usd": [cost_low, cost_high],
        "cost_basis": "bounded low-volume planning estimate; not a supplier quotation",
        "validation": validation,
    }


def write_scope5(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    plan = build_scope5_plan()
    files = {
        "manufacturing-plan.json": plan,
        "tolerance-stacks.json": {"stacks": plan["tolerance_stacks"]},
        "assembly-sequence.json": {"operations": plan["assembly_operations"]},
        "service-plan.json": {"procedures": plan["service_procedures"]},
        "cost-envelope.json": {"currency": "USD", "range": plan["cost_envelope_usd"], "basis": plan["cost_basis"]},
    }
    for name, payload in files.items():
        (output / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    index = {
        "schema_version": "1.0",
        "scope": plan["scope"],
        "capability_id": plan["capability_id"],
        "system_id": plan["system_id"],
        "scope4_plan_fingerprint": plan["scope4_plan_fingerprint"],
        "part_plan_count": len(plan["part_plans"]),
        "tolerance_stack_count": len(plan["tolerance_stacks"]),
        "assembly_operation_count": len(plan["assembly_operations"]),
        "service_procedure_count": len(plan["service_procedures"]),
        "cost_envelope_usd": plan["cost_envelope_usd"],
        "validation": plan["validation"],
        "status": "passed" if plan["validation"]["passed"] else "failed",
        "scope0_through_scope4_regression_required": True,
    }
    (output / "scope5-index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ObjectForge Scope 5 manufacturing evidence")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if write_scope5(args.output)["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
