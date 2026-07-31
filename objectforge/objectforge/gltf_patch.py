from __future__ import annotations

import math
from typing import Any

import numpy as np

from .gltf import append_accessor, append_binary, matrix_to_trs, pack_glb, parse_glb, quaternion_z


def patch_glb(data: bytes, *, construction_hash: str, physics: dict[str, Any], semantic: dict[str, Any], showcase: bool) -> bytes:
    doc, binary = parse_glb(data)
    node_by_name = {node.get("name"): i for i, node in enumerate(doc.get("nodes", []))}

    for name in ["LowerArmPivot", "UpperArmPivot", "ShadePivot"]:
        idx = node_by_name.get(name)
        if idx is None:
            raise ValueError(f"missing animated node {name}")
        node = doc["nodes"][idx]
        if "matrix" in node:
            translation, rotation, scale = matrix_to_trs(node.pop("matrix"))
            node["translation"] = translation
            node["rotation"] = rotation
            node["scale"] = scale

    times = np.asarray([0.0, 1.5, 3.0, 4.5, 6.0], dtype="<f4")
    binary, time_view = append_binary(doc, binary, times.tobytes())
    time_accessor = append_accessor(doc, time_view, 5126, len(times), "SCALAR", [0.0], [6.0])

    tracks = {
        "LowerArmPivot": [math.radians(a) for a in (0, 8, -10, 5, 0)],
        "UpperArmPivot": [math.radians(a) for a in (0, -18, 12, -8, 0)],
        "ShadePivot": [math.radians(a) for a in (0, 14, -20, 9, 0)],
    }
    samplers = []
    channels = []
    for name, angles in tracks.items():
        quaternions = np.asarray([quaternion_z(angle) for angle in angles], dtype="<f4")
        binary, view = append_binary(doc, binary, quaternions.tobytes())
        accessor = append_accessor(doc, view, 5126, len(quaternions), "VEC4")
        sampler_index = len(samplers)
        samplers.append({"input": time_accessor, "output": accessor, "interpolation": "LINEAR"})
        channels.append({"sampler": sampler_index, "target": {"node": node_by_name[name], "path": "rotation"}})
    doc.setdefault("animations", []).append({"name": "articulation_demo", "samplers": samplers, "channels": channels})

    extensions_used = set(doc.get("extensionsUsed", []))
    extensions_used.update(["KHR_lights_punctual", "KHR_materials_emissive_strength", "KHR_materials_clearcoat"])
    doc["extensionsUsed"] = sorted(extensions_used)
    lights = [
        {"name": "BulbSpot", "type": "spot", "color": [1.0, 0.78, 0.48], "intensity": 135.0, "range": 8.0,
         "spot": {"innerConeAngle": 0.28, "outerConeAngle": 0.72}},
    ]
    if showcase:
        lights.extend([
            {"name": "ShowcaseKey", "type": "point", "color": [1.0, 0.91, 0.82], "intensity": 105.0, "range": 14.0},
            {"name": "ShowcaseFill", "type": "point", "color": [0.58, 0.74, 1.0], "intensity": 62.0, "range": 14.0},
            {"name": "ShowcaseRim", "type": "point", "color": [0.35, 0.82, 1.0], "intensity": 78.0, "range": 12.0},
        ])
    doc.setdefault("extensions", {})["KHR_lights_punctual"] = {"lights": lights}
    light_anchor = node_by_name.get("BulbLightAnchor")
    if light_anchor is not None:
        doc["nodes"][light_anchor].setdefault("extensions", {})["KHR_lights_punctual"] = {"light": 0}

    if showcase:
        doc.setdefault("cameras", []).append({
            "name": "ShowcaseCamera", "type": "perspective",
            "perspective": {"yfov": 0.62, "znear": 0.05, "zfar": 100.0},
        })
        additions = [
            {"name": "ShowcaseCameraNode", "camera": len(doc["cameras"]) - 1,
             "translation": [5.35, 3.05, 6.55], "rotation": [-0.12, 0.34, 0.045, 0.93]},
            {"name": "ShowcaseKeyNode", "translation": [-3.2, 5.8, 4.4],
             "extensions": {"KHR_lights_punctual": {"light": 1}}},
            {"name": "ShowcaseFillNode", "translation": [4.4, 3.2, 3.0],
             "extensions": {"KHR_lights_punctual": {"light": 2}}},
            {"name": "ShowcaseRimNode", "translation": [1.5, 4.8, -3.8],
             "extensions": {"KHR_lights_punctual": {"light": 3}}},
        ]
        start = len(doc["nodes"])
        doc["nodes"].extend(additions)
        doc["scenes"][doc.get("scene", 0)].setdefault("nodes", []).extend(range(start, start + len(additions)))

    for material in doc.get("materials", []):
        if material.get("name") == "WarmEmitter":
            material.setdefault("extensions", {})["KHR_materials_emissive_strength"] = {"emissiveStrength": 8.0}
        if material.get("name") in {"GraphitePowderCoat", "SwitchPlastic"}:
            material.setdefault("extensions", {})["KHR_materials_clearcoat"] = {
                "clearcoatFactor": 0.18 if material.get("name") == "GraphitePowderCoat" else 0.28,
                "clearcoatRoughnessFactor": 0.22,
            }

    doc.setdefault("asset", {}).setdefault("extras", {})["objectforge"] = {
        "schema_version": "1.0",
        "capability_id": "object-generation.procedural-detailed.v1",
        "construction_sha256": construction_hash,
        "external_model_generation_provider": False,
        "canonical_asset": not showcase,
        "showcase_asset": showcase,
    }
    root_index = node_by_name.get("LampRoot")
    if root_index is not None:
        doc["nodes"][root_index].setdefault("extras", {})["objectforge"] = {
            "semantic_type": "articulated_task_lamp",
            "physics_contract": "../behavior/physics.json",
            "semantic_contract": "../object/semantic-parts.json",
        }
    for joint_name, joint_id in [("LowerArmPivot", "base_hinge"), ("UpperArmPivot", "elbow_hinge"), ("ShadePivot", "shade_hinge")]:
        index = node_by_name.get(joint_name)
        if index is not None:
            constraint = next(item for item in physics["constraints"] if item["id"] == joint_id)
            doc["nodes"][index].setdefault("extras", {})["physics_joint"] = constraint

    semantic_lookup: dict[str, str] = {}
    for semantic_id, info in semantic["semantic_parts"].items():
        for node_name in info["nodes"]:
            semantic_lookup[node_name] = semantic_id
    for node in doc.get("nodes", []):
        name = node.get("name")
        if name in semantic_lookup:
            node.setdefault("extras", {})["semantic_part"] = semantic_lookup[name]

    doc["buffers"][0]["byteLength"] = len(binary)
    return pack_glb(doc, binary)
