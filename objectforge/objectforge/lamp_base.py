from __future__ import annotations

import math
from typing import Any

import numpy as np
import trimesh

from .geometry import BuildOperation, PartRecord, apply_material, build_materials, normalize

class LampBase:
    def __init__(self) -> None:
        self.materials = build_materials()
        self.operations: list[BuildOperation] = []
        self.parts: list[PartRecord] = []
        self._sequence = 0
        self.lower_vector = np.array([0.62, 1.74, 0.0])
        self.upper_vector = np.array([0.82, 1.33, 0.0])
        self.shade_axis = normalize(np.array([0.82, -0.48, 0.08]))
        self.base_radius = 1.18
        self.mass_estimates: dict[str, float] = {}

    def op(self, operator: str, target: str, purpose: str, parameters: dict[str, Any], *, status: str = "accepted",
           before: dict[str, Any] | None = None, after: dict[str, Any] | None = None, recovery_of: int | None = None) -> int:
        self._sequence += 1
        self.operations.append(BuildOperation(
            sequence=self._sequence,
            operator=operator,
            target=target,
            purpose=purpose,
            parameters=parameters,
            status=status,
            metrics_before=before or {},
            metrics_after=after or {},
            recovery_of=recovery_of,
        ))
        return self._sequence

    def add_part(self, node_name: str, geometry_name: str, parent: str, semantic_part: str, material_name: str,
                 geometry: trimesh.Trimesh, local_transform: np.ndarray | None = None,
                 collision: dict[str, Any] | None = None) -> None:
        _spec, material = self.materials[material_name]
        geometry = apply_material(geometry, material)
        geometry.metadata.update({
            "semantic_part": semantic_part,
            "material_name": material_name,
            "objectforge_generated": True,
        })
        self.parts.append(PartRecord(
            node_name=node_name,
            geometry_name=geometry_name,
            parent=parent,
            semantic_part=semantic_part,
            material=material_name,
            geometry=geometry,
            local_transform=np.eye(4) if local_transform is None else local_transform,
            collision=collision,
        ))

    def _evaluate_stability(self, upper_length: float) -> dict[str, float | bool]:
        base_mass = 4.8
        lower_mass = 0.8
        upper_mass = 0.65 * (upper_length / np.linalg.norm(self.upper_vector))
        shade_mass = 0.9
        lower_mid = self.lower_vector * 0.5
        elbow = self.lower_vector
        upper_dir = normalize(self.upper_vector)
        upper_mid = elbow + upper_dir * upper_length * 0.5
        shade_center = elbow + upper_dir * upper_length + self.shade_axis * 0.34
        masses = np.array([base_mass, lower_mass, upper_mass, shade_mass])
        points = np.vstack([[0, 0.12, 0], lower_mid, upper_mid, shade_center])
        center_of_mass = (masses[:, None] * points).sum(axis=0) / masses.sum()
        radial = float(math.hypot(center_of_mass[0], center_of_mass[2]))
        tipping_margin = self.base_radius - radial
        return {
            "center_of_mass_x": round(float(center_of_mass[0]), 4),
            "center_of_mass_z": round(float(center_of_mass[2]), 4),
            "support_radius": self.base_radius,
            "tipping_margin": round(tipping_margin, 4),
            "stable": bool(tipping_margin >= 0.12),
        }

    def plan_and_recover(self) -> dict[str, Any]:
        self.op("seed_blob", "design_matter", "Begin from one stretchable design volume.", {
            "primitive": "ellipsoid_field",
            "dimensions": [0.55, 0.55, 0.55],
            "representation": "semantic_constructive_field",
        })
        self.op("flatten_region", "design_matter.lower", "Create a stable base contact surface.", {
            "axis": "y", "amount": 0.31,
        })
        self.op("split_region", "design_matter", "Separate functional masses while retaining one construction history.", {
            "result_regions": ["base", "lower_arm", "upper_arm", "shade"],
        })

        bad_length = 7.0
        before = self._evaluate_stability(np.linalg.norm(self.upper_vector))
        rejected = self._evaluate_stability(bad_length)
        rejected_sequence = self.op(
            "stretch_region", "upper_arm", "Explore a long reach before accepting the structural proportion.",
            {"requested_length": bad_length, "units": "m"}, status="rejected", before=before, after=rejected,
        )
        self.op("rollback", "construction_checkpoint_03", "Reject the unstable reach and restore the last valid state.", {
            "reason": "center of mass leaves the required tipping margin",
            "rejected_operation": rejected_sequence,
        }, recovery_of=rejected_sequence)
        accepted = self._evaluate_stability(np.linalg.norm(self.upper_vector))
        self.op("stretch_region", "upper_arm", "Apply a bounded reach that preserves support stability.", {
            "accepted_length": round(float(np.linalg.norm(self.upper_vector)), 4), "units": "m",
        }, before=rejected, after=accepted, recovery_of=rejected_sequence)
        return {"rejected": rejected, "recovered": accepted, "rejected_operation": rejected_sequence}
