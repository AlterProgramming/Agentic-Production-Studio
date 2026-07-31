from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from PIL import Image, ImageDraw
import trimesh


def _material_color(mesh: trimesh.Trimesh) -> np.ndarray:
    material = getattr(mesh.visual, "material", None)
    texture = getattr(material, "baseColorTexture", None)
    if texture is not None:
        try:
            array = np.asarray(texture.convert("RGB").resize((8, 8)), dtype=float)
            return array.mean(axis=(0, 1)) / 255.0
        except Exception:
            pass
    factor = getattr(material, "baseColorFactor", None)
    if factor is not None:
        value = np.asarray(factor[:3], dtype=float)
        return value if value.max() <= 1.0 else value / 255.0
    return np.array([0.48, 0.56, 0.63])


def render_glb(glb_path: Path, output_path: Path, *, elev: float = 20, azim: float = -42,
               title: str | None = None, wireframe: bool = False, max_faces: int = 18000,
               pose: dict[str, tuple[str, float]] | None = None) -> None:
    scene = trimesh.load(glb_path, force="scene")
    if pose:
        for node_name, (axis, degrees) in pose.items():
            try:
                original, _ = scene.graph.get(node_name)
                parent = scene.graph.transforms.parents[node_name]
                angle = np.radians(degrees)
                if axis == "x":
                    rotation = trimesh.transformations.rotation_matrix(angle, [1, 0, 0])
                elif axis == "y":
                    rotation = trimesh.transformations.rotation_matrix(angle, [0, 1, 0])
                else:
                    rotation = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
                scene.graph.update(frame_to=node_name, frame_from=parent, matrix=original @ rotation)
            except Exception:
                pass
    meshes = scene.dump(concatenate=False)
    total_faces = sum(len(mesh.faces) for mesh in meshes)
    stride = max(1, int(np.ceil(total_faces / max_faces)))
    light = np.array([-0.45, 0.75, 0.55], dtype=float)
    light /= np.linalg.norm(light)
    fig = plt.figure(figsize=(10.8, 8.0), dpi=150)
    ax = fig.add_subplot(111, projection="3d")
    fig.patch.set_facecolor("#101722")
    ax.set_facecolor("#101722")
    all_vertices = []
    for mesh in meshes:
        if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
            continue
        vertices = np.asarray(mesh.vertices, dtype=float)[:, [0, 2, 1]]
        faces = np.asarray(mesh.faces, dtype=int)[::stride]
        triangles = vertices[faces]
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        lengths = np.linalg.norm(normals, axis=1)
        normals[lengths > 1e-9] /= lengths[lengths > 1e-9, None]
        diffuse = np.clip(normals @ light, -0.2, 1.0)
        shade = 0.45 + 0.55 * np.maximum(diffuse, 0.0)
        base = _material_color(mesh)
        colors = np.clip(base[None, :] * shade[:, None] + 0.05, 0, 1)
        collection = Poly3DCollection(triangles, linewidths=0.08 if wireframe else 0.0,
                                      edgecolors=(0.45, 0.75, 0.92, 0.55) if wireframe else "none")
        collection.set_facecolor(colors)
        ax.add_collection3d(collection)
        all_vertices.append(vertices)
    vertices = np.vstack(all_vertices)
    minimum, maximum = vertices.min(axis=0), vertices.max(axis=0)
    center = (minimum + maximum) / 2
    radius = max(float(np.max(maximum - minimum)) * 0.62, 0.5)
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_proj_type("persp", focal_length=0.8)
    ax.set_axis_off()
    if title:
        ax.set_title(title, color="#edf4fb", fontsize=16, pad=6)
    plt.subplots_adjust(left=0, right=1, top=0.96, bottom=0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def contact_sheet(images: list[tuple[Path, str]], output: Path, *, columns: int = 3) -> None:
    loaded = [(Image.open(path).convert("RGB"), label) for path, label in images]
    width, height = 560, 440
    rows = int(np.ceil(len(loaded) / columns))
    canvas = Image.new("RGB", (columns * width, rows * height), (12, 18, 26))
    draw = ImageDraw.Draw(canvas)
    for index, (image, label) in enumerate(loaded):
        image.thumbnail((width - 24, height - 54), Image.Resampling.LANCZOS)
        x = (index % columns) * width + (width - image.width) // 2
        y = (index // columns) * height + 10
        canvas.paste(image, (x, y))
        draw.text(((index % columns) * width + 18, (index // columns) * height + height - 34), label, fill=(226, 235, 244))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=94)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    images: list[tuple[Path, str]] = []
    for family in ("lamp", "case", "table"):
        for variant_dir in sorted((args.root / family).iterdir()):
            target = args.output / family / f"{variant_dir.name}.png"
            render_glb(variant_dir / "object/object.glb", target, title=f"{family.title()} · {variant_dir.name.replace('_', ' ').title()}")
            images.append((target, f"{family.title()} · {variant_dir.name.replace('_', ' ').title()}"))
    contact_sheet(images, args.output / "scope1-all-variants.png")


if __name__ == "__main__":
    main()
