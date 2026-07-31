from __future__ import annotations

import math
from typing import Any

import numpy as np

from objectforge.gltf import append_accessor, append_binary, matrix_to_trs, pack_glb, parse_glb
from objectforge.grammar.core import GrammarAssetBuilder


def _quat(axis: tuple[float, float, float], angle: float) -> list[float]:
    axis_v = np.asarray(axis, dtype=float)
    axis_v /= max(float(np.linalg.norm(axis_v)), 1e-12)
    s = math.sin(angle / 2.0)
    return [float(axis_v[0] * s), float(axis_v[1] * s), float(axis_v[2] * s), float(math.cos(angle / 2.0))]


def patch_runtime_glb(data: bytes, *, builder: GrammarAssetBuilder, construction_hash: str, showcase: bool) -> bytes:
    document, binary = parse_glb(data)
    node_by_name = {node.get("name"): index for index, node in enumerate(document.get("nodes", []))}

    if builder.articulations:
        times = np.asarray([0.0, 1.5, 3.0, 4.5, 6.0], dtype="<f4")
        binary, time_view = append_binary(document, binary, times.tobytes())
        time_accessor = append_accessor(document, time_view, 5126, len(times), "SCALAR", [0.0], [6.0])
        samplers: list[dict[str, Any]] = []
        channels: list[dict[str, Any]] = []
        for articulation in builder.articulations:
            node_index = node_by_name.get(articulation.node)
            if node_index is None:
                raise ValueError(f"missing articulation node {articulation.node}")
            node = document["nodes"][node_index]
            if "matrix" in node:
                translation_v, rotation_v, scale_v = matrix_to_trs(node.pop("matrix"))
                node["translation"] = translation_v
                node["rotation"] = rotation_v
                node["scale"] = scale_v
            low, high = articulation.limits_degrees
            degrees = [0.0, high * 0.34, low * 0.30, high * 0.16, 0.0]
            rotations = np.asarray([_quat(articulation.axis, math.radians(value)) for value in degrees], dtype="<f4")
            binary, rotation_view = append_binary(document, binary, rotations.tobytes())
            rotation_accessor = append_accessor(document, rotation_view, 5126, len(rotations), "VEC4")
            sampler_index = len(samplers)
            samplers.append({"input": time_accessor, "output": rotation_accessor, "interpolation": "LINEAR"})
            channels.append({"sampler": sampler_index, "target": {"node": node_index, "path": "rotation"}})
            node.setdefault("extras", {})["physics_joint"] = {"id": articulation.id, "axis": list(articulation.axis), "limits_degrees": list(articulation.limits_degrees), "damping": articulation.damping}
        document.setdefault("animations", []).append({"name": "functional_demo", "samplers": samplers, "channels": channels})

    extensions_used = set(document.get("extensionsUsed", []))
    extensions_used.add("KHR_materials_clearcoat")
    lights: list[dict[str, Any]] = []
    emitter_anchor = node_by_name.get("EmitterLightAnchor")
    if emitter_anchor is not None:
        extensions_used.add("KHR_lights_punctual")
        lights.append({"name": "ObjectEmitter", "type": "spot", "color": [1.0, 0.78, 0.48], "intensity": 120.0, "range": 8.0, "spot": {"innerConeAngle": 0.26, "outerConeAngle": 0.72}})
        document["nodes"][emitter_anchor].setdefault("extensions", {})["KHR_lights_punctual"] = {"light": 0}

    if showcase:
        extensions_used.add("KHR_lights_punctual")
        offset = len(lights)
        lights.extend([
            {"name": "ShowcaseKey", "type": "point", "color": [1.0, 0.91, 0.82], "intensity": 110.0, "range": 16.0},
            {"name": "ShowcaseFill", "type": "point", "color": [0.55, 0.72, 1.0], "intensity": 64.0, "range": 16.0},
            {"name": "ShowcaseRim", "type": "point", "color": [0.35, 0.82, 1.0], "intensity": 80.0, "range": 14.0},
        ])
        document.setdefault("cameras", []).append({"name": "ShowcaseCamera", "type": "perspective", "perspective": {"yfov": 0.63, "znear": 0.05, "zfar": 100.0}})
        new_nodes = [
            {"name": "ShowcaseCameraNode", "camera": len(document["cameras"]) - 1, "translation": [5.8, 3.8, 7.2], "rotation": [-0.12, 0.32, 0.04, 0.94]},
            {"name": "ShowcaseKeyNode", "translation": [-3.5, 6.0, 4.8], "extensions": {"KHR_lights_punctual": {"light": offset}}},
            {"name": "ShowcaseFillNode", "translation": [4.8, 3.4, 3.2], "extensions": {"KHR_lights_punctual": {"light": offset + 1}}},
            {"name": "ShowcaseRimNode", "translation": [1.2, 5.0, -4.0], "extensions": {"KHR_lights_punctual": {"light": offset + 2}}},
        ]
        start = len(document["nodes"])
        document["nodes"].extend(new_nodes)
        document["scenes"][document.get("scene", 0)].setdefault("nodes", []).extend(range(start, start + len(new_nodes)))

    if lights:
        document.setdefault("extensions", {})["KHR_lights_punctual"] = {"lights": lights}

    for material in document.get("materials", []):
        name = material.get("name", "")
        if name in {"GraphitePowderCoat", "IvoryPowderCoat", "SignalOrange", "SwitchPlastic", "OakVarnish", "WalnutVarnish", "CeramicWhite"}:
            material.setdefault("extensions", {})["KHR_materials_clearcoat"] = {"clearcoatFactor": 0.18, "clearcoatRoughnessFactor": 0.24}
        if name == "WarmEmitter":
            extensions_used.add("KHR_materials_emissive_strength")
            material.setdefault("extensions", {})["KHR_materials_emissive_strength"] = {"emissiveStrength": 7.5}
    document["extensionsUsed"] = sorted(extensions_used)

    semantic = builder.semantic_contract()
    semantic_lookup = {node_name: semantic_id for semantic_id, info in semantic["semantic_parts"].items() for node_name in info["nodes"]}
    for node in document.get("nodes", []):
        if node.get("name") in semantic_lookup:
            node.setdefault("extras", {})["semantic_part"] = semantic_lookup[node["name"]]
    root_index = node_by_name.get(builder.root_name)
    if root_index is not None:
        document["nodes"][root_index].setdefault("extras", {})["objectforge"] = {"family": builder.family, "variant": builder.variant, "physics_contract": "../behavior/physics.json", "semantic_contract": "semantic-parts.json" if not showcase else "../object/semantic-parts.json"}
    document.setdefault("asset", {}).setdefault("extras", {})["objectforge"] = {"schema_version": "1.0", "capability_id": "objectforge.grammar-driven-detailed-assets.v1", "construction_sha256": construction_hash, "family": builder.family, "variant": builder.variant, "canonical_asset": not showcase, "showcase_asset": showcase, "external_finished_model_provider": False}
    document["buffers"][0]["byteLength"] = len(binary)
    return pack_glb(document, binary)
