from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import trimesh

from objectforge.geometry import cylinder_y, cylinder_z, frustum_shell, normalize, ring_gear_y, rounded_box, rotation_matrix_from_to, rotation_x, rotation_y, torus_y, translation, tube_along
from .core import Articulation, GrammarAssetBuilder


class SupportGrammar:
    @staticmethod
    def weighted_base(builder: GrammarAssetBuilder, *, radius: float, height: float, material: str, layered: bool = True, feet: int = 4) -> None:
        builder.op("support.weighted_base", "support", "Create a stable weighted contact body.", {"radius": radius, "height": height, "layers": 3 if layered else 1, "feet": feet})
        builder.add_part("BaseLower", "base_lower", builder.root_name, "support.base", material, cylinder_y(radius, height * 0.58, sections=96), translation([0, height * 0.29, 0]), {"shape": "cylinder", "radius": radius, "height": height})
        if layered:
            builder.add_part("BaseUpper", "base_upper", builder.root_name, "support.base", material, cylinder_y(radius * 0.90, height * 0.33, sections=96), translation([0, height * 0.68, 0]))
            builder.add_part("BaseFillet", "base_fillet", builder.root_name, "support.edge_detail", "WarmAluminum", torus_y(radius * 0.88, max(0.018, height * 0.08), 72, 12), translation([0, height * 0.52, 0]))
        builder.add_part("BaseUnderside", "base_underside", builder.root_name, "support.underside", "MoldedBlack", cylinder_y(radius * 0.82, height * 0.13, sections=72), translation([0, height * 0.065, 0]))
        for i in range(feet):
            angle = 2 * math.pi * i / feet + math.pi / 4
            builder.add_part(f"RubberFoot{i+1}", f"rubber_foot_{i+1}", builder.root_name, "support.foot", "DarkRubber", cylinder_y(radius * 0.11, height * 0.11, sections=28), translation([radius * 0.64 * math.cos(angle), height * 0.045, radius * 0.64 * math.sin(angle)]))
        builder.add_body(body_id="base", node=builder.root_name, body_type="static", mass=max(2.4, radius * 3.8), collision={"shape": "cylinder", "radius": radius, "height": height}, friction=0.74)

    @staticmethod
    def four_leg_frame(builder: GrammarAssetBuilder, *, top_size: tuple[float, float], height: float, leg_section: float, material: str, inset: float = 0.18) -> list[np.ndarray]:
        width, depth = top_size
        positions = [np.array([sx * (width / 2 - inset), height / 2, sz * (depth / 2 - inset)]) for sx in (-1, 1) for sz in (-1, 1)]
        builder.op("support.four_leg_frame", "support", "Create four load-bearing supports and a continuous apron.", {"width": width, "depth": depth, "height": height, "leg_section": leg_section})
        for index, position in enumerate(positions):
            builder.add_part(f"Leg{index+1}", f"leg_{index+1}", builder.root_name, "support.leg", material, rounded_box((leg_section, height, leg_section), radius=leg_section * 0.18, segments=5), translation(position), {"shape": "box", "extents": [leg_section, height, leg_section]})
            builder.add_part(f"FootPad{index+1}", f"foot_pad_{index+1}", builder.root_name, "support.foot", "DarkRubber", rounded_box((leg_section * 1.08, 0.055, leg_section * 1.08), radius=0.02, segments=4), translation([position[0], 0.028, position[2]]))
        apron_y = height - 0.14
        for name, extents, pos in [("ApronFront", (width - inset * 1.25, 0.17, leg_section * 0.58), (0, apron_y, depth / 2 - inset)), ("ApronBack", (width - inset * 1.25, 0.17, leg_section * 0.58), (0, apron_y, -depth / 2 + inset)), ("ApronLeft", (leg_section * 0.58, 0.17, depth - inset * 1.25), (-width / 2 + inset, apron_y, 0)), ("ApronRight", (leg_section * 0.58, 0.17, depth - inset * 1.25), (width / 2 - inset, apron_y, 0))]:
            builder.add_part(name, name.lower(), builder.root_name, "joinery.apron", material, rounded_box(extents, radius=0.035, segments=4), translation(pos))
        builder.add_body(body_id="frame", node=builder.root_name, body_type="static", mass=5.2, collision={"shape": "compound_box_frame", "width": width, "depth": depth, "height": height})
        return positions

    @staticmethod
    def pedestal(builder: GrammarAssetBuilder, *, radius: float, height: float, column_radius: float, material: str) -> None:
        builder.op("support.pedestal", "support", "Build a broad base, central column, and reinforced neck.", {"radius": radius, "height": height, "column_radius": column_radius})
        builder.add_part("PedestalBase", "pedestal_base", builder.root_name, "support.base", material, cylinder_y(radius, 0.18, sections=112), translation([0, 0.09, 0]))
        builder.add_part("PedestalUnderside", "pedestal_underside", builder.root_name, "support.underside", "DarkRubber", cylinder_y(radius * 0.82, 0.08, sections=96), translation([0, 0.04, 0]))
        builder.add_part("PedestalColumn", "pedestal_column", builder.root_name, "support.column", material, cylinder_y(column_radius, height - 0.22, sections=80), translation([0, 0.18 + (height - 0.22) / 2, 0]))
        builder.add_part("PedestalNeckRing", "pedestal_neck_ring", builder.root_name, "joinery.collar", "BrushedSteel", torus_y(column_radius * 1.35, 0.055, 72, 12), translation([0, height - 0.06, 0]))
        for i in range(8):
            angle = 2 * math.pi * i / 8
            rib = rounded_box((0.08, 0.20, radius * 0.55), radius=0.025, segments=4)
            rib.apply_transform(rotation_y(-angle))
            rib.apply_translation([0, 0.18, 0])
            builder.add_part(f"BaseRib{i+1}", f"base_rib_{i+1}", builder.root_name, "support.rib", material, rib)
        builder.add_body(body_id="pedestal", node=builder.root_name, body_type="static", mass=6.4, collision={"shape": "compound_pedestal", "radius": radius, "height": height}, friction=0.70)


class ShellGrammar:
    @staticmethod
    def tray(builder: GrammarAssetBuilder, *, parent: str, prefix: str, size: tuple[float, float, float], wall: float, material: str, liner: str | None = None, open_up: bool = True) -> None:
        width, depth, height = size
        builder.op("shell.tray", prefix, "Create a hollow shell with explicit wall thickness and rim.", {"size": list(size), "wall": wall, "open_up": open_up})
        builder.add_part(f"{prefix}Bottom", f"{prefix.lower()}_bottom", parent, f"shell.{prefix.lower()}.bottom", material, rounded_box((width, wall, depth), radius=min(0.11, wall * 1.4), segments=6), translation([0, wall / 2, 0]))
        side_h = max(wall * 2, height - wall)
        for suffix, extents, pos in [("FrontWall", (width, side_h, wall), (0, wall + side_h / 2, depth / 2 - wall / 2)), ("BackWall", (width, side_h, wall), (0, wall + side_h / 2, -depth / 2 + wall / 2)), ("LeftWall", (wall, side_h, depth - 2 * wall), (-width / 2 + wall / 2, wall + side_h / 2, 0)), ("RightWall", (wall, side_h, depth - 2 * wall), (width / 2 - wall / 2, wall + side_h / 2, 0))]:
            builder.add_part(f"{prefix}{suffix}", f"{prefix.lower()}_{suffix.lower()}", parent, f"shell.{prefix.lower()}.wall", material, rounded_box(extents, radius=min(0.055, wall * 0.6), segments=5), translation(pos))
        for suffix, extents, pos in [("FrontRim", (width + wall * 0.34, wall * 0.60, wall * 1.10), (0, height, depth / 2 - wall / 2)), ("BackRim", (width + wall * 0.34, wall * 0.60, wall * 1.10), (0, height, -depth / 2 + wall / 2)), ("LeftRim", (wall * 1.10, wall * 0.60, depth - wall), (-width / 2 + wall / 2, height, 0)), ("RightRim", (wall * 1.10, wall * 0.60, depth - wall), (width / 2 - wall / 2, height, 0))]:
            builder.add_part(f"{prefix}{suffix}", f"{prefix.lower()}_{suffix.lower()}", parent, f"shell.{prefix.lower()}.rim", "DarkRubber" if liner else material, rounded_box(extents, radius=0.025, segments=4), translation(pos))
        if liner:
            builder.add_part(f"{prefix}Liner", f"{prefix.lower()}_liner", parent, f"interior.{prefix.lower()}.liner", liner, rounded_box((width - 2.5 * wall, wall * 0.55, depth - 2.5 * wall), radius=0.08, segments=5), translation([0, wall * 1.25, 0]))

    @staticmethod
    def shade(builder: GrammarAssetBuilder, *, parent: str, prefix: str, axis: np.ndarray, length: float, back_radius: float, front_radius: float, material: str) -> None:
        builder.op("shell.directional_shade", prefix, "Create a hollow directional shade with reflector and rim.", {"length": length, "back_radius": back_radius, "front_radius": front_radius})
        axis = normalize(axis)
        builder.add_part(f"{prefix}Shell", f"{prefix.lower()}_shell", parent, "shade.outer_shell", material, frustum_shell(axis, length, back_radius, front_radius, max(0.035, front_radius * 0.075), sections=80), collision={"shape": "convex_frustum", "length": length, "front_radius": front_radius})
        reflector = frustum_shell(axis, length * 0.86, back_radius * 0.78, front_radius * 0.84, max(0.014, front_radius * 0.025), sections=80)
        reflector.apply_translation(axis * length * 0.08)
        builder.add_part(f"{prefix}Reflector", f"{prefix.lower()}_reflector", parent, "shade.inner_reflector", "ReflectorSilver", reflector)
        rim = torus_y(front_radius, max(0.025, front_radius * 0.055), 80, 12)
        rim.apply_transform(rotation_matrix_from_to([0, 1, 0], axis))
        rim.apply_translation(axis * length)
        builder.add_part(f"{prefix}Rim", f"{prefix.lower()}_rim", parent, "shade.front_rim", "WarmAluminum", rim)


class ArticulationGrammar:
    @staticmethod
    def hinge(builder: GrammarAssetBuilder, *, node: str, parent: str, transform: np.ndarray, hinge_id: str, parent_body: str, child_body: str, radius: float, width: float, material: str, limits: tuple[float, float], axis: tuple[float, float, float] = (0, 0, 1)) -> None:
        builder.add_node(node, parent, transform)
        builder.op("articulation.hinge", node, "Add a retained pivot, housing, pin, and bounded motion contract.", {"hinge_id": hinge_id, "limits_degrees": list(limits), "radius": radius})
        builder.add_part(f"{node}Disc", f"{node.lower()}_disc", node, "joint.housing", material, cylinder_z(radius, width, sections=64))
        builder.add_part(f"{node}Pin", f"{node.lower()}_pin", node, "joint.pin", "BrushedSteel", cylinder_z(radius * 0.35, width * 1.24, sections=44))
        gear = ring_gear_y(radius * 0.78, radius * 0.08, width * 0.38, teeth=20)
        gear.apply_transform(rotation_x(math.pi / 2))
        builder.add_part(f"{node}Knurl", f"{node.lower()}_knurl", node, "joint.fastener", "WarmAluminum", gear, translation([0, 0, width * 0.58]))
        builder.add_articulation(Articulation(hinge_id, node, parent_body, child_body, axis, limits))


class RepetitionGrammar:
    @staticmethod
    def fasteners(builder: GrammarAssetBuilder, *, parent: str, prefix: str, points: Iterable[Iterable[float]], radius: float = 0.045, material: str = "BrushedSteel", axis: str = "y") -> None:
        points = [np.asarray(point, dtype=float) for point in points]
        builder.op("repetition.fasteners", prefix, "Add semantic repeated fasteners at declared attachment points.", {"count": len(points), "radius": radius})
        for index, point in enumerate(points):
            mesh = cylinder_y(radius, radius * 0.38, sections=32) if axis == "y" else cylinder_z(radius, radius * 0.38, sections=32)
            builder.add_part(f"{prefix}Fastener{index+1}", f"{prefix.lower()}_fastener_{index+1}", parent, "detail.fastener", material, mesh, translation(point))

    @staticmethod
    def ribs(builder: GrammarAssetBuilder, *, parent: str, prefix: str, count: int, width: float, depth: float, start_x: float, spacing: float, y: float, z: float, material: str) -> None:
        builder.op("repetition.ribs", prefix, "Add repeated stiffening and close-view surface rhythm.", {"count": count, "spacing": spacing})
        for i in range(count):
            builder.add_part(f"{prefix}Rib{i+1}", f"{prefix.lower()}_rib_{i+1}", parent, "detail.rib", material, rounded_box((width, depth, 0.045), radius=0.015, segments=3), translation([start_x + i * spacing, y, z]))


class JoineryGrammar:
    @staticmethod
    def bracket(builder: GrammarAssetBuilder, *, parent: str, prefix: str, center: Iterable[float], size: tuple[float, float, float], material: str) -> None:
        center = np.asarray(center, dtype=float)
        builder.op("joinery.bracket", prefix, "Resolve a structural connection with a shaped bracket and fasteners.", {"size": list(size), "center": center.tolist()})
        builder.add_part(f"{prefix}Bracket", f"{prefix.lower()}_bracket", parent, "joinery.bracket", material, rounded_box(size, radius=min(size) * 0.18, segments=4), translation(center))
        RepetitionGrammar.fasteners(builder, parent=parent, prefix=prefix, points=[center + [-size[0] * 0.28, 0, 0], center + [size[0] * 0.28, 0, 0]], radius=min(size) * 0.13, axis="z")

    @staticmethod
    def latch(builder: GrammarAssetBuilder, *, parent: str, prefix: str, center: Iterable[float], material: str) -> None:
        center = np.asarray(center, dtype=float)
        builder.op("joinery.latch", prefix, "Add a two-stage closure with catch and lever.", {"center": center.tolist()})
        builder.add_part(f"{prefix}Catch", f"{prefix.lower()}_catch", parent, "closure.catch", material, rounded_box((0.28, 0.09, 0.16), radius=0.035, segments=4), translation(center))
        builder.add_part(f"{prefix}Lever", f"{prefix.lower()}_lever", parent, "closure.lever", "BrushedSteel", rounded_box((0.18, 0.055, 0.24), radius=0.028, segments=4), translation(center + [0, 0.085, 0.025]))
        builder.add_part(f"{prefix}Pin", f"{prefix.lower()}_pin", parent, "closure.pin", "BrushedSteel", cylinder_z(0.035, 0.20, sections=32), translation(center + [0, 0.05, 0]))

    @staticmethod
    def handle(builder: GrammarAssetBuilder, *, parent: str, prefix: str, center: Iterable[float], width: float, height: float, material: str) -> None:
        center = np.asarray(center, dtype=float)
        builder.op("joinery.handle", prefix, "Add a graspable handle with separate mounts and clearance.", {"width": width, "height": height})
        points = np.array([center + [-width / 2, 0, 0], center + [-width / 2, height * 0.65, 0], center + [-width * 0.28, height, 0], center + [width * 0.28, height, 0], center + [width / 2, height * 0.65, 0], center + [width / 2, 0, 0]])
        builder.add_part(f"{prefix}Grip", f"{prefix.lower()}_grip", parent, "handle.grip", material, tube_along(points, radius=0.055, sections=18))
        for i, x in enumerate((-width / 2, width / 2)):
            builder.add_part(f"{prefix}Mount{i+1}", f"{prefix.lower()}_mount_{i+1}", parent, "handle.mount", "BrushedSteel", rounded_box((0.17, 0.09, 0.22), radius=0.035, segments=4), translation(center + [x, 0, 0]))


class DetailGrammar:
    @staticmethod
    def edge_band(builder: GrammarAssetBuilder, *, parent: str, prefix: str, size: tuple[float, float], y: float, thickness: float, material: str) -> None:
        width, depth = size
        builder.op("detail.edge_band", prefix, "Add a visible manufactured edge treatment.", {"width": width, "depth": depth, "thickness": thickness})
        for suffix, extents, pos in [("Front", (width, thickness, thickness), (0, y, depth / 2)), ("Back", (width, thickness, thickness), (0, y, -depth / 2)), ("Left", (thickness, thickness, depth), (-width / 2, y, 0)), ("Right", (thickness, thickness, depth), (width / 2, y, 0))]:
            builder.add_part(f"{prefix}{suffix}", f"{prefix.lower()}_{suffix.lower()}", parent, "detail.edge_band", material, rounded_box(extents, radius=thickness * 0.28, segments=4), translation(pos))
