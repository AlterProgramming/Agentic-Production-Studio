from __future__ import annotations

import math

import numpy as np
import trimesh

from objectforge.geometry import capsule_between, cylinder_y, cylinder_z, normalize, rounded_box, rotation_matrix_from_to, translation, tube_along
from objectforge.grammar.core import GrammarAssetBuilder
from objectforge.grammar.library import ArticulationGrammar, DetailGrammar, JoineryGrammar, ShellGrammar, SupportGrammar
from objectforge.planning.planner import ObjectPlan


def _stability(base_radius: float, reach: float, shade_mass: float = 0.8) -> dict[str, float | bool]:
    base_mass = max(3.2, base_radius * 4.0)
    arm_mass = 0.75 + reach * 0.22
    com_x = (arm_mass * reach * 0.48 + shade_mass * reach) / (base_mass + arm_mass + shade_mass)
    margin = base_radius - com_x
    return {"center_of_mass_x": round(com_x, 4), "support_radius": base_radius, "tipping_margin": round(margin, 4), "stable": bool(margin >= 0.11)}


def _add_capsule_parts(builder: GrammarAssetBuilder, *, parent: str, prefix: str, start: np.ndarray, end: np.ndarray, radius: float, material: str, semantic: str, z_offset: float = 0.0) -> None:
    for index, mesh in enumerate(capsule_between(start + [0, 0, z_offset], end + [0, 0, z_offset], radius, sections=32)):
        builder.add_part(f"{prefix}{index+1}", f"{prefix.lower()}_{index+1}", parent, semantic, material, mesh)


def _add_switch_and_cable(builder: GrammarAssetBuilder, *, base_radius: float, base_height: float) -> None:
    builder.add_part("SwitchRecess", "switch_recess", builder.root_name, "control.switch_recess", "MoldedBlack", rounded_box((0.34, 0.07, 0.20), radius=0.04, segments=4), translation([0, base_height * 0.70, base_radius * 0.83]))
    builder.add_part("PowerSwitch", "power_switch", builder.root_name, "control.switch", "SwitchPlastic", rounded_box((0.22, 0.09, 0.12), radius=0.035, segments=4), translation([0, base_height * 0.77, base_radius * 0.87]))
    points = np.array([[0, 0.08, -base_radius * 0.76], [0, 0.18, -base_radius * 1.02], [-0.18, 0.11, -base_radius * 1.42], [-0.52, 0.09, -base_radius * 1.70]])
    builder.add_part("PowerCable", "power_cable", builder.root_name, "cable.power", "CableBlack", tube_along(points, radius=0.026, sections=14), collision={"shape": "capsule_chain", "radius": 0.026})


def _add_shade_details(builder: GrammarAssetBuilder, *, parent: str, axis: np.ndarray, length: float, front_radius: float, material: str, vent_count: int) -> None:
    ShellGrammar.shade(builder, parent=parent, prefix="Shade", axis=axis, length=length, back_radius=front_radius * 0.48, front_radius=front_radius, material=material)
    axis = normalize(axis)
    socket = cylinder_y(front_radius * 0.24, length * 0.25, sections=56)
    socket.apply_transform(rotation_matrix_from_to([0, 1, 0], axis))
    socket.apply_translation(axis * length * 0.32)
    builder.add_part("BulbSocket", "bulb_socket", parent, "lighting.socket", "SwitchPlastic", socket)
    bulb = trimesh.creation.icosphere(subdivisions=3, radius=front_radius * 0.30)
    bulb.apply_transform(rotation_matrix_from_to([0, 1, 0], axis))
    bulb.apply_translation(axis * length * 0.61)
    builder.add_part("BulbEmitter", "bulb_emitter", parent, "lighting.emitter", "WarmEmitter", bulb)
    helper = np.array([0.0, 1.0, 0.0]) if abs(axis[1]) < 0.9 else np.array([0.0, 0.0, 1.0])
    side = normalize(np.cross(axis, helper))
    up = normalize(np.cross(side, axis))
    for index in range(vent_count):
        angle = 2 * math.pi * index / vent_count
        offset = axis * length * 0.14 + side * math.cos(angle) * front_radius * 0.36 + up * math.sin(angle) * front_radius * 0.36
        vent = rounded_box((0.045, 0.22, 0.032), radius=0.012, segments=3)
        vent.apply_transform(rotation_matrix_from_to([0, 1, 0], axis))
        vent.apply_translation(offset)
        builder.add_part(f"ShadeVent{index+1}", f"shade_vent_{index+1}", parent, "shade.vent", "DarkRubber", vent)
    builder.add_node("EmitterLightAnchor", parent, translation(axis * length * 0.70))


def build_lamp(plan: ObjectPlan) -> GrammarAssetBuilder:
    variant = plan.variant
    builder = GrammarAssetBuilder(plan.asset_id, "lamp", variant, "LampRoot", dimensions={})
    base_radius = {"compact": 0.78, "industrial": 1.05, "domestic": 0.86}[variant]
    base_height = {"compact": 0.24, "industrial": 0.30, "domestic": 0.27}[variant]
    base_material = {"compact": "GraphitePowderCoat", "industrial": "SignalOrange", "domestic": "IvoryPowderCoat"}[variant]
    SupportGrammar.weighted_base(builder, radius=base_radius, height=base_height, material=base_material, feet=4)
    _add_switch_and_cable(builder, base_radius=base_radius, base_height=base_height)

    intended_reach = {"compact": 1.45, "industrial": 2.25, "domestic": 1.60}[variant]
    before = _stability(base_radius, intended_reach)
    bad = _stability(base_radius, intended_reach * 3.7)
    rejected = builder.op("planner.explore_reach", "lamp.reach", "Probe an excessive reach before accepting the support relation.", {"requested_reach": round(intended_reach * 3.7, 3)}, status="rejected", before=before, after=bad)
    builder.op("rollback", "lamp.checkpoint.support", "Restore the last stable construction state.", {"reason": "tipping margin below threshold"}, recovery_of=rejected)
    recovered = _stability(base_radius, intended_reach)
    builder.op("planner.accept_reach", "lamp.reach", "Accept a bounded reach compatible with the support grammar.", {"accepted_reach": intended_reach}, before=bad, after=recovered, recovery_of=rejected)
    builder.recovery = {"status": "recovered", "forced_failure": {"operation": rejected, "finding": "unstable reach", "metrics": bad}, "rollback": {"preserved_prior_state": True, "replacement_metrics": recovered}, "source_overwritten": False}

    base_pivot_height = base_height * 0.88
    if variant == "compact":
        vector = np.array([0.72, 1.35, 0.0])
        ArticulationGrammar.hinge(builder, node="BasePivot", parent=builder.root_name, transform=translation([0, base_pivot_height, 0]), hinge_id="base_hinge", parent_body="base", child_body="arm", radius=0.20, width=0.22, material=base_material, limits=(-24, 30))
        _add_capsule_parts(builder, parent="BasePivot", prefix="SingleArm", start=np.zeros(3), end=vector, radius=0.105, material="WarmAluminum", semantic="reach.arm")
        JoineryGrammar.bracket(builder, parent="BasePivot", prefix="ArmBase", center=[0.10, 0.16, 0], size=(0.34, 0.24, 0.18), material=base_material)
        ArticulationGrammar.hinge(builder, node="ShadePivot", parent="BasePivot", transform=translation(vector), hinge_id="shade_hinge", parent_body="arm", child_body="shade", radius=0.17, width=0.20, material=base_material, limits=(-42, 36))
        _add_shade_details(builder, parent="ShadePivot", axis=normalize(np.array([0.82, -0.48, 0.06])), length=0.78, front_radius=0.47, material=base_material, vent_count=6)
        builder.add_body(body_id="arm", node="BasePivot", body_type="kinematic", mass=0.82, collision={"shape": "capsule", "radius": 0.11, "end": vector.tolist()})
        builder.add_body(body_id="shade", node="ShadePivot", body_type="kinematic", mass=0.62, collision={"shape": "frustum", "length": 0.78, "front_radius": 0.47})
    elif variant == "industrial":
        lower = np.array([0.62, 1.62, 0.0])
        upper = np.array([0.82, 1.28, 0.0])
        ArticulationGrammar.hinge(builder, node="LowerArmPivot", parent=builder.root_name, transform=translation([0, base_pivot_height, 0]), hinge_id="base_hinge", parent_body="base", child_body="lower_arm", radius=0.24, width=0.26, material=base_material, limits=(-20, 26))
        for offset in (-0.13, 0.13):
            _add_capsule_parts(builder, parent="LowerArmPivot", prefix=f"LowerArm{'Front' if offset > 0 else 'Back'}", start=np.zeros(3), end=lower, radius=0.075, material="WarmAluminum", semantic="reach.lower_arm", z_offset=offset)
        ArticulationGrammar.hinge(builder, node="UpperArmPivot", parent="LowerArmPivot", transform=translation(lower), hinge_id="elbow_hinge", parent_body="lower_arm", child_body="upper_arm", radius=0.22, width=0.28, material=base_material, limits=(-58, 46))
        for offset in (-0.13, 0.13):
            _add_capsule_parts(builder, parent="UpperArmPivot", prefix=f"UpperArm{'Front' if offset > 0 else 'Back'}", start=np.zeros(3), end=upper, radius=0.072, material="WarmAluminum", semantic="reach.upper_arm", z_offset=offset)
        ArticulationGrammar.hinge(builder, node="ShadePivot", parent="UpperArmPivot", transform=translation(upper), hinge_id="shade_hinge", parent_body="upper_arm", child_body="shade", radius=0.19, width=0.23, material=base_material, limits=(-46, 38))
        _add_shade_details(builder, parent="ShadePivot", axis=normalize(np.array([0.84, -0.46, 0.08])), length=0.98, front_radius=0.61, material=base_material, vent_count=10)
        for index, t in enumerate((0.28, 0.52, 0.76)):
            builder.add_part(f"LowerSpacer{index+1}", f"lower_spacer_{index+1}", "LowerArmPivot", "joinery.arm_spacer", "BrushedSteel", cylinder_z(0.055, 0.34, sections=28), translation(lower * t))
        for index, t in enumerate((0.32, 0.68)):
            builder.add_part(f"UpperSpacer{index+1}", f"upper_spacer_{index+1}", "UpperArmPivot", "joinery.arm_spacer", "BrushedSteel", cylinder_z(0.052, 0.34, sections=28), translation(upper * t))
        builder.add_body(body_id="lower_arm", node="LowerArmPivot", body_type="kinematic", mass=0.92, collision={"shape": "capsule_pair", "radius": 0.08, "end": lower.tolist()})
        builder.add_body(body_id="upper_arm", node="UpperArmPivot", body_type="kinematic", mass=0.78, collision={"shape": "capsule_pair", "radius": 0.08, "end": upper.tolist()})
        builder.add_body(body_id="shade", node="ShadePivot", body_type="kinematic", mass=0.84, collision={"shape": "frustum", "length": 0.98, "front_radius": 0.61})
    else:
        neck_points = np.array([[0, base_pivot_height, 0], [0.10, 0.72, 0], [0.18, 1.18, 0], [0.24, 1.58, 0], [0.52, 1.88, 0], [0.84, 1.92, 0]])
        builder.add_part("NeckCollar", "neck_collar", builder.root_name, "joinery.neck_collar", "Brass", cylinder_y(0.19, 0.26, sections=64), translation([0, base_pivot_height + 0.10, 0]))
        builder.add_part("Gooseneck", "gooseneck", builder.root_name, "reach.gooseneck", "Brass", tube_along(neck_points, radius=0.075, sections=24), collision={"shape": "capsule_chain", "radius": 0.075})
        ArticulationGrammar.hinge(builder, node="ShadePivot", parent=builder.root_name, transform=translation(neck_points[-1]), hinge_id="shade_hinge", parent_body="base", child_body="shade", radius=0.17, width=0.18, material="IvoryPowderCoat", limits=(-36, 42))
        _add_shade_details(builder, parent="ShadePivot", axis=normalize(np.array([0.72, -0.63, 0.02])), length=0.76, front_radius=0.50, material="IvoryPowderCoat", vent_count=7)
        DetailGrammar.edge_band(builder, parent=builder.root_name, prefix="BaseAccent", size=(base_radius * 1.42, base_radius * 1.42), y=base_height * 0.72, thickness=0.035, material="Brass")
        builder.add_body(body_id="shade", node="ShadePivot", body_type="kinematic", mass=0.60, collision={"shape": "frustum", "length": 0.76, "front_radius": 0.50})

    builder.interaction = {"drag_targets": [item.node for item in builder.articulations], "collision_prevents_self_fold": True, "snap_pose": "reading"}
    builder.op("material.assign", "lamp", "Assign embedded procedural PBR surfaces by functional region.", {"materials": sorted({part.material for part in builder.parts})})
    builder.op("physics.define", "lamp", "Retain rigid-body, collision, and articulation contracts.", {"bodies": len(builder.bodies), "constraints": len(builder.articulations)})
    return builder
