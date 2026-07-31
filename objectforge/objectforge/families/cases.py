from __future__ import annotations

import math

import numpy as np

from objectforge.geometry import cylinder_y, cylinder_z, rounded_box, rotation_x, rotation_y, translation
from objectforge.grammar.core import Articulation, GrammarAssetBuilder
from objectforge.grammar.library import JoineryGrammar, RepetitionGrammar, ShellGrammar
from objectforge.planning.planner import ObjectPlan


def _hinge_clearance(depth: float, lid_height: float, angle_degrees: float) -> dict[str, float | bool]:
    angle = math.radians(angle_degrees)
    clearance = depth * math.sin(angle) - lid_height * math.cos(angle)
    return {"angle_degrees": angle_degrees, "clearance": round(clearance, 4), "valid": bool(clearance >= 0.08)}


def _corner_guards(builder: GrammarAssetBuilder, *, width: float, depth: float, lower_height: float, material: str) -> None:
    for index, (sx, sz) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
        builder.add_part(f"CornerGuard{index+1}", f"corner_guard_{index+1}", builder.root_name, "shell.corner_guard", material, rounded_box((0.20, lower_height * 0.88, 0.20), radius=0.055, segments=5), translation([sx * (width / 2 - 0.10), lower_height * 0.50, sz * (depth / 2 - 0.10)]))


def _case_hinges(builder: GrammarAssetBuilder, *, width: float, depth: float, lower_height: float, lid_height: float, material: str) -> None:
    pivot_y = lower_height + lid_height
    pivot_z = -depth / 2
    builder.add_node("LidPivot", builder.root_name, translation([0, pivot_y, pivot_z]))
    builder.add_node("LidShellRoot", "LidPivot", translation([0, 0, depth / 2]) @ rotation_x(math.pi))
    builder.op("articulation.lid_hinge", "LidPivot", "Create a lid pivot with two separated hinge barrels.", {"axis": [1, 0, 0], "limits_degrees": [0, 108]})
    builder.add_articulation(Articulation("lid_hinge", "LidPivot", "case_body", "lid", (1, 0, 0), (0, 108), 0.72))
    for index, x in enumerate((-width * 0.28, width * 0.28)):
        barrel = cylinder_y(0.095, 0.36, sections=48)
        barrel.apply_transform(rotation_y(math.pi / 2))
        builder.add_part(f"HingeBarrel{index+1}", f"hinge_barrel_{index+1}", builder.root_name, "joint.hinge_barrel", material, barrel, translation([x, pivot_y - lid_height * 0.50, pivot_z]))
        pin = cylinder_y(0.036, 0.42, sections=32)
        pin.apply_transform(rotation_y(math.pi / 2))
        builder.add_part(f"HingePin{index+1}", f"hinge_pin_{index+1}", builder.root_name, "joint.hinge_pin", "BrushedSteel", pin, translation([x, pivot_y - lid_height * 0.50, pivot_z]))


def build_case(plan: ObjectPlan) -> GrammarAssetBuilder:
    variant = plan.variant
    builder = GrammarAssetBuilder(plan.asset_id, "case", variant, "CaseRoot", dimensions={})
    config = {
        "tool": dict(size=(2.75, 1.75, 0.56), lid=0.34, wall=0.10, shell="MoldedBlack", accent="SignalOrange", liner="FabricLiner"),
        "electronics": dict(size=(2.25, 1.42, 0.46), lid=0.28, wall=0.085, shell="MoldedBlue", accent="CarbonInsert", liner="FabricLiner"),
        "presentation": dict(size=(2.38, 1.50, 0.42), lid=0.26, wall=0.075, shell="WalnutVarnish", accent="Brass", liner="VelvetLiner"),
    }[variant]
    width, depth, lower_height = config["size"]
    lid_height = config["lid"]
    wall = config["wall"]
    shell_material = config["shell"]
    accent = config["accent"]
    liner = config["liner"]

    builder.op("seed_blob", "case_matter", "Begin with one bounded design volume for body and lid.", {"primitive": "rounded_ellipsoid_field", "dimensions": [width, lower_height + lid_height, depth]})
    builder.op("split_region", "case_matter", "Separate lower shell, lid, closure, handle, and protection systems.", {"regions": ["lower_shell", "lid", "hinges", "closure", "handle", "corner_protection"]})
    ShellGrammar.tray(builder, parent=builder.root_name, prefix="Lower", size=(width, depth, lower_height), wall=wall, material=shell_material, liner=liner)
    _case_hinges(builder, width=width, depth=depth, lower_height=lower_height, lid_height=lid_height, material=accent)
    ShellGrammar.tray(builder, parent="LidShellRoot", prefix="Lid", size=(width, depth, lid_height), wall=wall * 0.92, material=shell_material, liner=liner)

    bad = _hinge_clearance(depth, lid_height, 8.0)
    good = _hinge_clearance(depth, lid_height, 104.0)
    rejected = builder.op("planner.test_hinge", "lid_hinge", "Probe a lid orientation that collides with the lower shell.", {"angle_degrees": 8.0}, status="rejected", before=good, after=bad)
    builder.op("rollback", "case.checkpoint.shells", "Restore the non-colliding hinge orientation.", {"reason": "lid-shell clearance below threshold"}, recovery_of=rejected)
    builder.op("planner.accept_hinge", "lid_hinge", "Accept a hinge range with adequate rear clearance.", {"angle_degrees": 104.0}, before=bad, after=good, recovery_of=rejected)
    builder.recovery = {"status": "recovered", "forced_failure": {"operation": rejected, "finding": "lid collision", "metrics": bad}, "rollback": {"preserved_prior_state": True, "replacement_metrics": good}, "source_overwritten": False}

    latch_count = 1 if variant == "presentation" else 2
    latch_xs = [0.0] if latch_count == 1 else [-width * 0.25, width * 0.25]
    for index, x in enumerate(latch_xs):
        JoineryGrammar.latch(builder, parent=builder.root_name, prefix=f"Latch{index+1}", center=[x, lower_height * 0.73, depth / 2 + 0.07], material=accent)
    JoineryGrammar.handle(builder, parent=builder.root_name, prefix="Carry", center=[0, lower_height * 0.56, depth / 2 + 0.18], width=width * 0.36, height=0.34 if variant != "presentation" else 0.28, material="DarkRubber" if variant != "presentation" else "Brass")
    _corner_guards(builder, width=width, depth=depth, lower_height=lower_height, material=accent if variant != "presentation" else "Brass")

    rib_count = {"tool": 8, "electronics": 5, "presentation": 4}[variant]
    spacing = width * 0.68 / max(1, rib_count - 1)
    RepetitionGrammar.ribs(builder, parent=builder.root_name, prefix="Front", count=rib_count, width=0.055, depth=0.20, start_x=-width * 0.34, spacing=spacing, y=lower_height * 0.56, z=depth / 2 + 0.055, material=accent)
    lid_ribs = max(4, rib_count - 1)
    RepetitionGrammar.ribs(builder, parent="LidShellRoot", prefix="LidTop", count=lid_ribs, width=0.06, depth=depth * 0.64, start_x=-width * 0.30, spacing=width * 0.60 / max(1, lid_ribs - 1), y=lid_height + 0.018, z=0, material=accent)

    if variant == "electronics":
        for index, z in enumerate((-0.28, 0.0, 0.28)):
            port = cylinder_z(0.065, 0.11, sections=36)
            builder.add_part(f"CablePort{index+1}", f"cable_port_{index+1}", builder.root_name, "interface.cable_port", "DarkRubber", port, translation([width / 2 + 0.055, lower_height * 0.48, z]) @ rotation_y(math.pi / 2))
    elif variant == "tool":
        builder.add_part("PressureValve", "pressure_valve", builder.root_name, "interface.pressure_valve", "SignalOrange", cylinder_z(0.075, 0.14, sections=40), translation([-width * 0.37, lower_height * 0.50, depth / 2 + 0.08]))
    else:
        builder.add_part("NamePlate", "name_plate", "LidShellRoot", "detail.name_plate", "Brass", rounded_box((0.54, 0.035, 0.20), radius=0.025, segments=4), translation([0, lid_height + 0.025, 0.18]))

    builder.add_body(body_id="case_body", node=builder.root_name, body_type="static", mass=4.4, collision={"shape": "rounded_box", "extents": [width, lower_height, depth]}, friction=0.68)
    builder.add_body(body_id="lid", node="LidPivot", body_type="kinematic", mass=1.2, collision={"shape": "rounded_box", "extents": [width, lid_height, depth]})
    builder.interaction = {"drag_targets": ["LidPivot"], "snap_poses": ["closed", "inspection"], "latches_gate_opening": True}
    builder.op("material.assign", "case", "Assign shell, protection, hardware, and liner PBR materials.", {"materials": sorted({part.material for part in builder.parts})})
    builder.op("physics.define", "case", "Retain lid collision, hinge range, mass, and latch interaction.", {"bodies": 2, "constraints": 1})
    return builder
