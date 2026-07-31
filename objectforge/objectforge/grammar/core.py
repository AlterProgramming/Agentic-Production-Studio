from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import trimesh

from objectforge.geometry import BuildOperation, PartRecord, apply_material, cylinder_y, plane_xy, plane_xz, translation
from .materials import RuntimeMaterial, material_library


@dataclass(frozen=True)
class Articulation:
    id: str
    node: str
    parent_body: str
    child_body: str
    axis: tuple[float, float, float]
    limits_degrees: tuple[float, float]
    damping: float = 0.65


@dataclass
class GrammarAssetBuilder:
    asset_id: str
    family: str
    variant: str
    root_name: str
    dimensions: dict[str, float]
    capability_id: str = "objectforge.grammar-driven-detailed-assets.v1"
    functional_metadata: dict[str, Any] = field(default_factory=dict)
    materials: dict[str, tuple[RuntimeMaterial, Any]] = field(default_factory=material_library)
    parts: list[PartRecord] = field(default_factory=list)
    operations: list[BuildOperation] = field(default_factory=list)
    graph_nodes: dict[str, tuple[str, np.ndarray]] = field(default_factory=dict)
    articulations: list[Articulation] = field(default_factory=list)
    bodies: list[dict[str, Any]] = field(default_factory=list)
    interaction: dict[str, Any] = field(default_factory=dict)
    recovery: dict[str, Any] = field(default_factory=dict)
    _sequence: int = 0

    def __post_init__(self) -> None:
        self.graph_nodes[self.root_name] = ("world", np.eye(4))

    def op(self, operator: str, target: str, purpose: str, parameters: dict[str, Any], *, status: str = "accepted", before: dict[str, Any] | None = None, after: dict[str, Any] | None = None, recovery_of: int | None = None) -> int:
        self._sequence += 1
        self.operations.append(BuildOperation(sequence=self._sequence, operator=operator, target=target, purpose=purpose, parameters=parameters, status=status, metrics_before=before or {}, metrics_after=after or {}, recovery_of=recovery_of))
        return self._sequence

    def add_node(self, name: str, parent: str, transform: np.ndarray | None = None) -> None:
        if name in self.graph_nodes:
            raise ValueError(f"duplicate graph node {name}")
        self.graph_nodes[name] = (parent, np.eye(4) if transform is None else np.asarray(transform, dtype=float))

    def add_part(self, node_name: str, geometry_name: str, parent: str, semantic_part: str, material_name: str, geometry: trimesh.Trimesh, local_transform: np.ndarray | None = None, collision: dict[str, Any] | None = None) -> None:
        if material_name not in self.materials:
            raise KeyError(f"unknown material {material_name}")
        _, material = self.materials[material_name]
        geometry = apply_material(geometry, material)
        geometry.metadata.update({"semantic_part": semantic_part, "material_name": material_name, "objectforge_generated": True, "family": self.family, "variant": self.variant})
        self.parts.append(PartRecord(node_name=node_name, geometry_name=geometry_name, parent=parent, semantic_part=semantic_part, material=material_name, geometry=geometry, local_transform=np.eye(4) if local_transform is None else np.asarray(local_transform, dtype=float), collision=collision))

    def add_body(self, *, body_id: str, node: str, body_type: str, mass: float, collision: dict[str, Any], friction: float = 0.62, restitution: float = 0.06) -> None:
        self.bodies.append({"id": body_id, "node": node, "type": body_type, "mass": round(float(mass), 4), "collision": collision, "friction": friction, "restitution": restitution})

    def add_articulation(self, articulation: Articulation) -> None:
        self.articulations.append(articulation)

    def build_scene(self, include_showcase: bool = False) -> trimesh.Scene:
        scene = trimesh.Scene()
        pending = dict(self.graph_nodes)
        added = {"world"}
        while pending:
            progressed = False
            for name, (parent, matrix) in list(pending.items()):
                if parent in added:
                    scene.graph.update(frame_to=name, frame_from=parent, matrix=matrix)
                    added.add(name)
                    pending.pop(name)
                    progressed = True
            if not progressed:
                raise ValueError(f"unresolved graph parents: {pending}")
        for part in self.parts:
            scene.add_geometry(part.geometry, node_name=part.node_name, geom_name=part.geometry_name, parent_node_name=part.parent, transform=part.local_transform)
        if include_showcase:
            self._add_showcase(scene)
        return scene

    def _add_showcase(self, scene: trimesh.Scene) -> None:
        bounds = scene.bounds
        extents = np.maximum(bounds[1] - bounds[0], 0.1)
        center = (bounds[0] + bounds[1]) / 2.0
        radius = max(float(extents[0]), float(extents[2]), 1.0) * 0.68
        floor = apply_material(plane_xz(max(7.0, extents[0] * 2.8), max(6.0, extents[2] * 2.8)), self.materials["StageFloor"][1])
        scene.add_geometry(floor, node_name="ShowcaseFloor", geom_name="showcase_floor", parent_node_name="world", transform=translation([center[0], bounds[0][1] - 0.06, center[2]]))
        platform = apply_material(cylinder_y(radius, 0.12, sections=96), self.materials["StageMatte"][1])
        scene.add_geometry(platform, node_name="ShowcasePlatform", geom_name="showcase_platform", parent_node_name="world", transform=translation([center[0], bounds[0][1], center[2]]))
        backdrop = apply_material(plane_xy(max(7.5, extents[0] * 3.0), max(5.5, extents[1] * 2.1)), self.materials["StageMatte"][1])
        scene.add_geometry(backdrop, node_name="ShowcaseBackdrop", geom_name="showcase_backdrop", parent_node_name="world", transform=translation([center[0], center[1] + extents[1] * 0.15, bounds[0][2] - max(2.4, extents[2] * 1.2)]))

    def semantic_contract(self) -> dict[str, Any]:
        semantic: dict[str, dict[str, Any]] = {}
        for part in self.parts:
            semantic.setdefault(part.semantic_part, {"nodes": [], "material": part.material})["nodes"].append(part.node_name)
        return {"schema_version": "1.0", "asset_type": self.family, "variant": self.variant, "root": self.root_name, "semantic_parts": semantic, "articulations": [item.id for item in self.articulations], "grammar_driven": True, "capability_id": self.capability_id, "functional_goals": self.functional_metadata.get("requirements", []), "selected_architecture": self.functional_metadata.get("selected_architecture")}

    def physics_contract(self) -> dict[str, Any]:
        return {"schema_version": "1.0", "asset": "object/object.glb", "units": "meter-kilogram-second", "gravity": [0, -9.81, 0], "bodies": self.bodies, "constraints": [{"id": item.id, "type": "hinge", "node": item.node, "parent": item.parent_body, "child": item.child_body, "axis": list(item.axis), "limits_degrees": list(item.limits_degrees), "damping": item.damping} for item in self.articulations], "interaction": self.interaction, "external_providers": False}

    def material_contract(self) -> dict[str, Any]:
        used = sorted({part.material for part in self.parts})
        return {"schema_version": "1.0", "materials": [self.materials[name][0].__dict__ for name in used], "embedded_in_glb": True, "texture_generation": "first_party_procedural", "external_providers": False}

    def operation_jsonl(self) -> bytes:
        return ("\n".join(json.dumps(item.__dict__, sort_keys=True) for item in self.operations) + "\n").encode("utf-8")
