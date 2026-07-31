from __future__ import annotations

import json
import math
import struct
from typing import Any

import numpy as np
import trimesh


def parse_glb(data: bytes) -> tuple[dict[str, Any], bytes]:
    if data[:4] != b"glTF" or struct.unpack_from("<I", data, 4)[0] != 2:
        raise ValueError("invalid GLB header")
    total = struct.unpack_from("<I", data, 8)[0]
    if total != len(data):
        raise ValueError("GLB length mismatch")
    offset = 12
    json_len, json_type = struct.unpack_from("<II", data, offset)
    offset += 8
    if json_type != 0x4E4F534A:
        raise ValueError("missing JSON chunk")
    document = json.loads(data[offset:offset + json_len].decode("utf-8").rstrip(" " + chr(0)))
    offset += json_len
    binary = b""
    if offset < len(data):
        bin_len, bin_type = struct.unpack_from("<II", data, offset)
        offset += 8
        if bin_type != 0x004E4942:
            raise ValueError("invalid BIN chunk")
        binary = data[offset:offset + bin_len]
    return document, binary


def pack_glb(document: dict[str, Any], binary: bytes) -> bytes:
    json_bytes = json.dumps(document, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    binary += bytes([0]) * ((4 - len(binary) % 4) % 4)
    total = 12 + 8 + len(json_bytes) + (8 + len(binary) if binary else 0)
    chunks = [struct.pack("<4sII", b"glTF", 2, total), struct.pack("<II", len(json_bytes), 0x4E4F534A), json_bytes]
    if binary:
        chunks.extend([struct.pack("<II", len(binary), 0x004E4942), binary])
    return b"".join(chunks)


def append_binary(document: dict[str, Any], binary: bytes, payload: bytes, target: int | None = None) -> tuple[bytes, int]:
    pad = (4 - len(binary) % 4) % 4
    binary += bytes([0]) * pad
    offset = len(binary)
    binary += payload
    view = {"buffer": 0, "byteOffset": offset, "byteLength": len(payload)}
    if target is not None:
        view["target"] = target
    document.setdefault("bufferViews", []).append(view)
    document.setdefault("buffers", [{"byteLength": 0}])[0]["byteLength"] = len(binary)
    return binary, len(document["bufferViews"]) - 1


def append_accessor(document: dict[str, Any], view_index: int, component_type: int, count: int, accessor_type: str,
                    min_value: list[float] | None = None, max_value: list[float] | None = None) -> int:
    accessor: dict[str, Any] = {
        "bufferView": view_index,
        "byteOffset": 0,
        "componentType": component_type,
        "count": count,
        "type": accessor_type,
    }
    if min_value is not None:
        accessor["min"] = min_value
    if max_value is not None:
        accessor["max"] = max_value
    document.setdefault("accessors", []).append(accessor)
    return len(document["accessors"]) - 1


def quaternion_z(angle: float) -> list[float]:
    return [0.0, 0.0, math.sin(angle / 2.0), math.cos(angle / 2.0)]


def quaternion_from_matrix(matrix: np.ndarray) -> list[float]:
    q = trimesh.transformations.quaternion_from_matrix(matrix)
    return [float(q[1]), float(q[2]), float(q[3]), float(q[0])]


def matrix_to_trs(matrix_list: list[float]) -> tuple[list[float], list[float], list[float]]:
    matrix = np.asarray(matrix_list, dtype=float).reshape((4, 4), order="F")
    translation_v = matrix[:3, 3].tolist()
    scale_v = [float(np.linalg.norm(matrix[:3, i])) for i in range(3)]
    rot = matrix.copy()
    for i in range(3):
        if scale_v[i] > 1e-12:
            rot[:3, i] /= scale_v[i]
    return translation_v, quaternion_from_matrix(rot), scale_v
