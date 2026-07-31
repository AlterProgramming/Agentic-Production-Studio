from __future__ import annotations

from typing import Any

import numpy as np
import trimesh

from .geometry import apply_material, cylinder_y, plane_xy, plane_xz, translation

class LampContractsMixin:
    def build_scene(self, include_showcase: bool = False) -> trimesh.Scene:
        scene = trimesh.Scene()
        scene.graph.update(frame_to="LampRoot", frame_from="world", matrix=np.eye(4))
        scene.graph.update(frame_to="LowerArmPivot", frame_from="LampRoot", matrix=translation([0, 0.43, 0]))
        scene.graph.update(frame_to="UpperArmPivot", frame_from="LowerArmPivot", matrix=translation(self.lower_vector))
        scene.graph.update(frame_to="ShadePivot", frame_from="UpperArmPivot", matrix=translation(self.upper_vector))
        scene.graph.update(frame_to="BulbLightAnchor", frame_from="ShadePivot", matrix=translation(self.shade_axis * 0.70))

        for part in self.parts:
            scene.add_geometry(
                part.geometry,
                node_name=part.node_name,
                geom_name=part.geometry_name,
                parent_node_name=part.parent,
                transform=part.local_transform,
            )

        if include_showcase:
            floor = apply_material(plane_xz(7.5, 6.2), self.materials["StageFloor"][1])
            scene.add_geometry(floor, node_name="ShowcaseFloor", geom_name="showcase_floor", parent_node_name="world",
                               transform=translation([0.35, -0.18, 0]))
            platform = apply_material(cylinder_y(1.62, 0.12, sections=112), self.materials["StageMatte"][1])
            scene.add_geometry(platform, node_name="ShowcasePlatform", geom_name="showcase_platform", parent_node_name="world",
                               transform=translation([0, -0.02, 0]))
            backdrop = apply_material(plane_xy(7.5, 4.9), self.materials["StageMatte"][1])
            scene.add_geometry(backdrop, node_name="ShowcaseBackdrop", geom_name="showcase_backdrop", parent_node_name="world",
                               transform=translation([0.45, 2.25, -2.8]))
        return scene

    def physics_contract(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "asset": "object/object.glb",
            "units": "meter-kilogram-second",
            "gravity": [0, -9.81, 0],
            "bodies": [
                {"id": "base", "node": "LampRoot", "type": "static", "mass": 4.8,
                 "collision": {"shape": "cylinder", "radius": self.base_radius, "height": 0.28},
                 "friction": 0.72, "restitution": 0.08},
                {"id": "lower_arm", "node": "LowerArmPivot", "type": "kinematic", "mass": 0.8,
                 "collision": {"shape": "capsule_pair", "radius": 0.12, "end": self.lower_vector.round(4).tolist()}},
                {"id": "upper_arm", "node": "UpperArmPivot", "type": "kinematic", "mass": 0.65,
                 "collision": {"shape": "capsule_pair", "radius": 0.11, "end": self.upper_vector.round(4).tolist()}},
                {"id": "shade", "node": "ShadePivot", "type": "kinematic", "mass": 0.9,
                 "collision": {"shape": "convex_frustum", "length": 1.02, "front_radius": 0.69}},
            ],
            "constraints": [
                {"id": "base_hinge", "type": "hinge", "parent": "base", "child": "lower_arm", "axis": [0, 0, 1],
                 "limits_degrees": [-18, 24], "damping": 0.72},
                {"id": "elbow_hinge", "type": "hinge", "parent": "lower_arm", "child": "upper_arm", "axis": [0, 0, 1],
                 "limits_degrees": [-58, 46], "damping": 0.68},
                {"id": "shade_hinge", "type": "hinge", "parent": "upper_arm", "child": "shade", "axis": [0, 0, 1],
                 "limits_degrees": [-44, 38], "damping": 0.62},
            ],
            "interaction": {
                "drag_targets": ["LowerArmPivot", "UpperArmPivot", "ShadePivot"],
                "collision_prevents_self_fold": True,
                "snap_pose": "reading",
            },
            "external_providers": False,
        }

    def semantic_contract(self) -> dict[str, Any]:
        nodes: dict[str, dict[str, Any]] = {}
        for part in self.parts:
            nodes.setdefault(part.semantic_part, {"nodes": [], "material": part.material})["nodes"].append(part.node_name)
        return {
            "schema_version": "1.0",
            "asset_type": "articulated_task_lamp",
            "root": "LampRoot",
            "semantic_parts": nodes,
            "articulations": ["base_hinge", "elbow_hinge", "shade_hinge"],
            "presentation_requirements": {
                "standalone_viewer": True,
                "close_inspection": True,
                "wireframe_toggle": True,
                "lighting_adjustment": True,
                "animation_playback": True,
            },
        }
