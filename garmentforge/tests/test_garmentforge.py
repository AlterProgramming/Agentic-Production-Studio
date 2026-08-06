from pathlib import Path
import json
from garmentforge.construction import build_package
from garmentforge.validate import validate_package
from garmentforge.gltf import parse_glb

def test_build_and_validate(tmp_path:Path):
    manifest=build_package(tmp_path)
    receipt=validate_package(tmp_path)
    assert receipt["passed"], receipt
    assert len(manifest["detachable_assets"])==4

def test_system_is_re_dressable(tmp_path:Path):
    build_package(tmp_path)
    doc,_=parse_glb((tmp_path/"clothing-system.glb").read_bytes())
    assert [s["name"] for s in doc["scenes"]]==["Dressed_Character_And_Textile_Decor","Body_Only_Verification","Detached_Garment_Gallery"]
    names={n.get("name") for n in doc["nodes"]}
    assert {"Garment_Tunic","Garment_WrapSkirt","Garment_Mantle","Textile_HangingPanel"}<names

def test_textiles_are_not_body_mesh(tmp_path:Path):
    build_package(tmp_path)
    doc,_=parse_glb((tmp_path/"clothing-system.glb").read_bytes())
    garment_ids={m["extras"]["asset_id"] for m in doc["meshes"] if m.get("extras",{}).get("garment_class")}
    assert len(garment_ids)==4
    body=[m for m in doc["meshes"] if m.get("extras",{}).get("layer")=="embodied"]
    assert len(body)==1 and body[0]["extras"]["garment_ownership"] is False

def test_secondary_cloth_motion_is_explicit(tmp_path:Path):
    build_package(tmp_path)
    doc,_=parse_glb((tmp_path/"clothing-system.glb").read_bytes())
    targets={doc["nodes"][c["target"]["node"]]["name"] for c in doc["animations"][0]["channels"]}
    assert "Chest" in targets
    assert {"TunicHem_L","SkirtHem_L","CapeHem_C"}<targets
