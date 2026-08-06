from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from garmentforge.construction import build_package
from garmentforge.gltf import parse_glb
from garmentforge.validate import accessor_array, validate_package


def _build(tmp_path: Path):
    manifest = build_package(tmp_path)
    receipt = validate_package(tmp_path)
    assert receipt["passed"], receipt
    document, binary = parse_glb((tmp_path / "clothing-system.glb").read_bytes())
    return manifest, document, binary


def test_build_and_validate(tmp_path: Path):
    manifest, document, _ = _build(tmp_path)
    assert manifest["capability_id"] == "GarmentForge.clothing_construction.v2"
    assert len(manifest["detachable_assets"]) == 4
    assert [scene["name"] for scene in document["scenes"]] == [
        "Dressed_Character_And_Textile_Decor",
        "Body_Only_Verification",
        "Detached_Garment_Gallery",
        "Simulation_Cages_And_Seams",
    ]


def test_cages_adaptive_surfaces_seams_and_fit_are_separate(tmp_path: Path):
    _, document, binary = _build(tmp_path)
    render = [mesh for mesh in document["meshes"] if mesh.get("extras", {}).get("topology_role") == "render_surface"]
    cages = [mesh for mesh in document["meshes"] if mesh.get("extras", {}).get("topology_role") == "simulation_cage"]
    assert len(render) == 4
    assert len(cages) == 4
    assert all(mesh["extras"]["adaptive_density"] is True for mesh in render)
    assert all(any(len(set(counts)) > 1 for counts in mesh["extras"]["adaptive_row_counts"].values()) for mesh in render)
    assert all(mesh["extras"]["quad_source"] is True for mesh in cages)
    tunic_cage = next(mesh for mesh in cages if mesh["name"] == "Cage_Tunic")
    distance_seams = [seam for seam in tunic_cage["extras"]["seam_constraints"] if seam["simulation_constraint"] == "distance_pair"]
    assert distance_seams
    assert all(seam["ordered_vertex_pairs"] for seam in distance_seams)
    tunic = next(mesh for mesh in render if mesh["name"] == "Garment_Tunic")
    positions = accessor_array(document, binary, tunic["primitives"][0]["attributes"]["POSITION"])
    ranges = {item["name"]: item for item in tunic["extras"]["component_vertex_ranges"]}
    front = ranges["front"]
    back = ranges["back"]
    front_z = positions[front["vertex_start"]:front["vertex_start"] + front["vertex_count"], 2]
    back_z = positions[back["vertex_start"]:back["vertex_start"] + back["vertex_count"], 2]
    assert float(front_z.min()) > .238
    assert float(back_z.max()) < -.238
    assert tunic["extras"]["fit_clearance"]["validated"] is True


def test_body_material_is_not_textile(tmp_path: Path):
    _, document, _ = _build(tmp_path)
    body = next(mesh for mesh in document["meshes"] if mesh.get("extras", {}).get("layer") == "embodied")
    material = document["materials"][body["primitives"][0]["material"]]
    assert material["extras"]["material_class"] == "plain_body"
    assert "normalTexture" not in material
    assert "baseColorTexture" not in material["pbrMetallicRoughness"]


def test_render_weights_are_smooth_and_construction_reveal_is_coverage_based(tmp_path: Path):
    _, document, binary = _build(tmp_path)
    render = [mesh for mesh in document["meshes"] if mesh.get("extras", {}).get("topology_role") == "render_surface"]
    for mesh in render:
        primitive = mesh["primitives"][0]
        weights = accessor_array(document, binary, primitive["attributes"]["WEIGHTS_0"])
        assert len(np.unique(np.round(weights, 3), axis=0)) >= 10
        assert mesh["extras"]["construction_reveal"] == "uv_coverage_mask"
    construction = document["extras"]["construction_animation"]
    assert construction == {"method": "viewer_shader_uv_coverage_mask", "topology_spawn": False, "continuous_surface": True}
    viewer = (tmp_path / "viewer/construction.html").read_text()
    assert "uReveal" in viewer and "discard" in viewer
