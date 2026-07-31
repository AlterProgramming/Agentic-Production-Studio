from __future__ import annotations

import math
import numpy as np

from objectforge.geometry import cylinder_z, rounded_box, rotation_x, rotation_y, translation
from objectforge.grammar.core import Articulation, GrammarAssetBuilder
from objectforge.grammar.library import JoineryGrammar, RepetitionGrammar, ShellGrammar
from objectforge.planning.functional import FunctionalPlan
from .common import _add_knob, _add_label_plate, _new_builder


def _hinge_clearance(depth: float, lid_height: float, angle_degrees: float) -> dict[str, float | bool]:
    angle = math.radians(angle_degrees)
    clearance = depth * math.sin(angle) - lid_height * math.cos(angle)
    return {
        "angle_degrees": angle_degrees,
        "clearance": round(clearance, 4),
        "valid": bool(clearance >= 0.08),
    }


def build_hinged_protective_shell(plan: FunctionalPlan) -> GrammarAssetBuilder:
    builder = _new_builder(plan, "FunctionalRoot")
    width, depth, lower_h, lid_h, wall = 2.58, 1.58, 0.55, 0.34, 0.09
    ShellGrammar.tray(
        builder,
        parent=builder.root_name,
        prefix="Lower",
        size=(width, depth, lower_h),
        wall=wall,
        material="MoldedBlue",
        liner="FabricLiner",
    )

    for index, x in enumerate((-0.76, -0.25, 0.25, 0.76)):
        skid = rounded_box((0.16, 0.075, depth * 0.72), radius=0.028, segments=4)
        builder.add_part(
            f"BottomSkid{index + 1}",
            f"bottom_skid_{index + 1}",
            builder.root_name,
            "support.skid",
            "MoldedBlack",
            skid,
            translation([x, 0.035, 0]),
        )
    for index, (sx, sz) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
        foot = rounded_box((0.22, 0.075, 0.22), radius=0.045, segments=5)
        builder.add_part(
            f"CaseFoot{index + 1}",
            f"case_foot_{index + 1}",
            builder.root_name,
            "support.foot",
            "DarkRubber",
            foot,
            translation([sx * 0.98, 0.025, sz * 0.57]),
        )

    builder.add_node("AccessPivot", builder.root_name, translation([0, lower_h + lid_h, -depth / 2]))
    builder.add_node(
        "AccessShellRoot",
        "AccessPivot",
        translation([0, 0, depth / 2]) @ rotation_x(math.pi),
    )
    builder.add_articulation(
        Articulation("access_hinge", "AccessPivot", "body", "access_shell", (1, 0, 0), (0, 112), 0.72)
    )
    builder.op(
        "articulation.hinge",
        "AccessPivot",
        "Retain repeated access through a bounded protective-shell hinge.",
        {"limits_degrees": [0, 112]},
    )
    ShellGrammar.tray(
        builder,
        parent="AccessShellRoot",
        prefix="Access",
        size=(width, depth, lid_h),
        wall=wall * 0.92,
        material="MoldedBlue",
        liner="FabricLiner",
    )

    for index, x in enumerate(np.linspace(-0.82, 0.82, 5)):
        barrel = cylinder_z(0.082, 0.31, sections=52)
        barrel.apply_transform(rotation_y(math.pi / 2))
        builder.add_part(
            f"HingeBarrel{index + 1}",
            f"hinge_barrel_{index + 1}",
            builder.root_name,
            "access.hinge_barrel",
            "BrushedSteel",
            barrel,
            translation([x, lower_h + lid_h * 0.48, -depth / 2]),
        )
    spine = rounded_box((1.95, 0.10, 0.12), radius=0.035, segments=5)
    builder.add_part(
        "HingeSpine",
        "hinge_spine",
        builder.root_name,
        "access.hinge_spine",
        "MoldedBlack",
        spine,
        translation([0, lower_h + lid_h * 0.50, -depth / 2 - 0.02]),
    )

    for index, x in enumerate((-width * 0.27, 0.0, width * 0.27)):
        JoineryGrammar.latch(
            builder,
            parent=builder.root_name,
            prefix=f"Closure{index + 1}",
            center=[x, lower_h * 0.76, depth / 2 + 0.065],
            material="SignalOrange",
        )
    JoineryGrammar.handle(
        builder,
        parent=builder.root_name,
        prefix="Transport",
        center=[0, lower_h * 0.47, depth / 2 + 0.19],
        width=width * 0.40,
        height=0.36,
        material="DarkRubber",
    )

    for index, (sx, sz) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
        guard = rounded_box((0.22, lower_h * 0.94, 0.22), radius=0.060, segments=6)
        builder.add_part(
            f"LowerImpactGuard{index + 1}",
            f"lower_impact_guard_{index + 1}",
            builder.root_name,
            "protection.corner",
            "SignalOrange",
            guard,
            translation([sx * (width / 2 - 0.11), lower_h * 0.50, sz * (depth / 2 - 0.11)]),
        )
        lid_guard = rounded_box((0.21, lid_h * 0.88, 0.21), radius=0.055, segments=6)
        builder.add_part(
            f"LidImpactGuard{index + 1}",
            f"lid_impact_guard_{index + 1}",
            "AccessShellRoot",
            "protection.lid_corner",
            "SignalOrange",
            lid_guard,
            translation([sx * (width / 2 - 0.11), lid_h * 0.50, sz * (depth / 2 - 0.11)]),
        )
    RepetitionGrammar.ribs(
        builder,
        parent=builder.root_name,
        prefix="LowerStiffener",
        count=9,
        width=0.052,
        depth=0.22,
        start_x=-width * 0.34,
        spacing=width * 0.68 / 8,
        y=lower_h * 0.59,
        z=depth / 2 + 0.050,
        material="MoldedBlack",
    )
    RepetitionGrammar.ribs(
        builder,
        parent="AccessShellRoot",
        prefix="LidStiffener",
        count=9,
        width=0.052,
        depth=0.18,
        start_x=-width * 0.34,
        spacing=width * 0.68 / 8,
        y=lid_h * 0.52,
        z=depth / 2 + 0.045,
        material="MoldedBlack",
    )
    for suffix, center, size in (
        ("Front", [0, lower_h + 0.015, depth / 2 - 0.045], (width - 0.22, 0.040, 0.055)),
        ("Back", [0, lower_h + 0.015, -depth / 2 + 0.045], (width - 0.22, 0.040, 0.055)),
        ("Left", [-width / 2 + 0.045, lower_h + 0.015, 0], (0.055, 0.040, depth - 0.22)),
        ("Right", [width / 2 - 0.045, lower_h + 0.015, 0], (0.055, 0.040, depth - 0.22)),
    ):
        gasket = rounded_box(size, radius=0.016, segments=3)
        builder.add_part(
            f"SealGasket{suffix}",
            f"seal_gasket_{suffix.lower()}",
            builder.root_name,
            "closure.gasket",
            "DarkRubber",
            gasket,
            translation(center),
        )

    for index, x in enumerate((-0.73, -0.25, 0.25, 0.73)):
        divider = rounded_box((0.050, 0.21, depth * 0.70), radius=0.016, segments=4)
        builder.add_part(
            f"InteriorDivider{index + 1}",
            f"interior_divider_{index + 1}",
            builder.root_name,
            "organization.divider",
            "CarbonInsert",
            divider,
            translation([x, wall + 0.13, 0]),
        )
    for index, x in enumerate((-0.50, 0.0, 0.50)):
        pad = rounded_box((0.38, 0.060, 0.52), radius=0.075, segments=6)
        builder.add_part(
            f"InstrumentPad{index + 1}",
            f"instrument_pad_{index + 1}",
            builder.root_name,
            "organization.pad",
            "FabricLiner",
            pad,
            translation([x, wall + 0.055, 0]),
        )
        strap = rounded_box((0.31, 0.025, 0.060), radius=0.018, segments=3)
        builder.add_part(
            f"RetentionStrap{index + 1}",
            f"retention_strap_{index + 1}",
            builder.root_name,
            "organization.retention_strap",
            "DarkRubber",
            strap,
            translation([x, wall + 0.12, 0]),
        )
    valve = cylinder_z(0.065, 0.12, sections=48)
    builder.add_part(
        "PressureValve",
        "pressure_valve",
        builder.root_name,
        "interface.pressure_valve",
        "MoldedBlack",
        valve,
        translation([width / 2 + 0.03, lower_h * 0.46, 0.28]),
    )
    _add_knob(
        builder,
        parent=builder.root_name,
        prefix="ValveCap",
        center=[width / 2 + 0.085, lower_h * 0.46, 0.28],
        radius=0.050,
        axis="z",
        material="MoldedBlack",
    )
    _add_label_plate(
        builder,
        parent=builder.root_name,
        prefix="CaseIdentity",
        center=[0, lower_h * 0.58, depth / 2 + 0.095],
        size=(0.42, 0.035, 0.14),
    )

    bad = _hinge_clearance(depth, lid_h, 7.0)
    high_clearance = _hinge_clearance(depth, lid_h, 106.0)
    offset_clearance = {**_hinge_clearance(depth + 0.06, lid_h, 96.0), "rear_offset_m": 0.06}
    rejected = builder.op(
        "planner.try_alternative",
        "access_system",
        "Test the lowest-profile access motion and detect shell collision.",
        {"alternative": "shallow_hinge_sweep", "angle_degrees": 7.0},
        status="rejected",
        before=high_clearance,
        after=bad,
    )
    builder.op(
        "planner.compare_repairs",
        "access_system",
        "Compare a larger opening angle with a rear-offset hinge repair.",
        {
            "alternatives": [
                {"repair": "increase_opening_angle", "metrics": high_clearance, "complexity": 0.1},
                {"repair": "offset_hinge_axis", "metrics": offset_clearance, "complexity": 0.35},
            ],
            "selected": "increase_opening_angle",
        },
        recovery_of=rejected,
    )
    builder.op(
        "rollback",
        "checkpoint.shell_pair",
        "Restore the prior shell pair and apply the selected non-colliding access range.",
        {"preserved_prior_state": True},
        recovery_of=rejected,
    )
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
    builder.add_body(
        body_id="body",
        node=builder.root_name,
        body_type="static",
        mass=4.4,
        collision={"shape": "rounded_box", "extents": [width, lower_h, depth]},
        friction=0.70,
    )
    builder.add_body(
        body_id="access_shell",
        node="AccessPivot",
        body_type="kinematic",
        mass=1.30,
        collision={"shape": "rounded_box", "extents": [width, lid_h, depth]},
    )
    builder.interaction = {
        "drag_targets": ["AccessPivot"],
        "latches_gate_opening": True,
        "pressure_valve": "PressureValve",
        "snap_poses": ["closed", "inspection", "fully_open"],
    }
    builder.op(
        "refinement.verify_close_inspection",
        "hinged_protective_shell",
        "Verify hinge spine, gasket, corner protection, pressure valve, closure hardware, interior pads, straps, and complete underside.",
        {"detail_groups": ["hinge_spine", "gasket", "impact_guards", "pressure_valve", "interior_retention", "bottom_skids"]},
    )
    builder.op(
        "functional.verify",
        "protected_transport",
        "Verify containment, protection, repeated access, transport, and internal organization.",
        {"covered_requirements": [item.requirement_id for item in plan.brief.requirements], "access_clearance": high_clearance},
    )
    return builder
