from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from PIL import Image
from trimesh.visual.material import PBRMaterial


@dataclass(frozen=True)
class RuntimeMaterial:
    name: str
    base_color: tuple[int, int, int]
    metallic: float
    roughness: float
    texture_kind: str
    emissive: tuple[float, float, float] = (0.0, 0.0, 0.0)
    clearcoat: float = 0.0


def _texture(kind: str, base: tuple[int, int, int], *, size: int = 192, seed: int = 1) -> tuple[Image.Image, Image.Image]:
    rng = np.random.default_rng(seed + sum(base) + len(kind) * 13)
    yy, xx = np.mgrid[0:size, 0:size]
    color = np.zeros((size, size, 3), dtype=np.float32)
    color[:] = np.asarray(base, dtype=np.float32)
    roughness = np.full((size, size), 128.0, dtype=np.float32)
    metallic = np.zeros((size, size), dtype=np.float32)

    if kind in {"powder_coat", "painted_metal"}:
        grain = rng.normal(0.0, 3.0, (size, size))
        color += grain[..., None]
        roughness[:] = 130 + rng.normal(0, 6, (size, size))
        metallic[:] = 52 if kind == "painted_metal" else 24
    elif kind == "brushed_metal":
        brush = 7 * np.sin(xx * 0.34) + 2.5 * np.sin(xx * 1.4) + rng.normal(0, 1.8, (size, size))
        color += brush[..., None]
        roughness[:] = 52 + 13 * (0.5 + 0.5 * np.sin(xx * 0.17))
        metallic[:] = 244
    elif kind == "rubber":
        color += rng.normal(0, 2.3, (size, size))[..., None]
        roughness[:] = 228
    elif kind in {"plastic", "molded_plastic"}:
        color += rng.normal(0, 1.4, (size, size))[..., None]
        roughness[:] = 102 if kind == "plastic" else 145
    elif kind in {"oak", "walnut"}:
        wave = 10 * np.sin(xx * 0.09 + 1.2 * np.sin(yy * 0.025)) + 4 * np.sin(xx * 0.25 + yy * 0.015) + rng.normal(0, 1.2, (size, size))
        if kind == "walnut":
            wave *= 0.7
        color += wave[..., None] * np.array([1.0, 0.72, 0.38])[None, None, :]
        roughness[:] = 105 + 16 * (0.5 + 0.5 * np.sin(xx * 0.08))
    elif kind in {"fabric", "felt"}:
        weave = 4.0 * ((xx % 5 == 0) | (yy % 5 == 0)) + rng.normal(0, 1.5, (size, size))
        color += weave[..., None]
        roughness[:] = 222 if kind == "felt" else 194
    elif kind == "ceramic":
        speckles = rng.random((size, size)) > 0.986
        color += rng.normal(0, 1.0, (size, size))[..., None]
        color[speckles] -= np.array([12, 10, 8], dtype=float)
        roughness[:] = 72
    elif kind == "reflector":
        radial = np.sqrt((xx - size / 2) ** 2 + (yy - size / 2) ** 2)
        color += (7 * np.sin(radial * 0.42))[..., None]
        roughness[:] = 34 + 8 * np.sin(radial * 0.25)
        metallic[:] = 250
    elif kind == "carbon":
        checker = ((xx // 7 + yy // 7) % 2) * 6 - 3
        color += checker[..., None]
        roughness[:] = 115
        metallic[:] = 110
    elif kind == "emitter":
        color[:] = np.asarray(base, dtype=float)
        roughness[:] = 38
    else:
        color += rng.normal(0, 0.8, (size, size))[..., None]

    color = np.uint8(np.clip(color, 0, 255))
    orm = np.zeros((size, size, 3), dtype=np.uint8)
    orm[..., 0] = 255
    orm[..., 1] = np.uint8(np.clip(roughness, 0, 255))
    orm[..., 2] = np.uint8(np.clip(metallic, 0, 255))
    return Image.fromarray(color, mode="RGB"), Image.fromarray(orm, mode="RGB")


def material_library() -> dict[str, tuple[RuntimeMaterial, PBRMaterial]]:
    specs: Iterable[RuntimeMaterial] = (
        RuntimeMaterial("GraphitePowderCoat", (38, 48, 57), 0.08, 0.36, "powder_coat", clearcoat=0.16),
        RuntimeMaterial("IvoryPowderCoat", (214, 207, 190), 0.07, 0.38, "powder_coat", clearcoat=0.18),
        RuntimeMaterial("SignalOrange", (190, 74, 34), 0.06, 0.42, "painted_metal", clearcoat=0.16),
        RuntimeMaterial("WarmAluminum", (177, 151, 112), 0.94, 0.23, "brushed_metal", clearcoat=0.05),
        RuntimeMaterial("BrushedSteel", (166, 173, 179), 0.96, 0.20, "brushed_metal"),
        RuntimeMaterial("Brass", (184, 137, 58), 0.92, 0.24, "brushed_metal", clearcoat=0.08),
        RuntimeMaterial("DarkRubber", (25, 28, 31), 0.0, 0.88, "rubber"),
        RuntimeMaterial("CableBlack", (14, 17, 19), 0.0, 0.76, "rubber"),
        RuntimeMaterial("MoldedBlack", (36, 39, 43), 0.0, 0.58, "molded_plastic", clearcoat=0.1),
        RuntimeMaterial("MoldedBlue", (47, 83, 112), 0.0, 0.56, "molded_plastic", clearcoat=0.1),
        RuntimeMaterial("SwitchPlastic", (158, 57, 39), 0.0, 0.34, "plastic", clearcoat=0.24),
        RuntimeMaterial("ReflectorSilver", (215, 220, 225), 1.0, 0.14, "reflector"),
        RuntimeMaterial("WarmEmitter", (255, 231, 184), 0.0, 0.18, "emitter", emissive=(1.0, 0.67, 0.30)),
        RuntimeMaterial("OakVarnish", (162, 113, 66), 0.0, 0.43, "oak", clearcoat=0.16),
        RuntimeMaterial("WalnutVarnish", (91, 60, 42), 0.0, 0.47, "walnut", clearcoat=0.14),
        RuntimeMaterial("CeramicWhite", (221, 218, 207), 0.0, 0.28, "ceramic", clearcoat=0.22),
        RuntimeMaterial("FabricLiner", (64, 72, 79), 0.0, 0.84, "fabric"),
        RuntimeMaterial("VelvetLiner", (78, 38, 50), 0.0, 0.91, "felt"),
        RuntimeMaterial("CarbonInsert", (45, 48, 52), 0.42, 0.52, "carbon", clearcoat=0.18),
        RuntimeMaterial("StageMatte", (70, 80, 92), 0.0, 0.88, "powder_coat"),
        RuntimeMaterial("StageFloor", (40, 45, 52), 0.0, 0.66, "powder_coat"),
    )
    result: dict[str, tuple[RuntimeMaterial, PBRMaterial]] = {}
    for index, spec in enumerate(specs):
        base, orm = _texture(spec.texture_kind, spec.base_color, seed=71 + index * 7)
        result[spec.name] = (spec, PBRMaterial(name=spec.name, baseColorFactor=[1, 1, 1, 1], baseColorTexture=base, metallicFactor=1.0, roughnessFactor=1.0, metallicRoughnessTexture=orm, emissiveFactor=list(spec.emissive), doubleSided=False))
    return result
