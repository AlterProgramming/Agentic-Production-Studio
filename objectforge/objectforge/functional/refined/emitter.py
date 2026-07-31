from __future__ import annotations

import math
import numpy as np

from objectforge.geometry import cylinder_y, rounded_box, rotation_y, torus_y, translation, tube_along
from objectforge.grammar.core import GrammarAssetBuilder
from objectforge.grammar.library import ArticulationGrammar, RepetitionGrammar, ShellGrammar, SupportGrammar
from objectforge.planning.functional import FunctionalPlan
from .common import (
    _add_knob,
    _add_label_plate,
    _add_vent_bank,
    _annulus_y,
    _capsule_parts,
    _helical_spring,
    _new_builder,
    _stability,
)


def build_articulated_emitter(plan: FunctionalPlan) -> GrammarAssetBuilder:
    builder = _new_builder(plan, "FunctionalRoot")
    base_radius, base_height = 0.74, 0.25
    SupportGrammar.weighted_base(
        builder,
        radius=base_radius,
        height=base_height,
        material="GraphitePowderCoat",
        feet=6,
    )

    bezel = torus_y(base_radius * 0.71, 0.030, 96, 14)
    builder.add_part(
        "BaseControlBezel",
        "base_control_bezel",
        builder.root_name,
        "interface.base_bezel",
        "WarmAluminum",
        bezel,
        translation([0, base_height * 0.93, 0]),
    )
    _add_knob(
        builder,
        parent=builder.root_name,
        prefix="IntensityDial",
        center=[0.38, base_height + 0.055, 0.30],
        radius=0.095,
    )
    switch = rounded_box((0.22, 0.065, 0.13), radius=0.030, segments=5)
    builder.add_part(
        "PowerSwitch",
        "power_switch",
        builder.root_name,
        "interface.switch",
        "SwitchPlastic",
        switch,
        translation([-0.38, base_height + 0.045, 0.32]),
    )
    _add_vent_bank(
        builder,
        parent=builder.root_name,
        prefix="BaseVent",
        center=[0, base_height * 0.74, -base_radius * 0.91],
        count=9,
        spacing=0.095,
        size=(0.050, 0.075, 0.030),
    )
    RepetitionGrammar.fasteners(
        builder,
        parent=builder.root_name,
        prefix="BaseService",
        points=[
            [0.43 * math.cos(angle), base_height + 0.025, 0.43 * math.sin(angle)]
            for angle in np.linspace(0, math.tau, 6, endpoint=False)
        ],
        radius=0.024,
    )

    column = cylinder_y(0.115, 1.20, sections=80)
    builder.add_part(
        "ElevationColumn",
        "elevation_column",
        builder.root_name,
        "elevation.column",
        "GraphitePowderCoat",
        column,
        translation([0, base_height + 0.60, 0]),
    )
    boot = torus_y(0.17, 0.042, 72, 14)
    builder.add_part(
        "ColumnBoot",
        "column_boot",
        builder.root_name,
        "joinery.column_boot",
        "DarkRubber",
        boot,
        translation([0, base_height + 0.06, 0]),
    )
    collar = torus_y(0.158, 0.038, 72, 12)
    builder.add_part(
        "ColumnCollar",
        "column_collar",
        builder.root_name,
        "joinery.collar",
        "WarmAluminum",
        collar,
        translation([0, base_height + 1.18, 0]),
    )
    channel = rounded_box((0.075, 0.82, 0.055), radius=0.024, segments=4)
    builder.add_part(
        "ColumnCableChannel",
        "column_cable_channel",
        builder.root_name,
        "interface.cable_channel",
        "MoldedBlack",
        channel,
        translation([0, base_height + 0.66, -0.108]),
    )

    ArticulationGrammar.hinge(
        builder,
        node="ReachPivot",
        parent=builder.root_name,
        transform=translation([0, base_height + 1.22, 0]),
        hinge_id="reach_hinge",
        parent_body="base",
        child_body="reach",
        radius=0.19,
        width=0.19,
        material="SignalOrange",
        limits=(-42, 68),
    )
    arm_end = np.array([0.95, 0.48, 0.0])
    for z in (-0.082, 0.082):
        _capsule_parts(
            builder,
            parent="ReachPivot",
            prefix=f"ReachBar{'L' if z < 0 else 'R'}",
            start=np.array([0.06, 0.0, 0.0]),
            end=arm_end,
            radius=0.052,
            material="GraphitePowderCoat",
            semantic="reach.structure",
            z_offset=z,
        )
    RepetitionGrammar.fasteners(
        builder,
        parent="ReachPivot",
        prefix="ReachBridge",
        points=[
            [0.30, 0.15, -0.092],
            [0.30, 0.15, 0.092],
            [0.63, 0.31, -0.092],
            [0.63, 0.31, 0.092],
        ],
        radius=0.035,
        material="BrushedSteel",
        axis="z",
    )
    spring = _helical_spring(
        np.array([0.18, 0.02, -0.12]),
        np.array([0.78, 0.36, -0.12]),
        radius=0.050,
        turns=11,
    )
    builder.add_part(
        "ReachTensionSpring",
        "reach_tension_spring",
        "ReachPivot",
        "mechanism.tension_spring",
        "BrushedSteel",
        spring,
    )
    for index, point in enumerate(([0.24, 0.12, 0.0], [0.53, 0.26, 0.0], [0.79, 0.40, 0.0])):
        clip = _annulus_y(0.048, 0.066, 0.028, sections=40)
        builder.add_part(
            f"CableClip{index + 1}",
            f"cable_clip_{index + 1}",
            "ReachPivot",
            "interface.cable_clip",
            "DarkRubber",
            clip,
            translation(point),
        )

    ArticulationGrammar.hinge(
        builder,
        node="EmitterPivot",
        parent="ReachPivot",
        transform=translation(arm_end),
        hinge_id="emitter_hinge",
        parent_body="reach",
        child_body="emitter",
        radius=0.16,
        width=0.18,
        material="SignalOrange",
        limits=(-55, 72),
    )
    axis = np.array([0.90, -0.30, 0.0])
    ShellGrammar.shade(
        builder,
        parent="EmitterPivot",
        prefix="Emitter",
        axis=axis,
        length=0.52,
        back_radius=0.20,
        front_radius=0.34,
        material="SignalOrange",
    )
    for side in (-1, 1):
        yoke_points = np.array(
            [[0.06, 0.0, side * 0.22], [0.26, -0.06, side * 0.25], [0.43, -0.13, side * 0.23]]
        )
        builder.add_part(
            f"ShadeYoke{'L' if side < 0 else 'R'}",
            f"shade_yoke_{'l' if side < 0 else 'r'}",
            "EmitterPivot",
            "joint.shade_yoke",
            "WarmAluminum",
            tube_along(yoke_points, radius=0.025, sections=14),
        )
        _add_knob(
            builder,
            parent="EmitterPivot",
            prefix=f"ShadeKnob{'L' if side < 0 else 'R'}",
            center=[0.03, 0, side * 0.20],
            radius=0.063,
            axis="z",
            material="SignalOrange",
        )
    for index, distance in enumerate((0.13, 0.22, 0.31)):
        fin = torus_y(0.205 + index * 0.018, 0.018, 72, 10)
        fin.apply_transform(rotation_y(math.pi / 2))
        fin.apply_translation(axis / np.linalg.norm(axis) * distance)
        builder.add_part(
            f"ShadeCoolingFin{index + 1}",
            f"shade_cooling_fin_{index + 1}",
            "EmitterPivot",
            "detail.cooling_fin",
            "WarmAluminum",
            fin,
        )
    emitter = cylinder_y(0.215, 0.048, sections=80)
    emitter.apply_transform(rotation_y(math.pi / 2))
    emitter.apply_translation(axis / np.linalg.norm(axis) * 0.46)
    builder.add_part(
        "EmitterSurface",
        "emitter_surface",
        "EmitterPivot",
        "emission.surface",
        "WarmEmitter",
        emitter,
    )
    builder.add_node("EmitterLightAnchor", "EmitterPivot", translation(axis / np.linalg.norm(axis) * 0.51))

    cable_points = np.array(
        [[0, base_height + 0.10, -base_radius * 0.72], [0, 0.82, -0.11], [0.18, 1.48, -0.11], [0.76, 1.81, -0.10]]
    )
    builder.add_part(
        "ManagedCable",
        "managed_cable",
        builder.root_name,
        "interface.cable",
        "CableBlack",
        tube_along(cable_points, radius=0.023, sections=16),
    )
    _add_label_plate(
        builder,
        parent=builder.root_name,
        prefix="BaseRating",
        center=[0, base_height * 0.64, base_radius * 0.94],
        size=(0.30, 0.035, 0.12),
    )

    bad = _stability(base_radius, 3.9)
    short = _stability(0.55, 1.00)
    widened = _stability(base_radius, 1.00)
    rejected = builder.op(
        "planner.try_alternative",
        "support_and_reach",
        "Test a low-complexity long-reach alternative against stability.",
        {"alternative": "narrow_base_long_reach", "reach_m": 3.9},
        status="rejected",
        before=widened,
        after=bad,
    )
    builder.op(
        "planner.compare_repairs",
        "support_and_reach",
        "Compare shortening reach against widening the support body.",
        {
            "alternatives": [
                {"repair": "shorten_reach_only", "metrics": short, "utility_loss": 0.21},
                {"repair": "widen_support_and_bound_reach", "metrics": widened, "utility_loss": 0.04},
            ],
            "selected": "widen_support_and_bound_reach",
        },
        recovery_of=rejected,
    )
    builder.op(
        "rollback",
        "checkpoint.functional_layout",
        "Restore the accepted support geometry and bounded reach.",
        {"preserved_prior_state": True},
        recovery_of=rejected,
    )
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
    builder.add_body(
        body_id="reach",
        node="ReachPivot",
        body_type="kinematic",
        mass=0.92,
        collision={"shape": "capsule_pair", "length": 1.04, "radius": 0.07},
    )
    builder.add_body(
        body_id="emitter",
        node="EmitterPivot",
        body_type="kinematic",
        mass=0.86,
        collision={"shape": "convex_frustum", "length": 0.52, "front_radius": 0.34},
    )
    builder.interaction = {
        "drag_targets": ["ReachPivot", "EmitterPivot"],
        "controls": ["IntensityDialBody", "PowerSwitch"],
        "snap_poses": ["task", "stow", "inspection"],
    }
    builder.op(
        "refinement.verify_close_inspection",
        "articulated_emitter",
        "Verify controls, spring mechanism, cable management, joinery, cooling details, and underside completion.",
        {"detail_groups": ["base_controls", "tension_mechanism", "shade_yoke", "cooling_fins", "service_plate"]},
    )
    builder.op(
        "functional.verify",
        "directional_energy",
        "Verify all mandatory support, elevation, direction, emission, and interaction goals.",
        {"covered_requirements": [item.requirement_id for item in plan.brief.requirements], "stability": widened},
    )
    return builder
