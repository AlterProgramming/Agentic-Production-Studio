from __future__ import annotations

import math

import numpy as np
import trimesh

from .geometry import (
    capsule_between, cylinder_between, cylinder_y, cylinder_z, compose, frustum_shell,
    normalize, ring_gear_y, rounded_box, rotation_matrix_from_to, rotation_x, rotation_y,
    scale, torus_y, translation, tube_along,
)

class LampGeometryMixin:
    def build_geometry(self) -> None:
        self.op("refine_surface", "base", "Shape a weighted, inspectable base with underside detail.", {
            "edge_treatment": "layered radii and toroidal fillets", "sections": 96,
        })
        lower_base = cylinder_y(self.base_radius, 0.20, sections=96)
        self.add_part("BaseLower", "base_lower", "LampRoot", "base.shell", "GraphitePowderCoat", lower_base,
                      translation([0, 0.10, 0]), collision={"shape": "cylinder", "radius": self.base_radius, "height": 0.20})
        upper_base = cylinder_y(self.base_radius * 0.86, 0.10, sections=96)
        self.add_part("BaseUpperInset", "base_upper_inset", "LampRoot", "base.upper_inset", "GraphitePowderCoat", upper_base,
                      translation([0, 0.25, 0]))
        base_fillet = torus_y(self.base_radius * 0.89, 0.045, 96, 18)
        self.add_part("BaseFillet", "base_fillet", "LampRoot", "base.edge_fillet", "WarmAluminum", base_fillet,
                      translation([0, 0.20, 0]))
        underside = cylinder_y(self.base_radius * 0.72, 0.06, sections=80)
        self.add_part("BaseUnderside", "base_underside", "LampRoot", "base.underside", "DarkRubber", underside,
                      translation([0, -0.005, 0]))
        for i, (x, z) in enumerate([(0.72, 0.55), (-0.72, 0.55), (0.72, -0.55), (-0.72, -0.55)]):
            foot = cylinder_y(0.13, 0.055, sections=40)
            self.add_part(f"RubberFoot{i+1}", f"rubber_foot_{i+1}", "LampRoot", "base.rubber_foot", "DarkRubber", foot,
                          translation([x, -0.055, z]), collision={"shape": "cylinder", "radius": 0.13, "height": 0.055})

        switch = rounded_box((0.42, 0.10, 0.23), radius=0.055, segments=6)
        switch.apply_transform(rotation_x(math.pi / 2))
        self.add_part("BaseSwitch", "base_switch", "LampRoot", "control.switch", "SwitchPlastic", switch,
                      compose(translation([-0.42, 0.32, 0.74]), rotation_y(-0.18)))
        switch_recess = rounded_box((0.52, 0.04, 0.31), radius=0.07, segments=6)
        switch_recess.apply_transform(rotation_x(math.pi / 2))
        self.add_part("SwitchRecess", "switch_recess", "LampRoot", "control.switch_recess", "DarkRubber", switch_recess,
                      translation([-0.42, 0.285, 0.74]))
        cable_port = torus_y(0.11, 0.025, 48, 12)
        cable_port.apply_transform(rotation_x(math.pi / 2))
        self.add_part("CablePort", "cable_port", "LampRoot", "base.cable_port", "DarkRubber", cable_port,
                      compose(translation([0.0, 0.20, -1.17]), rotation_x(math.pi / 2)))

        y_hinge = 0.43
        support = rounded_box((0.55, 0.50, 0.54), radius=0.12, segments=7)
        self.add_part("BaseHingeSupport", "base_hinge_support", "LampRoot", "joint.base_support", "GraphitePowderCoat", support,
                      translation([0, y_hinge, 0]))
        for side, z in [("Front", 0.34), ("Back", -0.34)]:
            disc = cylinder_z(0.29, 0.095, sections=72)
            self.add_part(f"BaseHingeDisc{side}", f"base_hinge_disc_{side.lower()}", "LampRoot", "joint.base_housing", "WarmAluminum", disc,
                          translation([0, y_hinge, z]))
            bolt = ring_gear_y(0.13, 0.028, 0.08, teeth=28)
            bolt.apply_transform(rotation_x(math.pi / 2))
            self.add_part(f"BaseHingeBolt{side}", f"base_hinge_bolt_{side.lower()}", "LampRoot", "joint.base_fastener", "WarmAluminum", bolt,
                          compose(translation([0, y_hinge, z + (0.07 if z > 0 else -0.07)]), rotation_x(math.pi / 2)))

        self.op("define_joint", "base_hinge", "Create the first retained articulation pivot.", {
            "axis": [0, 0, 1], "limits_degrees": [-18, 24], "damping": 0.72,
        })
        self.op("stretch_region", "lower_arm", "Develop a load-bearing twin-bar lower arm.", {
            "vector": self.lower_vector.round(4).tolist(), "bar_count": 2,
        })
        for idx, z in enumerate((-0.115, 0.115), start=1):
            for piece_idx, mesh in enumerate(capsule_between([0, 0, z], [*self.lower_vector[:2], z], 0.095, sections=36), start=1):
                self.add_part(f"LowerArm{idx}Piece{piece_idx}", f"lower_arm_{idx}_{piece_idx}", "LowerArmPivot",
                              "arm.lower_bar", "GraphitePowderCoat", mesh)
        lower_channel = cylinder_between([0, 0, 0], self.lower_vector, 0.035, sections=20)
        self.add_part("LowerCableChannel", "lower_cable_channel", "LowerArmPivot", "cable.channel", "CableBlack", lower_channel)

        elbow_local = self.lower_vector
        for side, z in [("Front", 0.29), ("Back", -0.29)]:
            disc = cylinder_z(0.25, 0.095, sections=72)
            self.add_part(f"ElbowHousing{side}", f"elbow_housing_{side.lower()}", "LowerArmPivot", "joint.elbow_housing", "WarmAluminum", disc,
                          translation(elbow_local + np.array([0, 0, z])))
        elbow_core = rounded_box((0.48, 0.48, 0.44), radius=0.12, segments=7)
        self.add_part("ElbowCore", "elbow_core", "LowerArmPivot", "joint.elbow_core", "GraphitePowderCoat", elbow_core,
                      translation(elbow_local))

        self.op("define_joint", "elbow_hinge", "Create the second retained articulation pivot.", {
            "axis": [0, 0, 1], "limits_degrees": [-58, 46], "damping": 0.68,
        })
        self.op("stretch_region", "upper_arm", "Develop the bounded upper reach after stability recovery.", {
            "vector": self.upper_vector.round(4).tolist(), "bar_count": 2,
        })
        for idx, z in enumerate((-0.105, 0.105), start=1):
            for piece_idx, mesh in enumerate(capsule_between([0, 0, z], [*self.upper_vector[:2], z], 0.085, sections=34), start=1):
                self.add_part(f"UpperArm{idx}Piece{piece_idx}", f"upper_arm_{idx}_{piece_idx}", "UpperArmPivot",
                              "arm.upper_bar", "GraphitePowderCoat", mesh)
        upper_channel = cylinder_between([0, 0, 0], self.upper_vector, 0.031, sections=18)
        self.add_part("UpperCableChannel", "upper_cable_channel", "UpperArmPivot", "cable.channel", "CableBlack", upper_channel)

        shade_joint = self.upper_vector
        joint_core = cylinder_z(0.22, 0.42, sections=64)
        self.add_part("ShadeJointCore", "shade_joint_core", "UpperArmPivot", "joint.shade_core", "WarmAluminum", joint_core,
                      translation(shade_joint))
        knob = ring_gear_y(0.14, 0.032, 0.09, teeth=30)
        knob.apply_transform(rotation_x(math.pi / 2))
        self.add_part("ShadeAdjustmentKnob", "shade_adjustment_knob", "UpperArmPivot", "joint.shade_knob", "WarmAluminum", knob,
                      compose(translation(shade_joint + np.array([0, 0, 0.28])), rotation_x(math.pi / 2)))

        self.op("define_joint", "shade_hinge", "Allow directional aiming of the shade.", {
            "axis": [0, 0, 1], "limits_degrees": [-44, 38], "damping": 0.62,
        })
        self.op("inflate_region", "shade", "Grow the terminal volume into a directional shade.", {
            "back_radius": 0.34, "front_radius": 0.68, "length": 1.0,
        })
        self.op("subtract_volume", "shade", "Hollow the shade and preserve a visible reflective interior.", {
            "wall_thickness": 0.055, "opening": "front",
        })
        shell = frustum_shell(self.shade_axis, 1.02, 0.34, 0.69, 0.055, sections=96)
        self.add_part("ShadeShell", "shade_shell", "ShadePivot", "shade.outer_shell", "GraphitePowderCoat", shell,
                      collision={"shape": "convex_hull", "approximation": "frustum"})
        reflector = frustum_shell(self.shade_axis, 0.88, 0.27, 0.59, 0.018, sections=96)
        reflector.apply_translation(self.shade_axis * 0.09)
        self.add_part("ShadeReflector", "shade_reflector", "ShadePivot", "shade.inner_reflector", "ReflectorSilver", reflector)
        rim = torus_y(0.69, 0.035, 96, 14)
        rim.apply_transform(rotation_matrix_from_to([0, 1, 0], self.shade_axis))
        rim.apply_translation(self.shade_axis * 1.02)
        self.add_part("ShadeFrontRim", "shade_front_rim", "ShadePivot", "shade.front_rim", "WarmAluminum", rim)
        rear_cap = cylinder_y(0.31, 0.11, sections=80)
        rear_cap.apply_transform(rotation_matrix_from_to([0, 1, 0], self.shade_axis))
        rear_cap.apply_translation(self.shade_axis * 0.02)
        self.add_part("ShadeRearCap", "shade_rear_cap", "ShadePivot", "shade.rear_cap", "GraphitePowderCoat", rear_cap)

        socket = cylinder_y(0.18, 0.28, sections=64)
        socket.apply_transform(rotation_matrix_from_to([0, 1, 0], self.shade_axis))
        socket.apply_translation(self.shade_axis * 0.30)
        self.add_part("BulbSocket", "bulb_socket", "ShadePivot", "lighting.socket", "SwitchPlastic", socket)
        bulb = trimesh.creation.icosphere(subdivisions=3, radius=0.23)
        bulb.apply_transform(compose(rotation_matrix_from_to([0, 1, 0], self.shade_axis), scale([1.0, 1.35, 1.0])))
        bulb.apply_translation(self.shade_axis * 0.58)
        self.add_part("BulbEmitter", "bulb_emitter", "ShadePivot", "lighting.emitter", "WarmEmitter", bulb)

        helper = np.array([0, 1, 0]) if abs(self.shade_axis[1]) < 0.9 else np.array([0, 0, 1])
        side = normalize(np.cross(self.shade_axis, helper))
        up = normalize(np.cross(side, self.shade_axis))
        for i in range(9):
            angle = (i - 4) * 0.12
            offset = up * (0.16 * math.sin(angle)) + side * (0.20 * math.cos(angle)) + self.shade_axis * 0.16
            slot = rounded_box((0.055, 0.28, 0.035), radius=0.018, segments=4)
            slot.apply_transform(rotation_matrix_from_to([0, 1, 0], self.shade_axis))
            slot.apply_translation(offset)
            self.add_part(f"CoolingSlot{i+1}", f"cooling_slot_{i+1}", "ShadePivot", "shade.cooling_slot", "DarkRubber", slot)

        lower_end = np.array([0.0, 0.46, -0.38])
        elbow_world = np.array([0, 0.43, 0]) + self.lower_vector
        shade_world = elbow_world + self.upper_vector
        points = np.array([
            [0.0, 0.18, -1.16], [0.0, 0.34, -0.68], lower_end,
            [self.lower_vector[0] * 0.45, 0.43 + self.lower_vector[1] * 0.45 - 0.05, -0.24],
            [elbow_world[0] - 0.06, elbow_world[1] - 0.08, -0.24],
            [elbow_world[0] + self.upper_vector[0] * 0.55, elbow_world[1] + self.upper_vector[1] * 0.55 - 0.06, -0.22],
            [shade_world[0] - 0.10, shade_world[1] - 0.08, -0.18],
        ])
        cable = tube_along(points, radius=0.027, sections=16)
        self.add_part("PowerCable", "power_cable", "LampRoot", "cable.power", "CableBlack", cable,
                      collision={"shape": "capsule_chain", "radius": 0.027})

        self.op("detail_surface", "lamp", "Add tertiary manufacturing details for close inspection.", {
            "features": ["fillet rings", "rubber feet", "switch recess", "knurled fasteners", "cooling slots", "cable path", "socket"],
        })
        self.op("assign_pbr_materials", "lamp", "Assign embedded procedural PBR textures and light-responsive materials.", {
            "materials": sorted(self.materials.keys()), "texture_source": "first_party_procedural",
        })
        self.op("define_physics", "lamp", "Retain rigid-body and articulation behavior outside renderer-specific code.", {
            "rigid_bodies": 4, "hinges": 3, "collision_proxy_strategy": "semantic_primitives",
        })
