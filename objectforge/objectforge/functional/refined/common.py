from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import trimesh

from objectforge.geometry import (
    capsule_between,
    cylinder_y,
    cylinder_z,
    rounded_box,
    rotation_x,
    torus_y,
    translation,
    tube_along,
)
from objectforge.grammar.core import GrammarAssetBuilder
from objectforge.grammar.library import RepetitionGrammar
from objectforge.planning.functional import FunctionalPlan


CAPABILITY_ID = "objectforge.goal-directed-functional-construction.v2"


def _new_builder(plan: FunctionalPlan, root_name: str) -> GrammarAssetBuilder:
    builder = GrammarAssetBuilder(
        plan.asset_id,
        "functional_assembly",
        plan.selected_architecture.architecture_id,
        root_name,
        dimensions={},
        capability_id=CAPABILITY_ID,
        functional_metadata={
            "brief_id": plan.brief.brief_id,
            "intent": plan.brief.intent,
            "requirements": [item.to_dict() for item in plan.brief.requirements],
            "selected_architecture": plan.selected_architecture.architecture_id,
            "candidate_scores": [item.to_dict() for item in plan.candidates],
            "quality_revision": 2,
            "completion_standard": "standalone_close_inspection",
        },
    )
    builder.op(
        "intent.accept",
        plan.brief.brief_id,
        "Accept functional goals without receiving a named object class.",
        {
            "intent": plan.brief.intent,
            "requirements": [item.function for item in plan.brief.requirements],
            "object_class": None,
        },
    )
    builder.op(
        "planner.compare_architectures",
        plan.brief.brief_id,
        "Compare bounded architectures by requirement coverage, risk, complexity, and constraints.",
        {
            "candidate_scores": [item.to_dict() for item in plan.candidates],
            "selected": plan.selected_architecture.architecture_id,
        },
    )
    builder.op(
        "refinement.declare_quality_target",
        plan.brief.brief_id,
        "Require the selected architecture to survive close inspection as a finished standalone asset.",
        {
            "minimum_components": 48,
            "minimum_semantic_classes": 14,
            "minimum_material_classes": 6,
            "requires_joinery": True,
            "requires_controls_or_affordances": True,
            "requires_underside_or_back_completion": True,
        },
    )
    return builder


def _capsule_parts(
    builder: GrammarAssetBuilder,
    *,
    parent: str,
    prefix: str,
    start: np.ndarray,
    end: np.ndarray,
    radius: float,
    material: str,
    semantic: str,
    z_offset: float = 0.0,
) -> None:
    for index, mesh in enumerate(
        capsule_between(start + [0, 0, z_offset], end + [0, 0, z_offset], radius, sections=40)
    ):
        builder.add_part(
            f"{prefix}{index + 1}",
            f"{prefix.lower()}_{index + 1}",
            parent,
            semantic,
            material,
            mesh,
        )


def _annulus_y(inner: float, outer: float, height: float, *, sections: int = 72) -> trimesh.Trimesh:
    mesh = trimesh.creation.annulus(r_min=inner, r_max=outer, height=height, sections=sections)
    mesh.apply_transform(rotation_x(math.pi / 2))
    return mesh


def _helical_spring(start: np.ndarray, end: np.ndarray, *, radius: float, turns: int = 12) -> trimesh.Trimesh:
    axis = end - start
    length = float(np.linalg.norm(axis))
    direction = axis / max(length, 1e-9)
    helper = np.array([0.0, 0.0, 1.0]) if abs(direction[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    side = np.cross(direction, helper)
    side /= max(float(np.linalg.norm(side)), 1e-9)
    up = np.cross(side, direction)
    t = np.linspace(0.0, 1.0, turns * 18 + 1)
    angle = t * turns * math.tau
    points = (
        start[None, :]
        + t[:, None] * axis[None, :]
        + radius * np.cos(angle)[:, None] * side[None, :]
        + radius * np.sin(angle)[:, None] * up[None, :]
    )
    return tube_along(points, radius=max(0.008, radius * 0.20), sections=12)


def _add_knob(
    builder: GrammarAssetBuilder,
    *,
    parent: str,
    prefix: str,
    center: Iterable[float],
    radius: float,
    axis: str = "y",
    material: str = "MoldedBlack",
) -> None:
    center = np.asarray(center, dtype=float)
    body = (
        cylinder_y(radius, radius * 0.54, sections=64)
        if axis == "y"
        else cylinder_z(radius, radius * 0.54, sections=64)
    )
    builder.add_part(
        f"{prefix}Body",
        f"{prefix.lower()}_body",
        parent,
        "interface.control_knob",
        material,
        body,
        translation(center),
    )
    ring = torus_y(radius * 0.82, radius * 0.10, 64, 12)
    if axis == "z":
        ring.apply_transform(rotation_x(math.pi / 2))
    builder.add_part(
        f"{prefix}Grip",
        f"{prefix.lower()}_grip",
        parent,
        "interface.control_grip",
        "DarkRubber",
        ring,
        translation(center),
    )
    marker = rounded_box((radius * 0.13, radius * 0.18, radius * 0.78), radius=radius * 0.04, segments=3)
    builder.add_part(
        f"{prefix}Marker",
        f"{prefix.lower()}_marker",
        parent,
        "interface.control_marker",
        "SignalOrange",
        marker,
        translation(center + [0, radius * 0.30, 0]),
    )


def _add_label_plate(
    builder: GrammarAssetBuilder,
    *,
    parent: str,
    prefix: str,
    center: Iterable[float],
    size: tuple[float, float, float],
    material: str = "WarmAluminum",
) -> None:
    center = np.asarray(center, dtype=float)
    plate = rounded_box(size, radius=min(size) * 0.18, segments=4)
    builder.add_part(
        f"{prefix}Plate",
        f"{prefix.lower()}_plate",
        parent,
        "detail.identification_plate",
        material,
        plate,
        translation(center),
    )
    points = [center + [-size[0] * 0.38, 0, 0], center + [size[0] * 0.38, 0, 0]]
    RepetitionGrammar.fasteners(
        builder,
        parent=parent,
        prefix=prefix,
        points=points,
        radius=min(size) * 0.10,
        axis="z",
    )


def _add_vent_bank(
    builder: GrammarAssetBuilder,
    *,
    parent: str,
    prefix: str,
    center: Iterable[float],
    count: int,
    spacing: float,
    size: tuple[float, float, float],
    material: str = "MoldedBlack",
) -> None:
    center = np.asarray(center, dtype=float)
    builder.op(
        "detail.vent_bank",
        prefix,
        "Add repeated ventilation or relief slots as close-view manufacturing detail.",
        {"count": count, "spacing": spacing},
    )
    for index in range(count):
        slot = rounded_box(size, radius=min(size) * 0.28, segments=3)
        position = center + [(index - (count - 1) / 2.0) * spacing, 0, 0]
        builder.add_part(
            f"{prefix}Slot{index + 1}",
            f"{prefix.lower()}_slot_{index + 1}",
            parent,
            "detail.vent_slot",
            material,
            slot,
            translation(position),
        )


def _stability(base_radius: float, reach: float, end_mass: float = 0.95) -> dict[str, float | bool]:
    base_mass = max(4.1, base_radius * 5.0)
    arm_mass = 0.95 + reach * 0.25
    com = (arm_mass * reach * 0.46 + end_mass * reach) / (base_mass + arm_mass + end_mass)
    margin = base_radius - com
    return {
        "support_radius": round(base_radius, 4),
        "center_of_mass_x": round(com, 4),
        "tipping_margin": round(margin, 4),
        "stable": bool(margin >= 0.12),
    }
