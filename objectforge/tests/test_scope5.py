from __future__ import annotations

import json

from objectforge.scope5 import build_scope5_plan, write_scope5


def test_scope5_covers_manufacturing_tolerances_assembly_and_service() -> None:
    plan = build_scope5_plan()

    assert plan["validation"]["passed"] is True
    assert len(plan["part_plans"]) == 6
    assert len(plan["tolerance_stacks"]) == 9
    assert all(item["passed"] for item in plan["tolerance_stacks"])
    assert {item["operation_id"] for item in plan["assembly_operations"]} >= {"A00", "A90", "A95"}
    assert {item["object_id"] for item in plan["service_procedures"]} >= {
        "power_module",
        "analysis_module",
        "work_emitter",
        "protected_carrier",
    }
    assert plan["cost_envelope_usd"][0] < plan["cost_envelope_usd"][1]


def test_scope5_writes_complete_evidence(tmp_path) -> None:
    index = write_scope5(tmp_path)

    assert index["status"] == "passed"
    assert index["scope0_through_scope4_regression_required"] is True
    for name in (
        "scope5-index.json",
        "manufacturing-plan.json",
        "tolerance-stacks.json",
        "assembly-sequence.json",
        "service-plan.json",
        "cost-envelope.json",
    ):
        path = tmp_path / name
        assert path.stat().st_size > 100
        json.loads(path.read_text())
