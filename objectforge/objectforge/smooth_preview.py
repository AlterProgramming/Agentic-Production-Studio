from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Mapping

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import trimesh


PoseMap = Mapping[str, tuple[str, float]]


def _axis_vector(axis: str) -> np.ndarray:
    vectors = {
        "x": np.array([1.0, 0.0, 0.0]),
        "y": np.array([0.0, 1.0, 0.0]),
        "z": np.array([0.0, 0.0, 1.0]),
    }
    try:
        return vectors[axis.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported pose axis: {axis!r}") from exc


def _apply_pose(scene: trimesh.Scene, pose: PoseMap | None) -> None:
    if not pose:
        return
    nodes = set(scene.graph.nodes)
    for requested_node, (axis, degrees) in pose.items():
        matches = [node for node in nodes if node == requested_node or str(node).endswith(requested_node)]
        if not matches:
            continue
        for node in matches:
            transform, geometry = scene.graph[node]
            pivot = np.asarray(transform[:3, 3], dtype=float)
            rotation = trimesh.transformations.rotation_matrix(
                math.radians(float(degrees)), _axis_vector(axis), point=pivot
            )
            update = {"frame_to": node, "matrix": rotation @ transform}
            if geometry is not None:
                update["geometry"] = geometry
            scene.graph.update(**update)


def _normalize_scene_graph(scene: trimesh.Scene) -> None:
    """Remove null geometry references that break Trimesh graph hashing."""
    transforms = scene.graph.transforms
    for records in (transforms.edge_data, transforms.node_data):
        for record in records.values():
            if record.get("geometry") is None:
                record.pop("geometry", None)


def _scene_meshes(path: Path, pose: PoseMap | None) -> list[trimesh.Trimesh]:
    loaded = trimesh.load(path, force="scene", process=False)
    scene = loaded if isinstance(loaded, trimesh.Scene) else trimesh.Scene(loaded)
    _normalize_scene_graph(scene)
    _apply_pose(scene, pose)
    meshes = [mesh for mesh in scene.dump(concatenate=False) if isinstance(mesh, trimesh.Trimesh)]
    if not meshes:
        raise ValueError(f"No renderable mesh geometry in {path}")
    return meshes


def _camera_basis(elev: float, azim: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    elevation = math.radians(float(elev))
    azimuth = math.radians(float(azim))
    camera_direction = np.array(
        [math.cos(elevation) * math.cos(azimuth), math.sin(elevation), math.cos(elevation) * math.sin(azimuth)],
        dtype=float,
    )
    camera_direction /= np.linalg.norm(camera_direction)
    forward = -camera_direction
    world_up = np.array([0.0, 1.0, 0.0], dtype=float)
    right = np.cross(forward, world_up)
    if np.linalg.norm(right) < 1e-8:
        world_up = np.array([0.0, 0.0, 1.0], dtype=float)
        right = np.cross(forward, world_up)
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    up /= np.linalg.norm(up)
    return right, up, camera_direction


def _sample_faces(mesh: trimesh.Trimesh, limit: int) -> np.ndarray:
    count = len(mesh.faces)
    if count <= limit:
        return np.arange(count, dtype=np.int64)
    areas = np.asarray(mesh.area_faces, dtype=float)
    if not np.isfinite(areas).all() or areas.sum() <= 0:
        return np.linspace(0, count - 1, limit, dtype=np.int64)
    cdf = np.cumsum(areas)
    targets = (np.arange(limit, dtype=float) + 0.5) * (cdf[-1] / limit)
    return np.searchsorted(cdf, targets).astype(np.int64)


def _face_colors(mesh: trimesh.Trimesh, face_ids: np.ndarray) -> np.ndarray:
    try:
        colors = np.asarray(mesh.visual.face_colors, dtype=np.uint8)
        if len(colors) == len(mesh.faces):
            return colors[face_ids, :3]
    except Exception:
        pass
    return np.tile(np.array([[176, 183, 191]], dtype=np.uint8), (len(face_ids), 1))


def _font(size: int) -> ImageFont.ImageFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_glb_smooth(
    input_path: Path,
    output_path: Path,
    *,
    elev: float = 24.0,
    azim: float = -38.0,
    title: str | None = None,
    pose: PoseMap | None = None,
    size: tuple[int, int] = (1180, 760),
    supersample: int = 1,
    max_faces: int = 60000,
) -> Path:
    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    if supersample < 1:
        raise ValueError("supersample must be at least 1")

    width, height = int(size[0]) * supersample, int(size[1]) * supersample
    title_height = (70 if title else 28) * supersample
    canvas = np.full((height, width, 3), 247, dtype=np.uint8)
    right, up, camera_direction = _camera_basis(elev, azim)

    meshes = _scene_meshes(input_path, pose)
    total_faces = sum(len(mesh.faces) for mesh in meshes)
    remaining = max_faces
    packets: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
    projected_all: list[np.ndarray] = []

    for mesh in meshes:
        if len(mesh.faces) == 0:
            continue
        proportional = max(256, int(max_faces * len(mesh.faces) / max(total_faces, 1)))
        per_mesh_limit = min(len(mesh.faces), proportional, max(remaining, 256))
        face_ids = _sample_faces(mesh, per_mesh_limit)
        remaining = max(0, remaining - len(face_ids))
        triangles = np.asarray(mesh.vertices, dtype=float)[np.asarray(mesh.faces, dtype=np.int64)[face_ids]]
        flat = triangles.reshape(-1, 3)
        projected = np.column_stack((flat @ right, flat @ up)).reshape(-1, 3, 2)
        depth = triangles.mean(axis=1) @ camera_direction
        normals = np.asarray(mesh.face_normals, dtype=float)[face_ids]
        colors = _face_colors(mesh, face_ids)
        packets.append((projected, depth, normals, colors))
        projected_all.append(projected.reshape(-1, 2))

    if not projected_all:
        raise ValueError(f"No non-empty mesh faces in {input_path}")

    all_points = np.concatenate(projected_all, axis=0)
    minimum = all_points.min(axis=0)
    maximum = all_points.max(axis=0)
    span = np.maximum(maximum - minimum, 1e-6)
    scale = min(width * 0.88 / span[0], (height - title_height) * 0.88 / span[1])
    center = (minimum + maximum) * 0.5
    screen_center = np.array([width * 0.5, title_height + (height - title_height) * 0.50])

    faces: list[tuple[float, np.ndarray, np.ndarray]] = []
    light = camera_direction + np.array([0.15, 0.75, 0.05])
    light /= np.linalg.norm(light)
    for projected, depth, normals, base_colors in packets:
        screen = (projected - center) * scale
        screen[..., 0] += screen_center[0]
        screen[..., 1] = screen_center[1] - screen[..., 1]
        diffuse = np.clip(np.abs(normals @ light), 0.0, 1.0)
        intensity = 0.48 + 0.52 * diffuse
        shaded = np.clip(base_colors.astype(float) * intensity[:, None], 18, 245).astype(np.uint8)
        for z, triangle, color in zip(depth, screen, shaded, strict=True):
            faces.append((float(z), np.rint(triangle).astype(np.int32), color))

    faces.sort(key=lambda item: item[0])
    for _, triangle, color in faces:
        cv2.fillConvexPoly(
            canvas,
            triangle,
            color=tuple(int(channel) for channel in color),
            lineType=cv2.LINE_AA,
        )

    image = Image.fromarray(canvas, mode="RGB")
    draw = ImageDraw.Draw(image)
    if title:
        draw.text(
            (32 * supersample, 22 * supersample),
            title,
            fill=(27, 31, 36),
            font=_font(24 * supersample),
        )
    if supersample > 1:
        image = image.resize(size, Image.Resampling.LANCZOS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", optimize=True)
    return output_path


def contact_sheet(
    items: Iterable[tuple[Path, str]],
    output_path: Path,
    *,
    columns: int = 3,
    padding: int = 18,
) -> Path:
    entries = [(Path(path), label) for path, label in items]
    if not entries:
        raise ValueError("contact_sheet requires at least one image")
    if columns < 1:
        raise ValueError("columns must be at least 1")

    images = [Image.open(path).convert("RGB") for path, _ in entries]
    cell_width = max(image.width for image in images)
    image_height = max(image.height for image in images)
    label_height = 42
    rows = math.ceil(len(entries) / columns)
    sheet = Image.new(
        "RGB",
        (
            columns * cell_width + (columns + 1) * padding,
            rows * (image_height + label_height) + (rows + 1) * padding,
        ),
        (242, 244, 247),
    )
    draw = ImageDraw.Draw(sheet)
    font = _font(18)
    for index, ((_, label), image) in enumerate(zip(entries, images, strict=True)):
        row, column = divmod(index, columns)
        x = padding + column * (cell_width + padding)
        y = padding + row * (image_height + label_height + padding)
        image_x = x + (cell_width - image.width) // 2
        image_y = y + (image_height - image.height) // 2
        sheet.paste(image, (image_x, image_y))
        draw.text((x + 8, y + image_height + 10), label, fill=(35, 39, 44), font=font)
    for image in images:
        image.close()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)
    return output_path
