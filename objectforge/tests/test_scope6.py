from __future__ import annotations

import json

from objectforge.scope6 import build_scope6_evidence, write_scope6


def test_scope6_validates_reach_loads_failures_and_state_transitions() -> None:
    evidence = build_scope6_evidence()

    assert evidence["validation"]["passed"] is True
    assert len(evidence["reachability"]) == 11
    assert all(item["passed"] for item in evidence["reachability"])
    assert evidence["summary"]["human_route_count"] == evidence["summary"]["task_count"]
    assert evidence["summary"]["robot_route_count"] >= 5
    assert all(item["passed"] for item in evidence["load_cases"])
    assert all(item["passed"] for item in evidence["failure_scenarios"])
    assert evidence["state_machine"]["all_fault_paths_reach_safe_state"] is True


def test_scope6_writes_complete_operational_evidence(tmp_path) -> None:
    index = write_scope6(tmp_path)

    assert index["status"] == "passed"
    assert index["scope0_through_scope5_regression_required"] is True
    for name in (
        "scope6-index.json",
        "operational-validation.json",
        "reachability-matrix.json",
        "load-cases.json",
        "failure-injection.json",
        "state-machine.json",
    ):
        path = tmp_path / name
        assert path.stat().st_size > 100
        json.loads(path.read_text())
