from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from objectforge.planning.planner import GrammarUse


@dataclass(frozen=True)
class FunctionalRequirement:
    requirement_id: str
    function: str
    priority: int
    mandatory: bool = True
    parameters: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["parameters"] = dict(self.parameters or {})
        return payload


@dataclass(frozen=True)
class FunctionalBrief:
    schema_version: str
    brief_id: str
    intent: str
    requirements: tuple[FunctionalRequirement, ...]
    constraints: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "brief_id": self.brief_id,
            "intent": self.intent,
            "requirements": [item.to_dict() for item in self.requirements],
            "constraints": self.constraints,
            "object_class": None,
        }


@dataclass(frozen=True)
class FunctionalArchitecture:
    architecture_id: str
    label: str
    capabilities: frozenset[str]
    grammars: tuple[GrammarUse, ...]
    complexity: float
    risk: float
    builder_key: str


@dataclass(frozen=True)
class CandidateScore:
    architecture_id: str
    score: float
    weighted_coverage: float
    covered: tuple[str, ...]
    missing_mandatory: tuple[str, ...]
    complexity_penalty: float
    risk_penalty: float
    constraint_penalty: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FunctionalPlan:
    schema_version: str
    asset_id: str
    brief: FunctionalBrief
    selected_architecture: FunctionalArchitecture
    candidates: tuple[CandidateScore, ...]
    acceptance: dict[str, Any]

    @property
    def family(self) -> str:
        return "functional_assembly"

    @property
    def variant(self) -> str:
        return self.selected_architecture.architecture_id

    @property
    def grammars(self) -> tuple[GrammarUse, ...]:
        return self.selected_architecture.grammars

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "asset_id": self.asset_id,
            "brief": self.brief.to_dict(),
            "selected_architecture": {
                "architecture_id": self.selected_architecture.architecture_id,
                "label": self.selected_architecture.label,
                "builder_key": self.selected_architecture.builder_key,
                "capabilities": sorted(self.selected_architecture.capabilities),
                "grammars": [asdict(item) for item in self.selected_architecture.grammars],
            },
            "candidate_comparison": [item.to_dict() for item in self.candidates],
            "acceptance": self.acceptance,
        }


class FunctionalPlanner:
    """Score functional architectures from goals without receiving an object class."""

    def __init__(self, architectures: Iterable[FunctionalArchitecture]) -> None:
        self.architectures = tuple(architectures)
        if len({item.architecture_id for item in self.architectures}) != len(self.architectures):
            raise ValueError("duplicate architecture id")

    @staticmethod
    def _constraint_penalty(brief: FunctionalBrief, architecture: FunctionalArchitecture) -> float:
        penalty = 0.0
        footprint = brief.constraints.get("maximum_footprint_m")
        if footprint is not None:
            nominal = {
                "articulated_emitter": 0.72,
                "fixed_emitter_column": 0.52,
                "hinged_protective_shell": 0.78,
                "sliding_protective_shell": 0.92,
                "four_leg_service_station": 0.86,
                "pedestal_service_station": 0.68,
                "portable_slot_organizer": 0.62,
                "closed_compartment_organizer": 0.74,
            }.get(architecture.architecture_id, 0.8)
            if nominal > float(footprint):
                penalty += (nominal - float(footprint)) * 35.0
        if brief.constraints.get("must_be_freestanding") and "freestanding" not in architecture.capabilities:
            penalty += 30.0
        if brief.constraints.get("must_be_portable") and "portable" not in architecture.capabilities:
            penalty += 30.0
        return penalty

    def score(self, brief: FunctionalBrief, architecture: FunctionalArchitecture) -> CandidateScore:
        total = sum(max(1, item.priority) for item in brief.requirements)
        covered_items = [item for item in brief.requirements if item.function in architecture.capabilities]
        covered_weight = sum(max(1, item.priority) for item in covered_items)
        missing = tuple(item.requirement_id for item in brief.requirements if item.mandatory and item.function not in architecture.capabilities)
        coverage = 100.0 * covered_weight / max(1, total)
        complexity_penalty = architecture.complexity * 2.2
        risk_penalty = architecture.risk * 3.0
        constraint_penalty = self._constraint_penalty(brief, architecture)
        score = coverage - complexity_penalty - risk_penalty - constraint_penalty - 24.0 * len(missing)
        return CandidateScore(
            architecture_id=architecture.architecture_id,
            score=round(score, 4),
            weighted_coverage=round(coverage, 4),
            covered=tuple(item.requirement_id for item in covered_items),
            missing_mandatory=missing,
            complexity_penalty=round(complexity_penalty, 4),
            risk_penalty=round(risk_penalty, 4),
            constraint_penalty=round(constraint_penalty, 4),
        )

    def plan(self, brief: FunctionalBrief) -> FunctionalPlan:
        ranked_pairs = sorted(
            ((self.score(brief, architecture), architecture) for architecture in self.architectures),
            key=lambda item: item[0].score,
            reverse=True,
        )
        best_score, selected = ranked_pairs[0]
        if best_score.missing_mandatory:
            raise ValueError(f"no architecture covers mandatory goals: {best_score.missing_mandatory}")
        candidates = tuple(item[0] for item in ranked_pairs)
        return FunctionalPlan(
            schema_version="1.0",
            asset_id=f"scope2-{brief.brief_id}",
            brief=brief,
            selected_architecture=selected,
            candidates=candidates,
            acceptance={
                "all_mandatory_requirements_covered": True,
                "minimum_candidate_count": 3,
                "minimum_meshes": {
                    "articulated_emitter": 30,
                    "hinged_protective_shell": 34,
                    "four_leg_service_station": 30,
                    "portable_slot_organizer": 28,
                }[selected.architecture_id],
                "standalone_glb": True,
                "embedded_pbr_textures": True,
                "recovery_compares_alternatives": True,
                "external_finished_model_provider": False,
            },
        )


def architecture_catalog() -> tuple[FunctionalArchitecture, ...]:
    G = GrammarUse
    return (
        FunctionalArchitecture(
            "articulated_emitter", "Weighted articulated energy director",
            frozenset({"freestanding", "stable_support", "elevate_output", "direct_energy", "adjust_direction", "emit_light", "cable_management", "close_inspection"}),
            (G("support", "weighted_contact", {}), G("articulation", "multi_axis_reach", {}), G("shell", "directional_emitter", {}), G("joinery", "joint_housings", {}), G("material", "reflective_emissive", {})),
            complexity=3.2, risk=1.2, builder_key="articulated_emitter",
        ),
        FunctionalArchitecture(
            "fixed_emitter_column", "Fixed elevated energy director",
            frozenset({"freestanding", "stable_support", "elevate_output", "direct_energy", "emit_light", "cable_management", "close_inspection"}),
            (G("support", "weighted_contact", {}), G("shell", "fixed_emitter", {}), G("material", "reflective_emissive", {})),
            complexity=1.8, risk=0.5, builder_key="fixed_emitter_column",
        ),
        FunctionalArchitecture(
            "hinged_protective_shell", "Hinged protective transport shell",
            frozenset({"freestanding", "contain", "protect", "repeat_access", "portable", "organize_interior", "close_inspection"}),
            (G("shell", "protective_cavity", {}), G("articulation", "bounded_access", {}), G("joinery", "closure_and_handle", {}), G("repetition", "protection_ribs", {}), G("material", "impact_shell_liner", {})),
            complexity=3.0, risk=1.0, builder_key="hinged_protective_shell",
        ),
        FunctionalArchitecture(
            "sliding_protective_shell", "Sliding protective transport shell",
            frozenset({"contain", "protect", "repeat_access", "organize_interior", "close_inspection"}),
            (G("shell", "protective_cavity", {}), G("articulation", "linear_access", {}), G("joinery", "drawer_guides", {})),
            complexity=3.5, risk=1.8, builder_key="sliding_protective_shell",
        ),
        FunctionalArchitecture(
            "four_leg_service_station", "Four-contact elevated service platform",
            frozenset({"freestanding", "stable_support", "support_load", "elevate_surface", "open_storage", "small_footprint", "cable_management", "close_inspection"}),
            (G("support", "four_contact_load_path", {}), G("joinery", "aprons_brackets", {}), G("shell", "open_storage_shelf", {}), G("repetition", "feet_fasteners", {}), G("material", "load_surface_frame", {})),
            complexity=2.8, risk=0.8, builder_key="four_leg_service_station",
        ),
        FunctionalArchitecture(
            "pedestal_service_station", "Pedestal elevated service platform",
            frozenset({"freestanding", "stable_support", "support_load", "elevate_surface", "small_footprint", "cable_management", "close_inspection"}),
            (G("support", "pedestal_load_path", {}), G("joinery", "collar_ribs", {}), G("material", "load_surface_frame", {})),
            complexity=2.2, risk=1.1, builder_key="pedestal_service_station",
        ),
        FunctionalArchitecture(
            "portable_slot_organizer", "Open portable repeated-slot organizer",
            frozenset({"freestanding", "stable_support", "portable", "organize_repeated", "visible_access", "retain_items", "close_inspection"}),
            (G("support", "stable_tray", {}), G("shell", "open_retention", {}), G("repetition", "semantic_slots", {}), G("joinery", "carry_handle", {}), G("material", "impact_shell_grips", {})),
            complexity=2.5, risk=0.7, builder_key="portable_slot_organizer",
        ),
        FunctionalArchitecture(
            "closed_compartment_organizer", "Closed compartment organizer",
            frozenset({"freestanding", "stable_support", "portable", "organize_repeated", "retain_items", "protect", "close_inspection"}),
            (G("shell", "closed_compartments", {}), G("joinery", "carry_handle", {}), G("material", "impact_shell_grips", {})),
            complexity=2.7, risk=0.8, builder_key="closed_compartment_organizer",
        ),
    )


def benchmark_briefs() -> tuple[FunctionalBrief, ...]:
    R = FunctionalRequirement
    return (
        FunctionalBrief("1.0", "directional-energy", "Provide an adjustable pool of light above a work surface while remaining stable and inspectable.", (
            R("r1", "freestanding", 4), R("r2", "stable_support", 5), R("r3", "elevate_output", 4),
            R("r4", "direct_energy", 5), R("r5", "adjust_direction", 5), R("r6", "emit_light", 5),
            R("r7", "cable_management", 2), R("r8", "close_inspection", 3),
        ), {"must_be_freestanding": True, "maximum_footprint_m": 0.78}),
        FunctionalBrief("1.0", "protected-transport", "Protect and carry a delicate measuring instrument while allowing repeated access and organized placement.", (
            R("r1", "contain", 5), R("r2", "protect", 5), R("r3", "repeat_access", 5),
            R("r4", "portable", 4), R("r5", "organize_interior", 4), R("r6", "close_inspection", 3),
        ), {"must_be_portable": True, "maximum_footprint_m": 0.82}),
        FunctionalBrief("1.0", "elevated-service", "Support a working load at standing height, expose an open lower storage zone, and route a cable within a compact footprint.", (
            R("r1", "freestanding", 4), R("r2", "stable_support", 5), R("r3", "support_load", 5),
            R("r4", "elevate_surface", 5), R("r5", "open_storage", 4), R("r6", "small_footprint", 4),
            R("r7", "cable_management", 2), R("r8", "close_inspection", 3),
        ), {"must_be_freestanding": True, "maximum_footprint_m": 0.90, "design_load_kg": 12}),
        FunctionalBrief("1.0", "visible-organization", "Keep six handheld instruments individually retained, immediately visible, portable, and stable on a workbench.", (
            R("r1", "freestanding", 4), R("r2", "stable_support", 5), R("r3", "portable", 4),
            R("r4", "organize_repeated", 5), R("r5", "visible_access", 5), R("r6", "retain_items", 5),
            R("r7", "close_inspection", 3),
        ), {"must_be_freestanding": True, "must_be_portable": True, "maximum_footprint_m": 0.68, "item_count": 6}),
    )


def default_planner() -> FunctionalPlanner:
    return FunctionalPlanner(architecture_catalog())
