from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image
import trimesh
from trimesh.visual.material import PBRMaterial

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v if n < 1e-12 else v / n


def rotation_matrix_from_to(source: Iterable[float], target: Iterable[float]) -> np.ndarray:
    a = normalize(np.asarray(source, dtype=float))
    b = normalize(np.asarray(target, dtype=float))
    cross = np.cross(a, b)
    dot = float(np.clip(np.dot(a, b), -1.0, 1.0))
    if np.linalg.norm(cross) < 1e-10:
        if dot > 0:
            return np.eye(4)
        axis = normalize(np.cross(a, np.array([1.0, 0.0, 0.0]) if abs(a[0]) < 0.8 else np.array([0.0, 1.0, 0.0])))
        return trimesh.transformations.rotation_matrix(math.pi, axis)
    axis = normalize(cross)
    angle = math.acos(dot)
    return trimesh.transformations.rotation_matrix(angle, axis)


def compose(*matrices: np.ndarray) -> np.ndarray:
    out = np.eye(4)
    for matrix in matrices:
        out = out @ matrix
    return out


def translation(v: Iterable[float]) -> np.ndarray:
    return trimesh.transformations.translation_matrix(np.asarray(v, dtype=float))


def scale(v: Iterable[float]) -> np.ndarray:
    return trimesh.transformations.scale_and_translate(scale=np.asarray(v, dtype=float))


def rotation_z(angle: float) -> np.ndarray:
    return trimesh.transformations.rotation_matrix(angle, [0, 0, 1])


def rotation_x(angle: float) -> np.ndarray:
    return trimesh.transformations.rotation_matrix(angle, [1, 0, 0])


def rotation_y(angle: float) -> np.ndarray:
    return trimesh.transformations.rotation_matrix(angle, [0, 1, 0])


@dataclass
class MaterialSpec:
    name: str
    base_color: tuple[int, int, int]
    metallic: float
    roughness: float
    emissive: tuple[float, float, float] = (0.0, 0.0, 0.0)
    clearcoat: float = 0.0
    texture_kind: str = "solid"


@dataclass
class BuildOperation:
    sequence: int
    operator: str
    target: str
    purpose: str
    parameters: dict[str, Any]
    status: str = "accepted"
    metrics_before: dict[str, Any] = field(default_factory=dict)
    metrics_after: dict[str, Any] = field(default_factory=dict)
    recovery_of: int | None = None


@dataclass
class PartRecord:
    node_name: str
    geometry_name: str
    parent: str
    semantic_part: str
    material: str
    geometry: trimesh.Trimesh
    local_transform: np.ndarray
    collision: dict[str, Any] | None = None


def cylinder_y(radius: float, height: float, sections: int = 64) -> trimesh.Trimesh:
    mesh = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    mesh.apply_transform(rotation_x(math.pi / 2.0))
    return mesh


def cylinder_z(radius: float, height: float, sections: int = 64) -> trimesh.Trimesh:
    return trimesh.creation.cylinder(radius=radius, height=height, sections=sections)


def cylinder_between(start: Iterable[float], end: Iterable[float], radius: float, sections: int = 32) -> trimesh.Trimesh:
    start = np.asarray(start, dtype=float)
    end = np.asarray(end, dtype=float)
    vector = end - start
    length = float(np.linalg.norm(vector))
    mesh = trimesh.creation.cylinder(radius=radius, height=length, sections=sections)
    mesh.apply_transform(rotation_matrix_from_to([0, 0, 1], vector))
    mesh.apply_translation((start + end) / 2.0)
    return mesh


def capsule_between(start: Iterable[float], end: Iterable[float], radius: float, sections: int = 32) -> list[trimesh.Trimesh]:
    start = np.asarray(start, dtype=float)
    end = np.asarray(end, dtype=float)
    body = cylinder_between(start, end, radius, sections)
    cap_a = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    cap_a.apply_translation(start)
    cap_b = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    cap_b.apply_translation(end)
    return [body, cap_a, cap_b]


def rounded_rectangle_points(width: float, height: float, radius: float, segments: int = 6) -> np.ndarray:
    radius = min(radius, width / 2.0, height / 2.0)
    centers = [
        (width / 2.0 - radius, height / 2.0 - radius, 0.0),
        (-width / 2.0 + radius, height / 2.0 - radius, math.pi / 2.0),
        (-width / 2.0 + radius, -height / 2.0 + radius, math.pi),
        (width / 2.0 - radius, -height / 2.0 + radius, 3.0 * math.pi / 2.0),
    ]
    points: list[tuple[float, float]] = []
    for cx, cy, start in centers:
        for i in range(segments + 1):
            angle = start + (math.pi / 2.0) * i / segments
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return np.asarray(points, dtype=float)


def extrude_polygon_fan(points: np.ndarray, depth: float) -> trimesh.Trimesh:
    points = np.asarray(points, dtype=float)
    count = len(points)
    z0, z1 = -depth / 2.0, depth / 2.0
    verts = np.vstack([
        np.column_stack([points, np.full(count, z0)]),
        np.column_stack([points, np.full(count, z1)]),
        [[0.0, 0.0, z0], [0.0, 0.0, z1]],
    ])
    bottom_center = 2 * count
    top_center = 2 * count + 1
    faces: list[list[int]] = []
    for i in range(count):
        j = (i + 1) % count
        faces.append([bottom_center, j, i])
        faces.append([top_center, count + i, count + j])
        faces.append([i, j, count + j])
        faces.append([i, count + j, count + i])
    return trimesh.Trimesh(vertices=verts, faces=np.asarray(faces), process=True)


def rounded_box(extents: tuple[float, float, float], radius: float = 0.08, segments: int = 7) -> trimesh.Trimesh:
    points = rounded_rectangle_points(extents[0], extents[1], radius, segments)
    return extrude_polygon_fan(points, extents[2])


def torus_y(major_radius: float, minor_radius: float, major_sections: int = 72, minor_sections: int = 16) -> trimesh.Trimesh:
    vertices = []
    faces = []
    for i in range(major_sections):
        theta = 2 * math.pi * i / major_sections
        for j in range(minor_sections):
            phi = 2 * math.pi * j / minor_sections
            r = major_radius + minor_radius * math.cos(phi)
            x = r * math.cos(theta)
            z = r * math.sin(theta)
            y = minor_radius * math.sin(phi)
            vertices.append([x, y, z])
    for i in range(major_sections):
        ni = (i + 1) % major_sections
        for j in range(minor_sections):
            nj = (j + 1) % minor_sections
            a = i * minor_sections + j
            b = ni * minor_sections + j
            c = ni * minor_sections + nj
            d = i * minor_sections + nj
            faces.extend([[a, b, c], [a, c, d]])
    return trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=True)


def frustum_shell(axis: Iterable[float], length: float, back_radius: float, front_radius: float, thickness: float,
                  sections: int = 96) -> trimesh.Trimesh:
    axis = normalize(np.asarray(axis, dtype=float))
    helper = np.array([0.0, 1.0, 0.0]) if abs(axis[1]) < 0.9 else np.array([0.0, 0.0, 1.0])
    u = normalize(np.cross(axis, helper))
    v = normalize(np.cross(axis, u))
    center_back = np.zeros(3)
    center_front = axis * length
    inner_back = max(0.02, back_radius - thickness)
    inner_front = max(inner_back + 0.01, front_radius - thickness)
    vertices: list[np.ndarray] = []
    for center, radius in [
        (center_back, back_radius),
        (center_front, front_radius),
        (center_back + axis * thickness, inner_back),
        (center_front - axis * thickness, inner_front),
    ]:
        for i in range(sections):
            angle = 2 * math.pi * i / sections
            vertices.append(center + radius * (math.cos(angle) * u + math.sin(angle) * v))
    faces: list[list[int]] = []
    rings = [0, sections, 2 * sections, 3 * sections]
    for i in range(sections):
        j = (i + 1) % sections
        faces.extend([[rings[0] + i, rings[1] + i, rings[1] + j], [rings[0] + i, rings[1] + j, rings[0] + j]])
        faces.extend([[rings[2] + i, rings[3] + j, rings[3] + i], [rings[2] + i, rings[2] + j, rings[3] + j]])
        faces.extend([[rings[0] + i, rings[0] + j, rings[2] + j], [rings[0] + i, rings[2] + j, rings[2] + i]])
        faces.extend([[rings[1] + i, rings[3] + i, rings[3] + j], [rings[1] + i, rings[3] + j, rings[1] + j]])
    return trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=True)


def tube_along(points: np.ndarray, radius: float, sections: int = 18) -> trimesh.Trimesh:
    points = np.asarray(points, dtype=float)
    tangents = np.zeros_like(points)
    tangents[0] = normalize(points[1] - points[0])
    tangents[-1] = normalize(points[-1] - points[-2])
    for i in range(1, len(points) - 1):
        tangents[i] = normalize(points[i + 1] - points[i - 1])
    frames: list[tuple[np.ndarray, np.ndarray]] = []
    normal = normalize(np.cross(tangents[0], np.array([0, 0, 1]) if abs(tangents[0][2]) < 0.9 else np.array([0, 1, 0])))
    binormal = normalize(np.cross(tangents[0], normal))
    frames.append((normal, binormal))
    for i in range(1, len(points)):
        prev_t = tangents[i - 1]
        t = tangents[i]
        axis = np.cross(prev_t, t)
        if np.linalg.norm(axis) > 1e-8:
            angle = math.acos(float(np.clip(np.dot(prev_t, t), -1.0, 1.0)))
            rot = trimesh.transformations.rotation_matrix(angle, normalize(axis))[:3, :3]
            normal = normalize(rot @ normal)
        normal = normalize(normal - t * np.dot(normal, t))
        binormal = normalize(np.cross(t, normal))
        frames.append((normal, binormal))
    vertices: list[np.ndarray] = []
    for point, (n, b) in zip(points, frames):
        for j in range(sections):
            angle = 2 * math.pi * j / sections
            vertices.append(point + radius * (math.cos(angle) * n + math.sin(angle) * b))
    faces: list[list[int]] = []
    for i in range(len(points) - 1):
        for j in range(sections):
            nj = (j + 1) % sections
            a = i * sections + j
            b = (i + 1) * sections + j
            c = (i + 1) * sections + nj
            d = i * sections + nj
            faces.extend([[a, b, c], [a, c, d]])
    return trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=True)


def plane_xz(width: float, depth: float) -> trimesh.Trimesh:
    vertices = np.array([[-width/2, 0, -depth/2], [width/2, 0, -depth/2], [width/2, 0, depth/2], [-width/2, 0, depth/2]], dtype=float)
    faces = np.array([[0, 2, 1], [0, 3, 2]], dtype=int)
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=True)


def plane_xy(width: float, height: float) -> trimesh.Trimesh:
    vertices = np.array([[-width/2, -height/2, 0], [width/2, -height/2, 0], [width/2, height/2, 0], [-width/2, height/2, 0]], dtype=float)
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=int)
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=True)


def ring_gear_y(radius: float, thickness: float, depth: float, teeth: int = 24) -> trimesh.Trimesh:
    parts = [torus_y(radius, thickness, major_sections=teeth * 2, minor_sections=10)]
    for i in range(teeth):
        angle = 2 * math.pi * i / teeth
        box = rounded_box((thickness * 1.5, depth, thickness * 0.8), radius=thickness * 0.18, segments=3)
        box.apply_transform(rotation_y(-angle))
        box.apply_translation([(radius + thickness * 0.75) * math.cos(angle), 0.0, (radius + thickness * 0.75) * math.sin(angle)])
        parts.append(box)
    return trimesh.util.concatenate(parts)


def procedural_texture(kind: str, base: tuple[int, int, int], size: int = 256, seed: int = 7) -> tuple[Image.Image, Image.Image]:
    rng = np.random.default_rng(seed + sum(base) + len(kind))
    yy, xx = np.mgrid[0:size, 0:size]
    color = np.zeros((size, size, 3), dtype=np.float32)
    color[:] = np.asarray(base, dtype=float)
    if kind == "powder_coat":
        noise = rng.normal(0, 4.0, (size, size))
        speckle = rng.random((size, size)) > 0.992
        color += noise[..., None]
        color[speckle] += np.array([14, 14, 14])
        roughness = np.clip(150 + rng.normal(0, 8, (size, size)), 0, 255)
        metallic = np.full((size, size), 24)
    elif kind == "brushed_metal":
        brush = 9 * np.sin(xx * 0.42) + 4 * np.sin(xx * 1.13) + rng.normal(0, 2, (size, size))
        color += brush[..., None]
        roughness = np.clip(58 + 18 * (0.5 + 0.5 * np.sin(xx * 0.2)), 0, 255)
        metallic = np.full((size, size), 245)
    elif kind == "rubber":
        noise = rng.normal(0, 2.8, (size, size))
        color += noise[..., None]
        roughness = np.full((size, size), 225)
        metallic = np.zeros((size, size))
    elif kind == "reflector":
        radial = np.sqrt((xx - size / 2) ** 2 + (yy - size / 2) ** 2)
        color += (10 * np.sin(radial * 0.45))[..., None]
        roughness = np.clip(38 + 12 * np.sin(radial * 0.3), 0, 255)
        metallic = np.full((size, size), 250)
    elif kind == "plastic":
        noise = rng.normal(0, 1.5, (size, size))
        color += noise[..., None]
        roughness = np.full((size, size), 105)
        metallic = np.zeros((size, size))
    else:
        roughness = np.full((size, size), 128)
        metallic = np.zeros((size, size))
    color = np.uint8(np.clip(color, 0, 255))
    packed = np.zeros((size, size, 3), dtype=np.uint8)
    packed[..., 0] = 255
    packed[..., 1] = np.uint8(roughness)
    packed[..., 2] = np.uint8(metallic)
    return Image.fromarray(color, mode="RGB"), Image.fromarray(packed, mode="RGB")


def build_materials() -> dict[str, tuple[MaterialSpec, PBRMaterial]]:
    specs = [
        MaterialSpec("GraphitePowderCoat", (36, 48, 58), 0.08, 0.34, clearcoat=0.16, texture_kind="powder_coat"),
        MaterialSpec("WarmAluminum", (176, 150, 112), 0.94, 0.23, clearcoat=0.05, texture_kind="brushed_metal"),
        MaterialSpec("DarkRubber", (24, 27, 30), 0.0, 0.88, texture_kind="rubber"),
        MaterialSpec("ReflectorSilver", (214, 220, 225), 1.0, 0.14, texture_kind="reflector"),
        MaterialSpec("SwitchPlastic", (160, 58, 39), 0.0, 0.35, clearcoat=0.2, texture_kind="plastic"),
        MaterialSpec("CableBlack", (15, 17, 20), 0.0, 0.74, texture_kind="rubber"),
        MaterialSpec("WarmEmitter", (255, 230, 180), 0.0, 0.18, emissive=(1.0, 0.65, 0.28), texture_kind="solid"),
        MaterialSpec("StageMatte", (73, 84, 98), 0.0, 0.86, texture_kind="powder_coat"),
        MaterialSpec("StageFloor", (43, 48, 55), 0.0, 0.62, texture_kind="powder_coat"),
    ]
    out: dict[str, tuple[MaterialSpec, PBRMaterial]] = {}
    for i, spec in enumerate(specs):
        color_tex, mr_tex = procedural_texture(spec.texture_kind, spec.base_color, seed=17 + i)
        material = PBRMaterial(
            name=spec.name,
            baseColorFactor=[1, 1, 1, 1],
            baseColorTexture=color_tex,
            metallicFactor=1.0,
            roughnessFactor=1.0,
            metallicRoughnessTexture=mr_tex,
            emissiveFactor=list(spec.emissive),
            doubleSided=False,
        )
        out[spec.name] = (spec, material)
    return out


def planar_uv(mesh: trimesh.Trimesh) -> np.ndarray:
    vertices = np.asarray(mesh.vertices)
    extents = np.ptp(vertices, axis=0)
    axes = np.argsort(extents)[-2:]
    uv = vertices[:, axes].copy()
    for i in range(2):
        span = np.ptp(uv[:, i])
        uv[:, i] = 0.0 if span < 1e-9 else (uv[:, i] - uv[:, i].min()) / span
    scale_factor = max(1.0, float(np.max(extents)) * 1.8)
    return uv * scale_factor


def apply_material(mesh: trimesh.Trimesh, material: PBRMaterial) -> trimesh.Trimesh:
    mesh = mesh.copy()
    mesh.remove_unreferenced_vertices()
    mesh.visual = trimesh.visual.texture.TextureVisuals(uv=planar_uv(mesh), material=material)
    return mesh
