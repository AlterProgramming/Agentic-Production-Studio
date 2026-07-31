from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class GrammarUse:
    grammar: str
    role: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ObjectPlan:
    schema_version: str
    asset_id: str
    family: str
    variant: str
    intent: str
    grammars: tuple[GrammarUse, ...]
    acceptance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["grammars"] = [asdict(item) for item in self.grammars]
        return payload


class Scope1Planner:
    """Deterministic grammar selector for bounded Scope 1 object families."""
    _plans: dict[tuple[str, str], ObjectPlan] = {}

    @classmethod
    def register(cls, plan: ObjectPlan) -> None:
        key = (plan.family, plan.variant)
        if key in cls._plans:
            raise ValueError(f"duplicate plan {key}")
        cls._plans[key] = plan

    @classmethod
    def resolve(cls, family: str, variant: str) -> ObjectPlan:
        try:
            return cls._plans[(family, variant)]
        except KeyError as exc:
            raise ValueError(f"unsupported Scope 1 object {family}/{variant}") from exc

    @classmethod
    def variants(cls) -> list[tuple[str, str]]:
        return sorted(cls._plans)


def _register_defaults() -> None:
    common = {"canonical_glb": True, "showcase_glb": True, "embedded_pbr_textures": True, "standalone_viewer": True, "construction_ledger": True, "recovery_receipt": True, "external_finished_model_provider": False}
    entries = [
        ObjectPlan("1.0", "scope1-lamp-compact", "lamp", "compact", "Compact single-arm reading lamp", (GrammarUse("support", "weighted_base", {"profile": "compact"}), GrammarUse("articulation", "single_arm", {"hinges": 2}), GrammarUse("shell", "directional_shade", {"profile": "short"}), GrammarUse("joinery", "hinges_and_switch", {}), GrammarUse("detail", "manufacturing_features", {"density": "medium"}), GrammarUse("material", "painted_metal", {"palette": "graphite_warm"})), common | {"minimum_meshes": 24}),
        ObjectPlan("1.0", "scope1-lamp-industrial", "lamp", "industrial", "Twin-arm industrial task lamp", (GrammarUse("support", "weighted_base", {"profile": "wide"}), GrammarUse("articulation", "twin_arm", {"hinges": 3}), GrammarUse("shell", "directional_shade", {"profile": "industrial"}), GrammarUse("repetition", "fasteners_and_vents", {"density": "high"}), GrammarUse("material", "powder_coat", {"palette": "signal_orange"})), common | {"minimum_meshes": 34}),
        ObjectPlan("1.0", "scope1-lamp-domestic", "lamp", "domestic", "Rounded domestic gooseneck lamp", (GrammarUse("support", "weighted_base", {"profile": "soft"}), GrammarUse("articulation", "gooseneck_and_shade", {"hinges": 1}), GrammarUse("shell", "directional_shade", {"profile": "rounded"}), GrammarUse("detail", "soft_edge_treatment", {"density": "medium"}), GrammarUse("material", "painted_metal", {"palette": "ivory_brass"})), common | {"minimum_meshes": 22}),
        ObjectPlan("1.0", "scope1-case-tool", "case", "tool", "Ribbed hard-shell tool case", (GrammarUse("shell", "lower_and_lid", {"profile": "ribbed"}), GrammarUse("articulation", "lid_hinges", {"hinges": 2}), GrammarUse("joinery", "dual_latch_and_handle", {}), GrammarUse("repetition", "ribs_and_corner_fasteners", {"density": "high"}), GrammarUse("material", "molded_plastic", {"palette": "graphite_orange"})), common | {"minimum_meshes": 30}),
        ObjectPlan("1.0", "scope1-case-electronics", "case", "electronics", "Compact electronics transport case", (GrammarUse("shell", "lower_and_lid", {"profile": "compact"}), GrammarUse("articulation", "lid_hinges", {"hinges": 2}), GrammarUse("joinery", "latches_handle_ports", {}), GrammarUse("detail", "corner_guards_and_interior", {"density": "medium"}), GrammarUse("material", "molded_plastic", {"palette": "blue_carbon"})), common | {"minimum_meshes": 26}),
        ObjectPlan("1.0", "scope1-case-presentation", "case", "presentation", "Wood and velvet presentation case", (GrammarUse("shell", "lower_and_lid", {"profile": "presentation"}), GrammarUse("articulation", "brass_lid_hinges", {"hinges": 2}), GrammarUse("joinery", "single_clasp_and_handle", {}), GrammarUse("detail", "edge_band_and_liner", {"density": "high"}), GrammarUse("material", "wood_and_velvet", {"palette": "walnut_brass"})), common | {"minimum_meshes": 24}),
        ObjectPlan("1.0", "scope1-table-four-leg", "table", "four_leg", "Varnished four-leg side table", (GrammarUse("support", "four_leg_frame", {}), GrammarUse("joinery", "aprons_and_brackets", {}), GrammarUse("detail", "edge_band_fasteners", {"density": "medium"}), GrammarUse("material", "varnished_wood", {"palette": "oak"})), common | {"minimum_meshes": 26}),
        ObjectPlan("1.0", "scope1-table-pedestal", "table", "pedestal", "Round pedestal side table", (GrammarUse("support", "pedestal", {}), GrammarUse("joinery", "collar_and_ribs", {}), GrammarUse("detail", "edge_band_fasteners", {"density": "medium"}), GrammarUse("material", "ceramic_and_metal", {"palette": "white_brass"})), common | {"minimum_meshes": 22}),
        ObjectPlan("1.0", "scope1-table-metal-frame", "table", "metal_frame", "Metal-frame inset-top table", (GrammarUse("support", "four_leg_frame", {"profile": "metal"}), GrammarUse("joinery", "crossbars_and_brackets", {}), GrammarUse("detail", "caps_and_fasteners", {"density": "high"}), GrammarUse("material", "metal_and_wood", {"palette": "graphite_walnut"})), common | {"minimum_meshes": 30}),
    ]
    for entry in entries:
        Scope1Planner.register(entry)


_register_defaults()
