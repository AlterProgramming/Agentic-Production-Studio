from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from typing import Any

import numpy as np

COMPONENT = {np.dtype(np.float32): 5126, np.dtype(np.uint32): 5125, np.dtype(np.uint16): 5123, np.dtype(np.uint8): 5121}
TYPES = {1: "SCALAR", 2: "VEC2", 3: "VEC3", 4: "VEC4", 16: "MAT4"}


def pack_glb(document: dict[str, Any], binary: bytes) -> bytes:
    json_bytes = json.dumps(document, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    binary += b"\0" * ((4 - len(binary) % 4) % 4)
    total = 12 + 8 + len(json_bytes) + (8 + len(binary) if binary else 0)
    chunks = [struct.pack("<4sII", b"glTF", 2, total), struct.pack("<II", len(json_bytes), 0x4E4F534A), json_bytes]
    if binary:
        chunks.extend([struct.pack("<II", len(binary), 0x004E4942), binary])
    return b"".join(chunks)


def parse_glb(data: bytes) -> tuple[dict[str, Any], bytes]:
    if data[:4] != b"glTF" or struct.unpack_from("<I", data, 4)[0] != 2:
        raise ValueError("invalid GLB header")
    if struct.unpack_from("<I", data, 8)[0] != len(data):
        raise ValueError("GLB length mismatch")
    offset = 12
    json_len, json_type = struct.unpack_from("<II", data, offset)
    if json_type != 0x4E4F534A:
        raise ValueError("missing JSON chunk")
    offset += 8
    document = json.loads(data[offset:offset + json_len].decode("utf-8").rstrip(" \0"))
    offset += json_len
    binary = b""
    if offset < len(data):
        bin_len, bin_type = struct.unpack_from("<II", data, offset)
        if bin_type != 0x004E4942:
            raise ValueError("invalid BIN chunk")
        offset += 8
        binary = data[offset:offset + bin_len]
    return document, binary


@dataclass
class GLBBuilder:
    document: dict[str, Any] = field(default_factory=lambda: {
        "asset": {"version": "2.0", "generator": "GarmentForge.clothing_construction.v2"},
        "scene": 0,
        "scenes": [],
        "nodes": [],
        "meshes": [],
        "materials": [],
        "textures": [],
        "samplers": [],
        "images": [],
        "skins": [],
        "animations": [],
        "bufferViews": [],
        "accessors": [],
        "buffers": [{"byteLength": 0}],
        "extensionsUsed": ["KHR_materials_sheen"],
    })
    binary: bytearray = field(default_factory=bytearray)

    def append_view(self, payload: bytes, target: int | None = None, byte_stride: int | None = None) -> int:
        while len(self.binary) % 4:
            self.binary.append(0)
        offset = len(self.binary)
        self.binary.extend(payload)
        view: dict[str, Any] = {"buffer": 0, "byteOffset": offset, "byteLength": len(payload)}
        if target is not None:
            view["target"] = target
        if byte_stride is not None:
            view["byteStride"] = byte_stride
        self.document["bufferViews"].append(view)
        self.document["buffers"][0]["byteLength"] = len(self.binary)
        return len(self.document["bufferViews"]) - 1

    def accessor(self, array: np.ndarray, target: int | None = None, normalized: bool = False) -> int:
        arr = np.ascontiguousarray(array)
        if arr.dtype not in COMPONENT:
            raise TypeError(f"unsupported accessor dtype: {arr.dtype}")
        if arr.ndim == 1:
            count, width = arr.shape[0], 1
        elif arr.ndim == 2:
            count, width = arr.shape
        elif arr.ndim == 3 and arr.shape[1:] == (4, 4):
            count, width = arr.shape[0], 16
            arr = arr.reshape((count, width))
        else:
            raise ValueError(f"unsupported accessor shape: {arr.shape}")
        view = self.append_view(arr.tobytes(), target=target)
        item: dict[str, Any] = {
            "bufferView": view,
            "byteOffset": 0,
            "componentType": COMPONENT[arr.dtype],
            "count": int(count),
            "type": TYPES[width],
        }
        if normalized:
            item["normalized"] = True
        if np.issubdtype(arr.dtype, np.floating) and width in (1, 2, 3, 4):
            item["min"] = np.min(arr, axis=0).astype(float).reshape(-1).tolist()
            item["max"] = np.max(arr, axis=0).astype(float).reshape(-1).tolist()
        self.document["accessors"].append(item)
        return len(self.document["accessors"]) - 1

    def add_image(self, png: bytes, name: str) -> int:
        view = self.append_view(png)
        self.document["images"].append({"name": name, "bufferView": view, "mimeType": "image/png"})
        return len(self.document["images"]) - 1

    def add_texture(self, image: int, *, clamp: bool = False) -> int:
        sampler = {"magFilter": 9729, "minFilter": 9987, "wrapS": 33071 if clamp else 10497, "wrapT": 33071 if clamp else 10497}
        self.document["samplers"].append(sampler)
        self.document["textures"].append({"sampler": len(self.document["samplers"]) - 1, "source": image})
        return len(self.document["textures"]) - 1

    def add_textile_material(self, name: str, base_texture: int, normal_texture: int, roughness_texture: int, color: list[float], roughness: float, sheen: list[float]) -> int:
        self.document["materials"].append({
            "name": name,
            "doubleSided": True,
            "pbrMetallicRoughness": {
                "baseColorFactor": color,
                "baseColorTexture": {"index": base_texture},
                "metallicRoughnessTexture": {"index": roughness_texture},
                "metallicFactor": 0.0,
                "roughnessFactor": roughness,
            },
            "normalTexture": {"index": normal_texture, "scale": 0.42},
            "extensions": {"KHR_materials_sheen": {"sheenColorFactor": sheen, "sheenRoughnessFactor": 0.72}},
            "extras": {"material_class": "woven_textile", "two_sided_fabric": True, "macro_variation": True},
        })
        return len(self.document["materials"]) - 1

    def add_plain_material(self, name: str, color: list[float], roughness: float = 0.68) -> int:
        self.document["materials"].append({
            "name": name,
            "pbrMetallicRoughness": {
                "baseColorFactor": color,
                "metallicFactor": 0.0,
                "roughnessFactor": roughness,
            },
            "extras": {"material_class": "plain_body", "textile": False},
        })
        return len(self.document["materials"]) - 1

    def finish(self) -> bytes:
        self.document["buffers"][0]["byteLength"] = len(self.binary)
        return pack_glb(self.document, bytes(self.binary))
