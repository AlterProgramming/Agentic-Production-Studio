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
    if not doc.get("skins"): errors.append("missing skin")
    if not doc.get("animations"): errors.append("missing animation")
    render=[]; cages=[]; body=[]
    for mesh in doc.get("meshes",[]):
        extra=mesh.get("extras",{}); role=extra.get("topology_role")
        if extra.get("layer")=="embodied": body.append(mesh)
        if extra.get("garment_class") and role=="render_surface": render.append(mesh)
        if extra.get("garment_class") and role=="simulation_cage": cages.append(mesh)
        for primitive in mesh.get("primitives",[]):
            attrs=primitive.get("attributes",{})
            for required in ("POSITION","NORMAL","TEXCOORD_0","JOINTS_0","WEIGHTS_0"):
                if required not in attrs: errors.append(f"{mesh.get('name')} missing {required}")
            if "POSITION" in attrs:
                pos=accessor_array(doc,binary,attrs["POSITION"])
                if not np.isfinite(pos).all(): errors.append(f"{mesh.get('name')} non-finite positions")
            if extra.get("garment_class") and role=="render_surface" and "WEIGHTS_0" in attrs:
                weights=accessor_array(doc,binary,attrs["WEIGHTS_0"])
                if len(np.unique(np.round(weights,3),axis=0))<10: errors.append(f"{mesh.get('name')} weight field is too coarse")
    for mesh in render:
        extra=mesh["extras"]
        if extra.get("adaptive_density") is not True: errors.append(f"{mesh['name']} not adaptive")
        row_counts=extra.get("adaptive_row_counts",{})
        if not any(len(set(values))>1 for values in row_counts.values()): errors.append(f"{mesh['name']} has uniform row density")
        if extra.get("construction_reveal")!="uv_coverage_mask": errors.append(f"{mesh['name']} lacks coverage reveal")
    for mesh in cages:
        extra=mesh["extras"]
        if extra.get("quad_source") is not True or extra.get("triangulated_for_glb") is not True: errors.append(f"{mesh['name']} lacks quad-source boundary")
        seams=extra.get("seam_constraints",[])
        if not seams: errors.append(f"{mesh['name']} lacks seam constraints")
        for seam in seams:
            if seam.get("simulation_constraint") not in {"distance_pair","layered_contact","pin_pair","pinned_boundary"}: errors.append(f"{mesh['name']} seam constraint invalid")
            if seam.get("simulation_constraint")=="distance_pair" and not seam.get("ordered_vertex_pairs"): errors.append(f"{mesh['name']} seam pairs missing")
    if body:
        primitive=body[0]["primitives"][0]; material=doc["materials"][primitive["material"]]
        if material.get("extras",{}).get("material_class")!="plain_body": errors.append("body uses textile material")
        if material.get("normalTexture") or material.get("pbrMetallicRoughness",{}).get("baseColorTexture"): errors.append("body material contains weave textures")
    target_names={doc["nodes"][c["target"]["node"]].get("name") for a in doc.get("animations",[]) for c in a.get("channels",[])}
    if not any("Hem" in (n or "") for n in target_names): errors.append("animation has no independent cloth-joint target")
    if "Chest" not in target_names: errors.append("animation has no body driver")
    if system:
        if len(render)!=4 or len(cages)!=4: errors.append("system must contain four render garments and four cages")
        if len(doc.get("scenes",[]))<4: errors.append("system must retain cage verification scene")
        scene_names={s.get("name") for s in doc.get("scenes",[])}
        required={"Dressed_Character_And_Textile_Decor","Body_Only_Verification","Detached_Garment_Gallery","Simulation_Cages_And_Seams"}
        if not required.issubset(scene_names): errors.append(f"missing scenes: {sorted(required-scene_names)}")
        construction=doc.get("extras",{}).get("construction_animation",{})
        if construction.get("method")!="viewer_shader_uv_coverage_mask" or construction.get("topology_spawn") is not False: errors.append("construction animation boundary invalid")
    return {"path":str(path),"passed":not errors,"errors":errors,"mesh_count":len(doc.get("meshes",[])),"scene_count":len(doc.get("scenes",[])),"skin_count":len(doc.get("skins",[])),"animation_count":len(doc.get("animations",[])),"embedded_image_count":len(doc.get("images",[])),"render_garment_count":len(render),"simulation_cage_count":len(cages)}


def validate_package(root:Path)->dict:
    expected=["clothing-system.glb","tunic.glb","wrap-skirt.glb","mantle.glb","hanging-textile.glb"]
    results=[]
    for name in expected:
        path=root/name
        results.append({"path":str(path),"passed":False,"errors":["missing"]} if not path.exists() else validate_glb(path,system=name=="clothing-system.glb"))
    for viewer in (root/"viewer/index.html",root/"viewer/construction.html"):
        if not viewer.exists(): results.append({"path":str(viewer),"passed":False,"errors":["missing viewer"]})
    if (root/"viewer/construction.html").exists():
        text=(root/"viewer/construction.html").read_text()
        if "uReveal" not in text or "discard" not in text: results.append({"path":str(root/"viewer/construction.html"),"passed":False,"errors":["coverage shader missing"]})
    receipt={"schema_version":"2.0.0","kind":"garmentforge.validation-receipt","passed":all(r["passed"] for r in results),"results":results,"evidence_boundary":{"source":True,"local_rebuild":True,"glb_reopen":True,"seam_constraints":True,"cage_render_separation":True,"coverage_reveal_viewer":True,"continuum_cloth_solver":False,"deployed_runtime":False}}
    (root/"validation.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return receipt


def main()->int:
    p=argparse.ArgumentParser();p.add_argument("root",type=Path);args=p.parse_args();r=validate_package(args.root);print(json.dumps(r,indent=2));return 0 if r["passed"] else 1
if __name__=="__main__": raise SystemExit(main())
