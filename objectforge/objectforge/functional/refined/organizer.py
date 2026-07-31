from __future__ import annotations

import numpy as np

from objectforge.geometry import cylinder_y, rounded_box, torus_y, translation, tube_along
from objectforge.grammar.core import GrammarAssetBuilder
from objectforge.grammar.library import DetailGrammar, JoineryGrammar, ShellGrammar
from objectforge.planning.functional import FunctionalPlan
from .common import _add_label_plate, _annulus_y, _new_builder


def _distribution_metrics(
    points: list[tuple[float, float]],
    loads: list[float],
    half_width: float,
    half_depth: float,
) -> dict[str, float | bool]:
    total = sum(loads)
    cx = sum(point[0] * load for point, load in zip(points, loads)) / max(total, 1e-9)
    cz = sum(point[1] * load for point, load in zip(points, loads)) / max(total, 1e-9)
    margin = min(half_width - abs(cx), half_depth - abs(cz))
    return {
        "center_of_mass_x": round(cx, 4),
        "center_of_mass_z": round(cz, 4),
        "support_margin": round(margin, 4),
        "stable": bool(margin >= 0.12),
    }


def build_portable_slot_organizer(plan: FunctionalPlan) -> GrammarAssetBuilder:
    builder = _new_builder(plan, "FunctionalRoot")
    width, depth, height, wall = 1.30, 0.68, 0.22, 0.065
    ShellGrammar.tray(
        builder,
        parent=builder.root_name,
        prefix="Retention",
        size=(width, depth, height),
        wall=wall,
        material="MoldedBlack",
        liner="DarkRubber",
    )

    ballast = rounded_box((width * 0.80, 0.085, depth * 0.68), radius=0.055, segments=6)
    builder.add_part(
        "BallastCore",
        "ballast_core",
        builder.root_name,
        "support.ballast",
        "GraphitePowderCoat",
        ballast,
        translation([0, 0.055, 0]),
    )
    for index, (sx, sz) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
        foot = rounded_box((0.17, 0.065, 0.17), radius=0.040, segments=5)
        builder.add_part(
            f"BenchFoot{index + 1}",
            f"bench_foot_{index + 1}",
            builder.root_name,
            "support.foot",
            "DarkRubber",
            foot,
            translation([sx * width * 0.41, 0.020, sz * depth * 0.34]),
        )
        bumper = rounded_box((0.12, 0.16, 0.16), radius=0.045, segments=5)
        builder.add_part(
            f"SideBumper{index + 1}",
            f"side_bumper_{index + 1}",
            builder.root_name,
            "protection.bumper",
            "SignalOrange",
            bumper,
            translation([sx * (width / 2 - 0.055), 0.16, sz * (depth / 2 - 0.075)]),
        )

    lower_deck = rounded_box((width - 0.16, 0.075, depth - 0.16), radius=0.050, segments=6)
    builder.add_part(
        "LowerDeck",
        "lower_deck",
        builder.root_name,
        "organization.lower_deck",
        "CarbonInsert",
        lower_deck,
        translation([0, 0.24, 0]),
    )
    upper_deck = rounded_box((width - 0.28, 0.070, depth * 0.42), radius=0.045, segments=6)
    builder.add_part(
        "UpperDeck",
        "upper_deck",
        builder.root_name,
        "organization.upper_deck",
        "GraphitePowderCoat",
        upper_deck,
        translation([0, 0.45, -0.13]),
    )
    DetailGrammar.edge_band(
        builder,
        parent=builder.root_name,
        prefix="LowerDeckBand",
        size=(width - 0.16, depth - 0.16),
        y=0.255,
        thickness=0.035,
        material="WarmAluminum",
    )
    DetailGrammar.edge_band(
        builder,
        parent=builder.root_name,
        prefix="UpperDeckBand",
        size=(width - 0.28, depth * 0.42),
        y=0.465,
        thickness=0.032,
        material="WarmAluminum",
    )

    JoineryGrammar.handle(
        builder,
        parent=builder.root_name,
        prefix="Portable",
        center=[0, 0.48, -depth / 2 + 0.07],
        width=0.72,
        height=0.46,
        material="DarkRubber",
    )
    for index, x in enumerate((-0.36, 0.36)):
        brace = rounded_box((0.075, 0.46, 0.075), radius=0.026, segments=4)
        builder.add_part(
            f"HandleUpright{index + 1}",
            f"handle_upright_{index + 1}",
            builder.root_name,
            "handle.upright",
            "SignalOrange",
            brace,
            translation([x, 0.47, -depth / 2 + 0.07]),
        )
        JoineryGrammar.bracket(
            builder,
            parent=builder.root_name,
            prefix=f"HandleJoin{index + 1}",
            center=[x, 0.26, -depth / 2 + 0.07],
            size=(0.20, 0.12, 0.10),
            material="WarmAluminum",
        )

    slot_layout = [
        (-0.42, 0.10, 0.31),
        (0.0, 0.10, 0.31),
        (0.42, 0.10, 0.31),
        (-0.32, -0.16, 0.52),
        (0.0, -0.16, 0.52),
        (0.32, -0.16, 0.52),
    ]
    slots_2d: list[tuple[float, float]] = []
    for index, (x, z, y) in enumerate(slot_layout):
        slots_2d.append((x, z))
        cup = _annulus_y(0.070, 0.112, 0.25, sections=64)
        builder.add_part(
            f"RetentionCup{index + 1}",
            f"retention_cup_{index + 1}",
            builder.root_name,
            "organization.retention_socket",
            "MoldedBlue",
            cup,
            translation([x, y, z]),
        )
        insert = cylinder_y(0.068, 0.055, sections=56)
        builder.add_part(
            f"SocketInsert{index + 1}",
            f"socket_insert_{index + 1}",
            builder.root_name,
            "organization.socket_insert",
            "DarkRubber",
            insert,
            translation([x, y - 0.095, z]),
        )
        rim = torus_y(0.113, 0.022, 64, 12)
        builder.add_part(
            f"RetentionRim{index + 1}",
            f"retention_rim_{index + 1}",
            builder.root_name,
            "organization.slot_rim",
            "WarmAluminum",
            rim,
            translation([x, y + 0.125, z]),
        )
        clip_points = np.array(
            [[x - 0.085, y + 0.05, z + 0.06], [x - 0.11, y + 0.15, z], [x - 0.085, y + 0.23, z - 0.04]]
        )
        builder.add_part(
            f"RetentionClip{index + 1}",
            f"retention_clip_{index + 1}",
            builder.root_name,
            "organization.spring_clip",
            "BrushedSteel",
            tube_along(clip_points, radius=0.012, sections=10),
        )
        label = rounded_box((0.20, 0.025, 0.070), radius=0.018, segments=3)
        builder.add_part(
            f"SlotLabel{index + 1}",
            f"slot_label_{index + 1}",
            builder.root_name,
            "organization.slot_label",
            "SignalOrange",
            label,
            translation([x, 0.20 if y < 0.4 else 0.39, depth / 2 + 0.015]),
        )

    for index, x in enumerate((-0.22, 0.22)):
        divider = rounded_box((0.030, 0.18, depth - 0.18), radius=0.010, segments=3)
        builder.add_part(
            f"RetentionDivider{index + 1}",
            f"retention_divider_{index + 1}",
            builder.root_name,
            "organization.divider",
            "CarbonInsert",
            divider,
            translation([x, 0.30, 0]),
        )
    side_grip_points = np.array(
        [[-width / 2 - 0.02, 0.21, -0.17], [-width / 2 - 0.10, 0.28, 0], [-width / 2 - 0.02, 0.21, 0.17]]
    )
    builder.add_part(
        "SideAssistGrip",
        "side_assist_grip",
        builder.root_name,
        "handle.assist_grip",
        "DarkRubber",
        tube_along(side_grip_points, radius=0.026, sections=14),
    )
    _add_label_plate(
        builder,
        parent=builder.root_name,
        prefix="OrganizerIdentity",
        center=[0, 0.16, depth / 2 + 0.055],
        size=(0.34, 0.030, 0.12),
    )

    asymmetric_points = [(0.48, -0.12)] * 3 + [(0.36, 0.18)] * 3
    balanced_points = slots_2d
    loads = [0.9, 0.8, 0.85, 0.75, 0.9, 0.8]
    bad = _distribution_metrics(asymmetric_points, loads, width / 2, depth / 2)
    balanced = _distribution_metrics(balanced_points, loads, width / 2, depth / 2)
    counterweight = _distribution_metrics(
        asymmetric_points + [(-0.56, 0.0)],
        loads + [2.4],
        width / 2,
        depth / 2,
    )
    rejected = builder.op(
        "planner.try_alternative",
        "slot_layout",
        "Test a visually compact one-sided arrangement and detect load imbalance.",
        {"alternative": "one_sided_slots"},
        status="rejected",
        before=balanced,
        after=bad,
    )
    builder.op(
        "planner.compare_repairs",
        "slot_layout",
        "Compare symmetric redistribution against adding dead counterweight.",
        {
            "alternatives": [
                {"repair": "redistribute_slots", "metrics": balanced, "added_mass_kg": 0.0},
                {"repair": "add_counterweight", "metrics": counterweight, "added_mass_kg": 2.4},
            ],
            "selected": "redistribute_slots",
        },
        recovery_of=rejected,
    )
    builder.op(
        "rollback",
        "checkpoint.retention_layout",
        "Restore the tray and apply the balanced visible slot pattern.",
        {"preserved_prior_state": True},
        recovery_of=rejected,
    )
    builder.recovery = {
        "status": "recovered",
        "forced_failure": {
            "operation": rejected,
            "finding": "unbalanced repeated-item layout",
            "metrics": bad,
        },
        "alternative_comparison": [
            {"repair": "redistribute_slots", "metrics": balanced, "accepted": True},
            {"repair": "add_counterweight", "metrics": counterweight, "accepted": False},
        ],
        "rollback": {"preserved_prior_state": True, "replacement_metrics": balanced},
        "source_overwritten": False,
    }
    builder.add_body(
        body_id="organizer",
        node=builder.root_name,
        body_type="dynamic",
        mass=2.7,
        collision={"shape": "rounded_box", "extents": [width, height, depth]},
        friction=0.78,
    )
    builder.interaction = {
        "drag_targets": [builder.root_name],
        "semantic_slots": 6,
        "visible_access": True,
        "portable": True,
        "grips": ["PortableGrip", "SideAssistGrip"],
    }
    builder.op(
        "refinement.verify_close_inspection",
        "portable_slot_organizer",
        "Verify two-tier socket construction, inserts, spring clips, labels, handle joinery, bumpers, ballast, and complete underside.",
        {"detail_groups": ["two_tier_deck", "socket_inserts", "spring_clips", "slot_labels", "handle_joinery", "ballast"]},
    )
    builder.op(
        "functional.verify",
        "visible_organization",
        "Verify six visible retained positions, carry clearance, and stable load distribution.",
        {"covered_requirements": [item.requirement_id for item in plan.brief.requirements], "distribution": balanced},
    )
    return builder
