from __future__ import annotations

import math
from typing import Callable

import numpy as np
import trimesh

from objectforge.geometry import (
    capsule_between,
    cylinder_y,
    cylinder_z,
    rounded_box,
    rotation_x,
    rotation_y,
    torus_y,
    translation,
    tube_along,
)
from objectforge.grammar.core import Articulation, GrammarAssetBuilder
from objectforge.grammar.library import ArticulationGrammar, DetailGrammar, JoineryGrammar, RepetitionGrammar, ShellGrammar, SupportGrammar
from objectforge.planning.functional import FunctionalPlan


def _new_builder(plan: FunctionalPlan, root_name: str) -> GrammarAssetBuilder:
    builder = GrammarAssetBuilder(
        plan.asset_id,
        "functional_assembly",
        plan.selected_architecture.architecture_id,
        root_name,
        dimensions={},
        capability_id="objectforge.goal-directed-functional-construction.v1",
        functional_metadata={
            "brief_id": plan.brief.brief_id,
            "intent": plan.brief.intent,
            "requirements": [item.to_dict() for item in plan.brief.requirements],
            "selected_architecture": plan.selected_architecture.architecture_id,
            "candidate_scores": [item.to_dict() for item in plan.candidates],
        },
    )
    builder.op("intent.accept", plan.brief.brief_id, "Accept functional goals without receiving a named object class.", {
        "intent": plan.brief.intent,
        "requirements": [item.function for item in plan.brief.requirements],
        "object_class": None,
    })
    builder.op("planner.compare_architectures", plan.brief.brief_id, "Compare bounded architectures by requirement coverage, risk, complexity, and constraints.", {
        "candidate_scores": [item.to_dict() for item in plan.candidates],
        "selected": plan.selected_architecture.architecture_id,
    })
    return builder


def _capsule_parts(builder: GrammarAssetBuilder, *, parent: str, prefix: str, start: np.ndarray, end: np.ndarray,
                   radius: float, material: str, semantic: str, z_offset: float = 0.0) -> None:
    for index, mesh in enumerate(capsule_between(start + [0, 0, z_offset], end + [0, 0, z_offset], radius, sections=32)):
        builder.add_part(f"{prefix}{index+1}", f"{prefix.lower()}_{index+1}", parent, semantic, material, mesh)


def _stability(base_radius: float, reach: float, end_mass: float = 0.85) -> dict[str, float | bool]:
    base_mass = max(3.4, base_radius * 4.2)
    arm_mass = 0.8 + reach * 0.22
    com = (arm_mass * reach * 0.48 + end_mass * reach) / (base_mass + arm_mass + end_mass)
    margin = base_radius - com
    return {"support_radius": round(base_radius, 4), "center_of_mass_x": round(com, 4), "tipping_margin": round(margin, 4), "stable": bool(margin >= 0.10)}


def build_articulated_emitter(plan: FunctionalPlan) -> GrammarAssetBuilder:
    builder = _new_builder(plan, "FunctionalRoot")
    base_radius, base_height = 0.67, 0.22
    SupportGrammar.weighted_base(builder, radius=base_radius, height=base_height, material="GraphitePowderCoat", feet=5)

    column = cylinder_y(0.105, 1.18, sections=72)
    builder.add_part("ElevationColumn", "elevation_column", builder.root_name, "elevation.column", "GraphitePowderCoat", column,
                     translation([0, base_height + 0.59, 0]))
    collar = torus_y(0.145, 0.035, 64, 12)
    builder.add_part("ColumnCollar", "column_collar", builder.root_name, "joinery.collar", "WarmAluminum", collar,
                     translation([0, base_height + 1.17, 0]))

    ArticulationGrammar.hinge(builder, node="ReachPivot", parent=builder.root_name,
                              transform=translation([0, base_height + 1.20, 0]), hinge_id="reach_hinge",
                              parent_body="base", child_body="reach", radius=0.18, width=0.17,
                              material="SignalOrange", limits=(-42, 68))
    arm_end = np.array([0.86, 0.42, 0.0])
    for z in (-0.075, 0.075):
        _capsule_parts(builder, parent="ReachPivot", prefix=f"ReachBar{'L' if z < 0 else 'R'}",
                       start=np.array([0.05, 0.0, 0.0]), end=arm_end, radius=0.052,
                       material="GraphitePowderCoat", semantic="reach.structure", z_offset=z)
    RepetitionGrammar.fasteners(builder, parent="ReachPivot", prefix="ReachBridge",
                                points=[[0.28, 0.14, -0.085], [0.28, 0.14, 0.085], [0.58, 0.29, -0.085], [0.58, 0.29, 0.085]],
                                radius=0.034, material="BrushedSteel", axis="z")

    ArticulationGrammar.hinge(builder, node="EmitterPivot", parent="ReachPivot", transform=translation(arm_end),
                              hinge_id="emitter_hinge", parent_body="reach", child_body="emitter",
                              radius=0.15, width=0.16, material="SignalOrange", limits=(-55, 72))
    axis = np.array([0.88, -0.32, 0.0])
    ShellGrammar.shade(builder, parent="EmitterPivot", prefix="Emitter", axis=axis, length=0.48,
                       back_radius=0.19, front_radius=0.31, material="SignalOrange")
    emitter = cylinder_y(0.205, 0.045, sections=72)
    emitter.apply_transform(rotation_y(math.pi / 2))
    emitter.apply_translation(axis / np.linalg.norm(axis) * 0.43)
    builder.add_part("EmitterSurface", "emitter_surface", "EmitterPivot", "emission.surface", "WarmEmitter", emitter)
    builder.add_node("EmitterLightAnchor", "EmitterPivot", translation(axis / np.linalg.norm(axis) * 0.48))

    switch = rounded_box((0.24, 0.06, 0.14), radius=0.035, segments=5)
    builder.add_part("ControlSwitch", "control_switch", builder.root_name, "interface.switch", "SwitchPlastic", switch,
                     translation([0, base_height + 0.14, base_radius * 0.77]))
    cable_points = np.array([[0, base_height + 0.12, -base_radius * 0.72], [0, 0.78, -0.10], [0.14, 1.42, -0.10], [0.68, 1.76, -0.09]])
    builder.add_part("ManagedCable", "managed_cable", builder.root_name, "interface.cable", "CableBlack",
                     tube_along(cable_points, radius=0.024, sections=14))

    bad = _stability(base_radius, 3.9)
    short = _stability(0.50, 0.92)
    widened = _stability(base_radius, 0.92)
    rejected = builder.op("planner.try_alternative", "support_and_reach", "Test a low-complexity long-reach alternative against stability.",
                          {"alternative": "narrow_base_long_reach", "reach_m": 3.9}, status="rejected", before=widened, after=bad)
    builder.op("planner.compare_repairs", "support_and_reach", "Compare shortening reach against widening the support body.", {
        "alternatives": [
            {"repair": "shorten_reach_only", "metrics": short, "utility_loss": 0.21},
            {"repair": "widen_support_and_bound_reach", "metrics": widened, "utility_loss": 0.04},
        ],
        "selected": "widen_support_and_bound_reach",
    }, recovery_of=rejected)
    builder.op("rollback", "checkpoint.functional_layout", "Restore the accepted support geometry and bounded reach.",
               {"preserved_prior_state": True}, recovery_of=rejected)
    builder.recovery = {
        "status": "recovered",
        "forced_failure": {"operation": rejected, "finding": "unstable reach", "metrics": bad},
        "alternative_comparison": [
            {"repair": "shorten_reach_only", "metrics": short, "accepted": False},
            {"repair": "widen_support_and_bound_reach", "metrics": widened, "accepted": True},
        ],
        "rollback": {"preserved_prior_state": True, "replacement_metrics": widened},
        "source_overwritten": False,
    }
    builder.add_body(body_id="reach", node="ReachPivot", body_type="kinematic", mass=0.84,
                     collision={"shape": "capsule_pair", "length": 0.96, "radius": 0.07})
    builder.add_body(body_id="emitter", node="EmitterPivot", body_type="kinematic", mass=0.78,
                     collision={"shape": "convex_frustum", "length": 0.48, "front_radius": 0.31})
    builder.interaction = {"drag_targets": ["ReachPivot", "EmitterPivot"], "snap_poses": ["task", "stow", "inspection"]}
    builder.op("functional.verify", "directional_energy", "Verify all mandatory support, elevation, direction, emission, and interaction goals.", {
        "covered_requirements": [item.requirement_id for item in plan.brief.requirements], "stability": widened,
    })
    return builder


def _hinge_clearance(depth: float, lid_height: float, angle_degrees: float) -> dict[str, float | bool]:
    angle = math.radians(angle_degrees)
    clearance = depth * math.sin(angle) - lid_height * math.cos(angle)
    return {"angle_degrees": angle_degrees, "clearance": round(clearance, 4), "valid": bool(clearance >= 0.08)}


def build_hinged_protective_shell(plan: FunctionalPlan) -> GrammarAssetBuilder:
    builder = _new_builder(plan, "FunctionalRoot")
    width, depth, lower_h, lid_h, wall = 2.55, 1.55, 0.52, 0.31, 0.09
    ShellGrammar.tray(builder, parent=builder.root_name, prefix="Lower", size=(width, depth, lower_h), wall=wall,
                      material="MoldedBlue", liner="FabricLiner")
    builder.add_node("AccessPivot", builder.root_name, translation([0, lower_h + lid_h, -depth / 2]))
    builder.add_node("AccessShellRoot", "AccessPivot", translation([0, 0, depth / 2]) @ rotation_x(math.pi))
    builder.add_articulation(Articulation("access_hinge", "AccessPivot", "body", "access_shell", (1, 0, 0), (0, 108), 0.72))
    builder.op("articulation.hinge", "AccessPivot", "Retain repeated access through a bounded protective-shell hinge.", {"limits_degrees": [0, 108]})
    for index, x in enumerate((-width * 0.28, width * 0.28)):
        barrel = cylinder_z(0.09, 0.34, sections=48)
        barrel.apply_transform(rotation_y(math.pi / 2))
        builder.add_part(f"AccessBarrel{index+1}", f"access_barrel_{index+1}", builder.root_name, "access.hinge_barrel", "BrushedSteel", barrel,
                         translation([x, lower_h + lid_h * 0.48, -depth / 2]))
    ShellGrammar.tray(builder, parent="AccessShellRoot", prefix="Access", size=(width, depth, lid_h), wall=wall * 0.92,
                      material="MoldedBlue", liner="FabricLiner")
    for index, x in enumerate((-width * 0.25, width * 0.25)):
        JoineryGrammar.latch(builder, parent=builder.root_name, prefix=f"Closure{index+1}",
                             center=[x, lower_h * 0.74, depth / 2 + 0.07], material="SignalOrange")
    JoineryGrammar.handle(builder, parent=builder.root_name, prefix="Transport", center=[0, lower_h * 0.54, depth / 2 + 0.18],
                          width=width * 0.38, height=0.34, material="DarkRubber")
    for i, (sx, sz) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
        guard = rounded_box((0.20, lower_h * 0.90, 0.20), radius=0.055, segments=5)
        builder.add_part(f"ImpactGuard{i+1}", f"impact_guard_{i+1}", builder.root_name, "protection.corner", "SignalOrange", guard,
                         translation([sx * (width / 2 - 0.10), lower_h * 0.50, sz * (depth / 2 - 0.10)]))
    RepetitionGrammar.ribs(builder, parent=builder.root_name, prefix="Stiffener", count=7, width=0.055, depth=0.20,
                           start_x=-width * 0.32, spacing=width * 0.64 / 6, y=lower_h * 0.56, z=depth / 2 + 0.055,
                           material="SignalOrange")
    for i, x in enumerate((-0.72, -0.24, 0.24, 0.72)):
        divider = rounded_box((0.055, 0.18, depth * 0.68), radius=0.018, segments=4)
        builder.add_part(f"InteriorDivider{i+1}", f"interior_divider_{i+1}", builder.root_name, "organization.divider", "CarbonInsert", divider,
                         translation([x, wall + 0.11, 0]))
    for i, x in enumerate((-0.48, 0.0, 0.48)):
        pad = rounded_box((0.34, 0.055, 0.46), radius=0.07, segments=5)
        builder.add_part(f"InstrumentPad{i+1}", f"instrument_pad_{i+1}", builder.root_name, "organization.pad", "FabricLiner", pad,
                         translation([x, wall + 0.05, 0]))

    bad = _hinge_clearance(depth, lid_h, 7.0)
    high_clearance = _hinge_clearance(depth, lid_h, 104.0)
    offset_clearance = {**_hinge_clearance(depth + 0.06, lid_h, 96.0), "rear_offset_m": 0.06}
    rejected = builder.op("planner.try_alternative", "access_system", "Test the lowest-profile access motion and detect shell collision.",
                          {"alternative": "shallow_hinge_sweep", "angle_degrees": 7.0}, status="rejected", before=high_clearance, after=bad)
    builder.op("planner.compare_repairs", "access_system", "Compare a larger opening angle with a rear-offset hinge repair.", {
        "alternatives": [
            {"repair": "increase_opening_angle", "metrics": high_clearance, "complexity": 0.1},
            {"repair": "offset_hinge_axis", "metrics": offset_clearance, "complexity": 0.35},
        ], "selected": "increase_opening_angle",
    }, recovery_of=rejected)
    builder.op("rollback", "checkpoint.shell_pair", "Restore the prior shell pair and apply the selected non-colliding access range.",
               {"preserved_prior_state": True}, recovery_of=rejected)
    builder.recovery = {
        "status": "recovered",
        "forced_failure": {"operation": rejected, "finding": "access shell collision", "metrics": bad},
        "alternative_comparison": [
            {"repair": "increase_opening_angle", "metrics": high_clearance, "accepted": True},
            {"repair": "offset_hinge_axis", "metrics": offset_clearance, "accepted": False},
        ],
        "rollback": {"preserved_prior_state": True, "replacement_metrics": high_clearance},
        "source_overwritten": False,
    }
    builder.add_body(body_id="body", node=builder.root_name, body_type="static", mass=4.0,
                     collision={"shape": "rounded_box", "extents": [width, lower_h, depth]}, friction=0.68)
    builder.add_body(body_id="access_shell", node="AccessPivot", body_type="kinematic", mass=1.15,
                     collision={"shape": "rounded_box", "extents": [width, lid_h, depth]})
    builder.interaction = {"drag_targets": ["AccessPivot"], "latches_gate_opening": True, "snap_poses": ["closed", "inspection"]}
    builder.op("functional.verify", "protected_transport", "Verify containment, protection, repeated access, transport, and internal organization.", {
        "covered_requirements": [item.requirement_id for item in plan.brief.requirements], "access_clearance": high_clearance,
    })
    return builder


def _support_metrics(width: float, depth: float, load_kg: float, top_height: float) -> dict[str, float | bool]:
    half = min(width, depth) / 2.0
    overturn = load_kg * 9.81 * top_height * 0.08
    resisting = (5.2 + load_kg) * 9.81 * half
    margin = resisting - overturn
    return {"support_half_span": round(half, 4), "design_load_kg": load_kg, "top_height_m": top_height,
            "moment_margin_nm": round(margin, 4), "stable": bool(half >= 0.28 and margin > 10.0)}


def build_four_leg_service_station(plan: FunctionalPlan) -> GrammarAssetBuilder:
    builder = _new_builder(plan, "FunctionalRoot")
    width, depth, height = 1.30, 0.76, 1.02
    positions = SupportGrammar.four_leg_frame(builder, top_size=(width, depth), height=height, leg_section=0.095,
                                               material="GraphitePowderCoat", inset=0.15)
    top = rounded_box((width, 0.105, depth), radius=0.07, segments=7)
    builder.add_part("ServiceSurface", "service_surface", builder.root_name, "surface.load", "WalnutVarnish", top,
                     translation([0, height + 0.052, 0]), {"shape": "box", "extents": [width, 0.105, depth]})
    DetailGrammar.edge_band(builder, parent=builder.root_name, prefix="SurfaceBand", size=(width, depth), y=height + 0.065,
                            thickness=0.055, material="WarmAluminum")
    shelf_y = 0.38
    shelf = rounded_box((width - 0.20, 0.075, depth - 0.16), radius=0.045, segments=6)
    builder.add_part("OpenStorageShelf", "open_storage_shelf", builder.root_name, "storage.open_shelf", "OakVarnish", shelf,
                     translation([0, shelf_y, 0]))
    DetailGrammar.edge_band(builder, parent=builder.root_name, prefix="ShelfBand", size=(width - 0.20, depth - 0.16), y=shelf_y + 0.012,
                            thickness=0.04, material="BrushedSteel")
    for i, pos in enumerate(positions):
        JoineryGrammar.bracket(builder, parent=builder.root_name, prefix=f"LoadJoin{i+1}",
                               center=[pos[0], height - 0.13, pos[2]], size=(0.24, 0.12, 0.08), material="SignalOrange")
    for i, x in enumerate((-0.32, 0.32)):
        grommet = torus_y(0.075, 0.025, 48, 10)
        builder.add_part(f"CableGrommet{i+1}", f"cable_grommet_{i+1}", builder.root_name, "interface.cable_grommet", "DarkRubber", grommet,
                         translation([x, height + 0.11, 0.18]))
    cable_rail = rounded_box((0.72, 0.07, 0.10), radius=0.025, segments=4)
    builder.add_part("CableRail", "cable_rail", builder.root_name, "interface.cable_rail", "MoldedBlack", cable_rail,
                     translation([0, height - 0.24, -depth / 2 + 0.08]))

    bad = _support_metrics(0.42, 0.36, 12, height)
    wider = _support_metrics(width, depth, 12, height)
    pedestal_alt = _support_metrics(0.68, 0.68, 12, height)
    rejected = builder.op("planner.try_alternative", "load_path", "Test a minimum-footprint support layout against the declared working load.",
                          {"alternative": "narrow_four_contact", "width": 0.42, "depth": 0.36}, status="rejected", before=wider, after=bad)
    builder.op("planner.compare_repairs", "load_path", "Compare widening the four-contact frame with switching to a pedestal load path.", {
        "alternatives": [
            {"repair": "widen_four_contact_frame", "metrics": wider, "open_storage_preserved": True},
            {"repair": "switch_to_pedestal", "metrics": pedestal_alt, "open_storage_preserved": False},
        ], "selected": "widen_four_contact_frame",
    }, recovery_of=rejected)
    builder.op("rollback", "checkpoint.load_path", "Restore the open-storage frame and accepted support footprint.",
               {"preserved_prior_state": True}, recovery_of=rejected)
    builder.recovery = {
        "status": "recovered",
        "forced_failure": {"operation": rejected, "finding": "insufficient support footprint", "metrics": bad},
        "alternative_comparison": [
            {"repair": "widen_four_contact_frame", "metrics": wider, "accepted": True},
            {"repair": "switch_to_pedestal", "metrics": pedestal_alt, "accepted": False},
        ],
        "rollback": {"preserved_prior_state": True, "replacement_metrics": wider},
        "source_overwritten": False,
    }
    builder.interaction = {"drag_targets": [], "contact_surface": "surface.load", "open_storage": "storage.open_shelf", "design_load_kg": 12}
    builder.op("functional.verify", "elevated_service", "Verify load support, standing-height surface, open storage, footprint, and cable routing.", {
        "covered_requirements": [item.requirement_id for item in plan.brief.requirements], "support": wider,
    })
    return builder


def _distribution_metrics(points: list[tuple[float, float]], loads: list[float], half_width: float, half_depth: float) -> dict[str, float | bool]:
    total = sum(loads)
    cx = sum(point[0] * load for point, load in zip(points, loads)) / max(total, 1e-9)
    cz = sum(point[1] * load for point, load in zip(points, loads)) / max(total, 1e-9)
    margin = min(half_width - abs(cx), half_depth - abs(cz))
    return {"center_of_mass_x": round(cx, 4), "center_of_mass_z": round(cz, 4), "support_margin": round(margin, 4), "stable": bool(margin >= 0.12)}


def build_portable_slot_organizer(plan: FunctionalPlan) -> GrammarAssetBuilder:
    builder = _new_builder(plan, "FunctionalRoot")
    width, depth, height, wall = 1.22, 0.58, 0.20, 0.065
    ShellGrammar.tray(builder, parent=builder.root_name, prefix="Retention", size=(width, depth, height), wall=wall,
                      material="MoldedBlack", liner="DarkRubber")
    for i, (sx, sz) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
        foot = cylinder_y(0.065, 0.045, sections=28)
        builder.add_part(f"BenchFoot{i+1}", f"bench_foot_{i+1}", builder.root_name, "support.foot", "DarkRubber", foot,
                         translation([sx * (width * 0.41), 0.023, sz * (depth * 0.36)]))
    spine = rounded_box((0.10, 0.82, 0.10), radius=0.035, segments=5)
    builder.add_part("CarrySpine", "carry_spine", builder.root_name, "handle.spine", "SignalOrange", spine,
                     translation([0, 0.54, 0]))
    JoineryGrammar.handle(builder, parent=builder.root_name, prefix="Portable", center=[0, 0.80, 0], width=0.54, height=0.30,
                          material="DarkRubber")
    slots = [(-0.43, -0.16), (-0.15, -0.16), (0.15, -0.16), (0.43, -0.16), (-0.28, 0.16), (0.28, 0.16)]
    for index, (x, z) in enumerate(slots):
        cup = cylinder_y(0.095, 0.24, sections=48)
        builder.add_part(f"RetentionCup{index+1}", f"retention_cup_{index+1}", builder.root_name, "organization.retention_cup", "MoldedBlue", cup,
                         translation([x, 0.24, z]))
        rim = torus_y(0.098, 0.024, 48, 10)
        builder.add_part(f"RetentionRim{index+1}", f"retention_rim_{index+1}", builder.root_name, "organization.slot_rim", "WarmAluminum", rim,
                         translation([x, 0.36, z]))
        marker = rounded_box((0.10, 0.025, 0.045), radius=0.012, segments=3)
        builder.add_part(f"SlotMarker{index+1}", f"slot_marker_{index+1}", builder.root_name, "organization.slot_marker", "SignalOrange", marker,
                         translation([x, 0.12, depth / 2 + 0.015]))
    for i, x in enumerate((-0.32, 0.0, 0.32)):
        divider = rounded_box((0.035, 0.15, depth - 0.16), radius=0.012, segments=3)
        builder.add_part(f"RetentionDivider{i+1}", f"retention_divider_{i+1}", builder.root_name, "organization.divider", "CarbonInsert", divider,
                         translation([x, 0.16, 0]))

    asymmetric_points = [(0.43, -0.16), (0.43, -0.16), (0.43, -0.16), (0.28, 0.16), (0.28, 0.16), (0.28, 0.16)]
    balanced_points = slots
    loads = [0.9, 0.8, 0.85, 0.75, 0.9, 0.8]
    bad = _distribution_metrics(asymmetric_points, loads, width / 2, depth / 2)
    balanced = _distribution_metrics(balanced_points, loads, width / 2, depth / 2)
    counterweight = _distribution_metrics(asymmetric_points + [(-0.5, 0.0)], loads + [2.2], width / 2, depth / 2)
    rejected = builder.op("planner.try_alternative", "slot_layout", "Test a visually compact one-sided arrangement and detect load imbalance.",
                          {"alternative": "one_sided_slots"}, status="rejected", before=balanced, after=bad)
    builder.op("planner.compare_repairs", "slot_layout", "Compare symmetric redistribution against adding dead counterweight.", {
        "alternatives": [
            {"repair": "redistribute_slots", "metrics": balanced, "added_mass_kg": 0.0},
            {"repair": "add_counterweight", "metrics": counterweight, "added_mass_kg": 2.2},
        ], "selected": "redistribute_slots",
    }, recovery_of=rejected)
    builder.op("rollback", "checkpoint.retention_layout", "Restore the tray and apply the balanced visible slot pattern.",
               {"preserved_prior_state": True}, recovery_of=rejected)
    builder.recovery = {
        "status": "recovered",
        "forced_failure": {"operation": rejected, "finding": "unbalanced repeated-item layout", "metrics": bad},
        "alternative_comparison": [
            {"repair": "redistribute_slots", "metrics": balanced, "accepted": True},
            {"repair": "add_counterweight", "metrics": counterweight, "accepted": False},
        ],
        "rollback": {"preserved_prior_state": True, "replacement_metrics": balanced},
        "source_overwritten": False,
    }
    builder.add_body(body_id="organizer", node=builder.root_name, body_type="dynamic", mass=2.3,
                     collision={"shape": "rounded_box", "extents": [width, height, depth]}, friction=0.76)
    builder.interaction = {"drag_targets": [builder.root_name], "semantic_slots": 6, "visible_access": True, "portable": True}
    builder.op("functional.verify", "visible_organization", "Verify six visible retained positions, carry clearance, and stable load distribution.", {
        "covered_requirements": [item.requirement_id for item in plan.brief.requirements], "distribution": balanced,
    })
    return builder


_BUILDERS: dict[str, Callable[[FunctionalPlan], GrammarAssetBuilder]] = {
    "articulated_emitter": build_articulated_emitter,
    "hinged_protective_shell": build_hinged_protective_shell,
    "four_leg_service_station": build_four_leg_service_station,
    "portable_slot_organizer": build_portable_slot_organizer,
}


def build_functional_architecture(plan: FunctionalPlan) -> GrammarAssetBuilder:
    try:
        return _BUILDERS[plan.selected_architecture.builder_key](plan)
    except KeyError as exc:
        raise ValueError(f"selected architecture is not implemented in Scope 2: {plan.selected_architecture.builder_key}") from exc
