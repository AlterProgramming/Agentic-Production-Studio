from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from .gltf import parse_glb

COMPONENT_DTYPE={5126:np.float32,5125:np.uint32,5123:np.uint16,5121:np.uint8}
WIDTH={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4,"MAT4":16}


def accessor_array(doc:dict[str,Any],binary:bytes,index:int)->np.ndarray:
    acc=doc["accessors"][index]; view=doc["bufferViews"][acc["bufferView"]]
    dtype=np.dtype(COMPONENT_DTYPE[acc["componentType"]]).newbyteorder("<")
    width=WIDTH[acc["type"]]; offset=view.get("byteOffset",0)+acc.get("byteOffset",0)
    return np.frombuffer(binary,dtype=dtype,count=acc["count"]*width,offset=offset).reshape((acc["count"],width))


def validate_glb(path:Path,system:bool=False)->dict:
    doc,binary=parse_glb(path.read_bytes()); errors=[]
    if not binary: errors.append("missing binary payload")
    if any(x.get("uri") for x in doc.get("images",[])): errors.append("external image URI present")
    if len(doc.get("images",[]))<2: errors.append("embedded fabric base and normal textures required")
    if not doc.get("skins"): errors.append("missing skin")
    if not doc.get("animations"): errors.append("missing animation")
    names={n.get("name") for n in doc.get("nodes",[])}
    cloth={n for n in names if n and "Hem" in n}
    if len(cloth)<2: errors.append("secondary cloth joints missing")
    garment_meshes=[]
    for mesh in doc.get("meshes",[]):
        extra=mesh.get("extras",{})
        if extra.get("garment_class"):
            garment_meshes.append(mesh)
            if extra.get("detachable") is not True: errors.append(f"{mesh.get('name')} not detachable")
            if not extra.get("panels") or not extra.get("seams"): errors.append(f"{mesh.get('name')} lacks panel/seam construction metadata")
        for primitive in mesh.get("primitives",[]):
            attrs=primitive.get("attributes",{})
            for required in ("POSITION","NORMAL","TEXCOORD_0","JOINTS_0","WEIGHTS_0"):
                if required not in attrs: errors.append(f"{mesh.get('name')} missing {required}")
            if "POSITION" in attrs:
                pos=accessor_array(doc,binary,attrs["POSITION"])
                if not np.isfinite(pos).all(): errors.append(f"{mesh.get('name')} non-finite positions")
                if len(pos)<500: errors.append(f"{mesh.get('name')} under-resolved ({len(pos)} vertices)")
    channels=[c for a in doc.get("animations",[]) for c in a.get("channels",[])]
    targeted={doc["nodes"][c["target"]["node"]].get("name") for c in channels}
    if not any("Hem" in (n or "") for n in targeted): errors.append("animation has no independent cloth-joint target")
    if not any(n in targeted for n in ("Chest","UpperArm_L","UpperArm_R")): errors.append("animation has no body driver")
    if system:
        if len(doc.get("scenes",[]))<3: errors.append("system GLB must retain dressed, body-only, and detached-gallery scenes")
        required={"Garment_Tunic","Garment_WrapSkirt","Garment_Mantle","Textile_HangingPanel","Layer_Embodied_Body"}
        if not required.issubset(names): errors.append(f"system missing nodes: {sorted(required-names)}")
        if len(garment_meshes)<4: errors.append("system must contain four textile assets")
        extras=doc.get("extras",{})
        checks=extras.get("verification",{})
        if not all(checks.get(k) is True for k in ("reopen","alternate_pose","alternate_garment_state","alternate_camera")): errors.append("reuse verification contract incomplete")
    return {"path":str(path),"passed":not errors,"errors":errors,"mesh_count":len(doc.get("meshes",[])),"scene_count":len(doc.get("scenes",[])),"skin_count":len(doc.get("skins",[])),"animation_count":len(doc.get("animations",[])),"embedded_image_count":len(doc.get("images",[])),"cloth_joint_count":len(cloth)}


def validate_package(root:Path)->dict:
    expected=["clothing-system.glb","tunic.glb","wrap-skirt.glb","mantle.glb","hanging-textile.glb"]
    results=[]
    for name in expected:
        path=root/name
        if not path.exists(): results.append({"path":str(path),"passed":False,"errors":["missing"]})
        else: results.append(validate_glb(path,system=name=="clothing-system.glb"))
    receipt={"schema_version":"1.0.0","kind":"garmentforge.validation-receipt","passed":all(r["passed"] for r in results),"results":results,
             "evidence_boundary":{"source":True,"local_rebuild":True,"glb_reopen":True,"external_viewer_upload":False,"deployed_runtime":False}}
    (root/"validation.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return receipt


def main()->int:
    p=argparse.ArgumentParser();p.add_argument("root",type=Path);args=p.parse_args();r=validate_package(args.root);print(json.dumps(r,indent=2));return 0 if r["passed"] else 1
if __name__=="__main__": raise SystemExit(main())
