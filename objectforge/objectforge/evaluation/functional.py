from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from objectforge.grammar.core import GrammarAssetBuilder
from objectforge.planning.functional import FunctionalPlan


@dataclass(frozen=True)
class FunctionalEvaluation:
    passed: bool
    metrics: dict[str, Any]
    failures: tuple[str, ...]


def evaluate_functional_plan(plan: FunctionalPlan) -> FunctionalEvaluation:
    selected = next(item for item in plan.candidates if item.architecture_id == plan.selected_architecture.architecture_id)
    failures: list[str] = []
    if selected.missing_mandatory:
        failures.append("selected architecture misses mandatory requirements")
    if len(plan.candidates) < 3:
        failures.append("fewer than three alternatives compared")
    if plan.brief.to_dict().get("object_class") is not None:
        failures.append("planner received an object class")
    if len({item.score for item in plan.candidates}) < 2:
        failures.append("candidate comparison did not discriminate")
    return FunctionalEvaluation(
        passed=not failures,
        metrics={
            "mandatory_requirement_count": sum(1 for item in plan.brief.requirements if item.mandatory),
            "covered_requirement_count": len(selected.covered),
            "candidate_count": len(plan.candidates),
            "selected_score": selected.score,
            "selected_architecture": selected.architecture_id,
        },
        failures=tuple(failures),
    )


def evaluate_functional_builder(builder: GrammarAssetBuilder, plan: FunctionalPlan) -> FunctionalEvaluation:
    failures: list[str] = []
    if builder.capability_id != "objectforge.goal-directed-functional-construction.v2":
        failures.append("builder does not advertise active Scope 2 revision")
    if builder.functional_metadata.get("selected_architecture") != plan.selected_architecture.architecture_id:
        failures.append("builder architecture differs from planner decision")
    comparisons = builder.recovery.get("alternative_comparison", [])
    if len(comparisons) < 2:
        failures.append("recovery did not compare alternatives")
    if sum(1 for item in comparisons if item.get("accepted")) != 1:
        failures.append("recovery must select one alternative")
    if not builder.recovery.get("rollback", {}).get("preserved_prior_state"):
        failures.append("recovery checkpoint was not preserved")
    verification = [item for item in builder.operations if item.operator == "functional.verify"]
    if not verification:
        failures.append("missing functional verification operation")
    return FunctionalEvaluation(
        passed=not failures,
        metrics={
            "alternative_count": len(comparisons),
            "accepted_alternative": next((item.get("repair") for item in comparisons if item.get("accepted")), None),
            "functional_verification_count": len(verification),
            "operation_count": len(builder.operations),
        },
        failures=tuple(failures),
    )
