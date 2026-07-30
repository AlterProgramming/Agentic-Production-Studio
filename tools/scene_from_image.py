#!/usr/bin/env python3
"""Convert an image into a reusable, animated glTF scene.

The image becomes an embedded texture on named geometry. The GLB also carries
an explicit camera, two lights, animation, stable node names, and truth-boundary
metadata. This is a scene derivative, not an assertion that missing source
pixels or identities were recovered.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image

GLTF_JSON_CHUNK = 0x4E4F534A
GLTF_BIN_CHUNK = 0x004E4942
ARRAY_BUFFER = 34962
ELEMENT_ARRAY_BUFFER = 34963
FLOAT = 5126
UNSIGNED_SHORT = 5123


def _pad4(data: bytes, fill: bytes = b"\x00") -> bytes:
    return data + fill * ((-len(data)) % 4)


def _pack_f32(values: Iterable[float]) -> bytes:
    values = tuple(float(v) for v in values)
    return struct.pack(f"<{len(values)}f", *values)


def _pack_u16(values: Iterable[int]) -> bytes:
    values = tuple(int(v) for v in values)
    return struct.pack(f"<{len(values)}H", *values)


def _flat(rows: Sequence[Sequence[float]]) -> list[float]:
    return [value for row in rows for value in row]


@dataclass
class BufferBuilder:
    data: bytearray
    views: list[dict]
    accessors: list[dict]

    @classmethod
    def create(cls) -> "BufferBuilder":
        return cls(bytearray(), [], [])

    def add_view(self, payload: bytes, *, target: int | None = None) -> int:
        while len(self.data) % 4:
            self.data.append(0)
        offset = len(self.data)
        self.data.extend(payload)
        view = {"buffer": 0, "byteOffset": offset, "byteLength": len(payload)}
        if target is not None:
            view["target"] = target
        self.views.append(view)
        return len(self.views) - 1

    def add_accessor(
        self,
        payload: bytes,
        *,
        component_type: int,
        count: int,
        type_name: str,
        target: int | None = None,
        minimum: Sequence[float] | None = None,
        maximum: Sequence[float] | None = None,
    ) -> int:
        view = self.add_view(payload, target=target)
        accessor = {
            "bufferView": view,
            "byteOffset": 0,
            "componentType": component_type,
            "count": count,
            "type": type_name,
        }
        if minimum is not None:
            accessor["min"] = list(minimum)
        if maximum is not None:
            accessor["max"] = list(maximum)
        self.accessors.append(accessor)
        return len(self.accessors) - 1


def _quad(width: float, height: float, z: float) -> tuple[list[list[float]], list[list[float]], list[list[float]], list[int]]:
    positions = [
        [-width / 2, -height / 2, z],
        [ width / 2, -height / 2, z],
        [ width / 2,  height / 2, z],
        [-width / 2,  height / 2, z],
    ]
    normals = [[0.0, 0.0, 1.0]] * 4
    texcoords = [[0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]
    indices = [0, 1, 2, 0, 2, 3]
    return positions, normals, texcoords, indices


def _box(width: float, height: float, depth: float) -> tuple[list[list[float]], list[list[float]], list[int]]:
    x, y, z = width / 2, height / 2, depth / 2
    faces = [
        ((0, 0, 1), [(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]),
        ((0, 0,-1), [(x,-y,-z),(-x,-y,-z),(-x,y,-z),(x,y,-z)]),
        ((1, 0, 0), [(x,-y,z),(x,-y,-z),(x,y,-z),(x,y,z)]),
        ((-1,0, 0), [(-x,-y,-z),(-x,-y,z),(-x,y,z),(-x,y,-z)]),
        ((0, 1, 0), [(-x,y,z),(x,y,z),(x,y,-z),(-x,y,-z)]),
        ((0,-1, 0), [(-x,-y,-z),(x,-y,-z),(x,-y,z),(-x,-y,z)]),
    ]
    positions: list[list[float]] = []
    normals: list[list[float]] = []
    indices: list[int] = []
    for normal, corners in faces:
        start = len(positions)
        positions.extend([list(v) for v in corners])
        normals.extend([list(normal)] * 4)
        indices.extend([start, start+1, start+2, start, start+2, start+3])
    return positions, normals, indices


def _mesh_primitive(
    builder: BufferBuilder,
    positions: Sequence[Sequence[float]],
    normals: Sequence[Sequence[float]],
    indices: Sequence[int],
    *,
    material: int,
    texcoords: Sequence[Sequence[float]] | None = None,
) -> dict:
    mins = [min(row[i] for row in positions) for i in range(3)]
    maxs = [max(row[i] for row in positions) for i in range(3)]
    pos = builder.add_accessor(
        _pack_f32(_flat(positions)), component_type=FLOAT, count=len(positions),
        type_name="VEC3", target=ARRAY_BUFFER, minimum=mins, maximum=maxs,
    )
    norm = builder.add_accessor(
        _pack_f32(_flat(normals)), component_type=FLOAT, count=len(normals),
        type_name="VEC3", target=ARRAY_BUFFER,
    )
    attrs = {"POSITION": pos, "NORMAL": norm}
    if texcoords is not None:
        uv = builder.add_accessor(
            _pack_f32(_flat(texcoords)), component_type=FLOAT, count=len(texcoords),
            type_name="VEC2", target=ARRAY_BUFFER,
        )
        attrs["TEXCOORD_0"] = uv
    idx = builder.add_accessor(
        _pack_u16(indices), component_type=UNSIGNED_SHORT, count=len(indices),
        type_name="SCALAR", target=ELEMENT_ARRAY_BUFFER,
        minimum=[min(indices)], maximum=[max(indices)],
    )
    return {"attributes": attrs, "indices": idx, "material": material, "mode": 4}


def _quat_y(degrees: float) -> list[float]:
    half = math.radians(degrees) / 2
    return [0.0, math.sin(half), 0.0, math.cos(half)]


def _texture_payload(image_path: Path, max_texture: int) -> tuple[bytes, str, list[int]]:
    image = Image.open(image_path).convert("RGB")
    original_size = list(image.size)
    image.thumbnail((max_texture, max_texture), Image.Resampling.LANCZOS)
    stream = io.BytesIO()
    image.save(stream, format="JPEG", quality=90, optimize=True, progressive=True)
    return stream.getvalue(), "image/jpeg", original_size


def build_scene(source: Path, output: Path, *, title: str, max_texture: int = 1024) -> tuple[Path, Path]:
    texture, mime_type, original_size = _texture_payload(source, max_texture)
    with Image.open(source) as image:
        aspect = image.width / image.height
    panel_width = 3.2
    panel_height = panel_width / aspect

    builder = BufferBuilder.create()
    image_view = builder.add_view(texture)

    surface = _quad(panel_width, panel_height, 0.061)
    backing = _box(panel_width + 0.18, panel_height + 0.18, 0.12)
    pedestal = _box(1.15, 0.34, 0.48)

    meshes = [
        {"name": "ReconstructionSurface", "primitives": [
            _mesh_primitive(builder, surface[0], surface[1], surface[3], material=0, texcoords=surface[2])
        ]},
        {"name": "PanelBacking", "primitives": [
            _mesh_primitive(builder, backing[0], backing[1], backing[2], material=1)
        ]},
        {"name": "Pedestal", "primitives": [
            _mesh_primitive(builder, pedestal[0], pedestal[1], pedestal[2], material=2)
        ]},
    ]

    times = [0.0, 1.5, 3.0, 4.5, 6.0]
    rotations = [_quat_y(v) for v in (-5.0, 2.5, 5.0, -2.5, -5.0)]
    translations = [[0.0, v, 0.0] for v in (-0.02, 0.045, -0.02, 0.045, -0.02)]
    time_accessor = builder.add_accessor(
        _pack_f32(times), component_type=FLOAT, count=len(times), type_name="SCALAR",
        minimum=[min(times)], maximum=[max(times)],
    )
    rotation_accessor = builder.add_accessor(
        _pack_f32(_flat(rotations)), component_type=FLOAT, count=len(rotations), type_name="VEC4",
    )
    translation_accessor = builder.add_accessor(
        _pack_f32(_flat(translations)), component_type=FLOAT, count=len(translations), type_name="VEC3",
    )

    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    gltf = {
        "asset": {
            "version": "2.0",
            "generator": "Agentic Production Studio model-first scene_from_image",
            "extras": {
                "canonicalCapability": "visual-generation.model-first.v1",
                "sourceSha256": source_hash,
                "truthBoundary": "Scene derivative of the supplied image; missing source content is not claimed as recovered.",
            },
        },
        "extensionsUsed": ["KHR_lights_punctual"],
        "extensions": {"KHR_lights_punctual": {"lights": [
            {"name": "KeyLight", "type": "point", "color": [1.0, 0.94, 0.86], "intensity": 65.0, "range": 12.0},
            {"name": "FillLight", "type": "point", "color": [0.78, 0.86, 1.0], "intensity": 32.0, "range": 12.0},
        ]}},
        "scene": 0,
        "scenes": [{"name": title, "nodes": [0, 4, 5, 6]}],
        "nodes": [
            {"name": "SceneRoot", "children": [1, 2, 3]},
            {"name": "ReconstructionSurface", "mesh": 0},
            {"name": "PanelBacking", "mesh": 1},
            {"name": "Pedestal", "mesh": 2, "translation": [0.0, -panel_height/2 - 0.38, -0.16]},
            {"name": "PrimaryCamera", "camera": 0, "translation": [0.0, 0.0, 5.55]},
            {"name": "KeyLight", "translation": [-2.4, 2.8, 4.2], "extensions": {"KHR_lights_punctual": {"light": 0}}},
            {"name": "FillLight", "translation": [2.8, -0.5, 3.4], "extensions": {"KHR_lights_punctual": {"light": 1}}},
        ],
        "cameras": [{"name": "PrimaryCamera", "type": "perspective", "perspective": {
            "yfov": math.radians(38.0), "znear": 0.1, "zfar": 100.0,
        }}],
        "meshes": meshes,
        "materials": [
            {"name": "ReconstructionTexture", "pbrMetallicRoughness": {
                "baseColorTexture": {"index": 0}, "metallicFactor": 0.0, "roughnessFactor": 0.72,
            }, "doubleSided": True},
            {"name": "PanelBackingMaterial", "pbrMetallicRoughness": {
                "baseColorFactor": [0.94, 0.94, 0.96, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.78,
            }},
            {"name": "PedestalMaterial", "pbrMetallicRoughness": {
                "baseColorFactor": [0.18, 0.20, 0.25, 1.0], "metallicFactor": 0.18, "roughnessFactor": 0.48,
            }},
        ],
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}],
        "textures": [{"name": "ReconstructionTexture", "sampler": 0, "source": 0}],
        "images": [{"name": source.stem, "bufferView": image_view, "mimeType": mime_type}],
        "animations": [{
            "name": "SceneBreathingLoop",
            "samplers": [
                {"input": time_accessor, "output": rotation_accessor, "interpolation": "LINEAR"},
                {"input": time_accessor, "output": translation_accessor, "interpolation": "LINEAR"},
            ],
            "channels": [
                {"sampler": 0, "target": {"node": 0, "path": "rotation"}},
                {"sampler": 1, "target": {"node": 0, "path": "translation"}},
            ],
        }],
        "buffers": [{"byteLength": len(builder.data)}],
        "bufferViews": builder.views,
        "accessors": builder.accessors,
    }

    json_chunk = _pad4(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), b" ")
    bin_chunk = _pad4(bytes(builder.data))
    total_length = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    glb = (
        struct.pack("<4sII", b"glTF", 2, total_length)
        + struct.pack("<II", len(json_chunk), GLTF_JSON_CHUNK) + json_chunk
        + struct.pack("<II", len(bin_chunk), GLTF_BIN_CHUNK) + bin_chunk
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(glb)

    manifest = {
        "schema_version": "1.0.0",
        "kind": "scene-model",
        "scene_id": output.stem,
        "title": title,
        "canonical_capability": "visual-generation.model-first.v1",
        "source": {
            "path": source.name,
            "sha256": source_hash,
            "dimensions_px": original_size,
            "status": "inferred-not-decoded",
            "truth_boundary": "This packages the available reconstruction as a scene; it does not recover the original missing picture.",
        },
        "assets": {"model": output.name},
        "nodes": ["SceneRoot", "ReconstructionSurface", "PanelBacking", "Pedestal", "PrimaryCamera", "KeyLight", "FillLight"],
        "motion": {"clip": "SceneBreathingLoop", "duration_seconds": 6.0, "loop": True},
        "validation": {
            "required_named_nodes": True,
            "embedded_texture": True,
            "camera": True,
            "lights": 2,
            "animation_channels": 2,
        },
    }
    manifest_path = output.with_suffix(".scene.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return output, manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--title", default="Model-first image scene")
    parser.add_argument("--max-texture", type=int, default=1024)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.image.is_file():
        raise SystemExit(f"image does not exist: {args.image}")
    if args.max_texture < 128:
        raise SystemExit("--max-texture must be at least 128")
    model, manifest = build_scene(args.image, args.out, title=args.title, max_texture=args.max_texture)
    print(model)
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
