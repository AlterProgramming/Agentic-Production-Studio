from __future__ import annotations

import math

from objectforge.geometry import cylinder_y, rounded_box, torus_y, translation
from objectforge.grammar.core import GrammarAssetBuilder
from objectforge.grammar.library import DetailGrammar, JoineryGrammar, RepetitionGrammar, SupportGrammar
from objectforge.planning.planner import ObjectPlan


def _stability(width: float, depth: float, inset: float, top_mass: float) -> dict[str, float | bool]:
    support_half_x = width / 2 - inset
    support_half_z = depth / 2 - inset
    com_offset_x = min(width * 0.15, top_mass * 0.025)
    margin = min(support_half_x - com_offset_x, support_half_z)
    return {"support_half_x": round(support_half_x, 4), "support_half_z": round(support_half_z, 4), "center_of_mass_offset_x": round(com_offset_x, 4), "tipping_margin": round(margin, 4), "stable": bool(margin >= 0.16)}


def _top(builder: GrammarAssetBuilder, *, width: float, depth: float, thickness: float, material: str, y: float, round_profile: bool = False) -> None:
    mesh = cylinder_y(width / 2, thickness, sections=112) if round_profile else rounded_box((width, thickness, depth), radius=min(0.12, thickness * 0.55), segments=7)
    builder.add_part("TableTop", "table_top", builder.root_name, "surface.top", material, mesh, translation([0, y, 0]), {"shape": "cylinder" if round_profile else "box", "extents": [width, thickness, depth]})
    underside = cylinder_y(width * 0.38, thickness * 0.20, sections=80) if round_profile else rounded_box((width * 0.78, thickness * 0.20, depth * 0.76), radius=0.06, segments=5)
    builder.add_part("TopUnderside", "top_underside", builder.root_name, "surface.underside", "CarbonInsert", underside, translation([0, y - thickness * 0.58, 0]))
    if round_profile:
        builder.add_part("TopEdgeRing", "top_edge_ring", builder.root_name, "detail.edge_band", "Brass", torus_y(width / 2, 0.045, 96, 12), translation([0, y + thickness / 2, 0]))
    else:
        DetailGrammar.edge_band(builder, parent=builder.root_name, prefix="TopEdge", size=(width, depth), y=y + thickness * 0.45, thickness=0.045, material="BrushedSteel")


def build_table(plan: ObjectPlan) -> GrammarAssetBuilder:
    variant = plan.variant
    builder = GrammarAssetBuilder(plan.asset_id, "table", variant, "TableRoot", dimensions={})
    config = {
        "four_leg": dict(width=1.78, depth=1.25, height=1.02, top=0.16, top_mat="OakVarnish", frame_mat="OakVarnish", inset=0.18),
        "pedestal": dict(width=1.48, depth=1.48, height=0.98, top=0.14, top_mat="CeramicWhite", frame_mat="Brass", inset=0.16),
        "metal_frame": dict(width=1.92, depth=1.18, height=1.04, top=0.15, top_mat="WalnutVarnish", frame_mat="GraphitePowderCoat", inset=0.15),
    }[variant]
    width, depth, height, thickness = config["width"], config["depth"], config["height"], config["top"]
    builder.op("seed_blob", "table_matter", "Begin from a bounded support-and-surface design field.", {"dimensions": [width, height, depth], "family": "small_furniture"})
    builder.op("split_region", "table_matter", "Separate top, load path, joinery, feet, and edge treatment.", {"regions": ["top", "supports", "joinery", "feet", "surface_detail"]})

    bad = _stability(width, depth, inset=min(width, depth) * 0.46, top_mass=4.8)
    good = _stability(width, depth, inset=config["inset"], top_mass=4.8)
    rejected = builder.op("planner.test_support_inset", "support", "Probe an over-inset support layout that tips under side load.", {"inset": min(width, depth) * 0.46}, status="rejected", before=good, after=bad)
    builder.op("rollback", "table.checkpoint.top", "Restore the prior support footprint.", {"reason": "support polygon too small"}, recovery_of=rejected)
    builder.op("planner.accept_support_inset", "support", "Accept a support footprint with usable tipping margin.", {"inset": config["inset"]}, before=bad, after=good, recovery_of=rejected)
    builder.recovery = {"status": "recovered", "forced_failure": {"operation": rejected, "finding": "insufficient support footprint", "metrics": bad}, "rollback": {"preserved_prior_state": True, "replacement_metrics": good}, "source_overwritten": False}

    if variant == "four_leg":
        positions = SupportGrammar.four_leg_frame(builder, top_size=(width, depth), height=height - thickness, leg_section=0.15, material=config["frame_mat"], inset=config["inset"])
        _top(builder, width=width, depth=depth, thickness=thickness, material=config["top_mat"], y=height - thickness / 2)
        for index, position in enumerate(positions):
            JoineryGrammar.bracket(builder, parent=builder.root_name, prefix=f"Corner{index+1}", center=[position[0], height - thickness - 0.08, position[2]], size=(0.24, 0.16, 0.08), material="Brass")
        RepetitionGrammar.fasteners(builder, parent=builder.root_name, prefix="Top", points=[[-width * 0.34, height - thickness * 0.20, -depth * 0.34], [width * 0.34, height - thickness * 0.20, -depth * 0.34], [-width * 0.34, height - thickness * 0.20, depth * 0.34], [width * 0.34, height - thickness * 0.20, depth * 0.34]], radius=0.035, material="Brass", axis="y")
    elif variant == "pedestal":
        SupportGrammar.pedestal(builder, radius=0.62, height=height - thickness, column_radius=0.19, material=config["frame_mat"])
        _top(builder, width=width, depth=depth, thickness=thickness, material=config["top_mat"], y=height - thickness / 2, round_profile=True)
        for index in range(10):
            angle = 2 * math.pi * index / 10
            builder.add_part(f"TopFastener{index+1}", f"top_fastener_{index+1}", builder.root_name, "detail.fastener", "BrushedSteel", cylinder_y(0.026, 0.035, sections=24), translation([0.48 * math.cos(angle), height - thickness - 0.015, 0.48 * math.sin(angle)]))
    else:
        positions = SupportGrammar.four_leg_frame(builder, top_size=(width, depth), height=height - thickness, leg_section=0.12, material=config["frame_mat"], inset=config["inset"])
        _top(builder, width=width, depth=depth, thickness=thickness, material=config["top_mat"], y=height - thickness / 2)
        for name, extents, pos in [("LowerFrontRail", (width - 0.38, 0.09, 0.10), (0, 0.24, depth / 2 - config["inset"])), ("LowerBackRail", (width - 0.38, 0.09, 0.10), (0, 0.24, -depth / 2 + config["inset"])), ("LowerCenterBrace", (0.10, 0.09, depth - 0.38), (0, 0.24, 0))]:
            builder.add_part(name, name.lower(), builder.root_name, "support.crossbar", config["frame_mat"], rounded_box(extents, radius=0.025, segments=4), translation(pos))
        for index, position in enumerate(positions):
            builder.add_part(f"LegCap{index+1}", f"leg_cap_{index+1}", builder.root_name, "detail.leg_cap", "WarmAluminum", rounded_box((0.15, 0.05, 0.15), radius=0.025, segments=4), translation([position[0], height - thickness - 0.035, position[2]]))
            JoineryGrammar.bracket(builder, parent=builder.root_name, prefix=f"FrameCorner{index+1}", center=[position[0], height - thickness - 0.10, position[2]], size=(0.22, 0.14, 0.075), material="WarmAluminum")

    builder.interaction = {"drag_targets": [], "static_object": True, "contact_surface": "surface.top"}
    builder.op("functional.evaluate", "table", "Verify level top, support footprint, ground contact, and complete underside.", {"top_level": True, "ground_contacts": 4 if variant != "pedestal" else 1, "stability": good})
    builder.op("material.assign", "table", "Assign top, frame, joinery, and foot PBR materials.", {"materials": sorted({part.material for part in builder.parts})})
    return builder
