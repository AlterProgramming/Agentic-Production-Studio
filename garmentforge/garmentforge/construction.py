from __future__ import annotations

import hashlib
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import trimesh
from PIL import Image

from .gltf import GLBBuilder, parse_glb
from .viewer import viewer_html


def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-9)


def _quat(axis: tuple[float, float, float], angle: float) -> list[float]:
    a = np.asarray(axis, dtype=float)
    a /= np.linalg.norm(a)
    s = math.sin(angle / 2.0)
    return [float(a[0] * s), float(a[1] * s), float(a[2] * s), float(math.cos(angle / 2.0))]


def _texture(color: tuple[int, int, int], weave: int, accent: tuple[int, int, int]) -> tuple[bytes, bytes]:
    size = 256
    y, x = np.mgrid[0:size, 0:size]
    warp = (np.sin(x * math.pi * 2 / weave) * 0.5 + 0.5)
    weft = (np.sin(y * math.pi * 2 / (weave + 3)) * 0.5 + 0.5)
    checker = ((x // (weave * 2) + y // (weave * 2)) % 2).astype(float)
    grain = 0.72 + 0.12 * warp + 0.10 * weft + 0.06 * checker
    rgb = np.asarray(color)[None, None, :] * grain[..., None]
    thread = (np.maximum(warp, weft) > 0.88)[..., None]
    rgb = np.where(thread, np.asarray(accent)[None, None, :] * 0.85 + rgb * 0.15, rgb)
    image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    base = io.BytesIO(); image.save(base, format="PNG", optimize=True)
    h = 0.5 + 0.22 * (warp - 0.5) + 0.18 * (weft - 0.5)
    gy, gx = np.gradient(h)
    normal = _normalize(np.stack([-gx * 2.5, -gy * 2.5, np.ones_like(gx)], axis=-1))
    normal = ((normal * 0.5 + 0.5) * 255).astype(np.uint8)
    nimg = Image.fromarray(normal, "RGB")
    norm = io.BytesIO(); nimg.save(norm, format="PNG", optimize=True)
    return base.getvalue(), norm.getvalue()


@dataclass
class MeshData:
    name: str
    positions: np.ndarray
    normals: np.ndarray
    uv: np.ndarray
    indices: np.ndarray
    joints: np.ndarray
    weights: np.ndarray
    material: int
    extras: dict

    @property
    def triangle_count(self) -> int:
        return int(len(self.indices) // 3)


def _grid_surface(nx: int, ny: int, fn: Callable[[float, float], tuple[float, float, float]], uv_scale=(1.0, 1.0)) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    vertices = []
    uv = []
    for j in range(ny + 1):
        v = j / ny
        for i in range(nx + 1):
            u = i / nx
            vertices.append(fn(u, v))
            uv.append((u * uv_scale[0], v * uv_scale[1]))
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            b = a + 1
            c = a + nx + 1
            d = c + 1
            faces.extend((a, c, b, b, c, d))
    pos = np.asarray(vertices, dtype=np.float32)
    idx = np.asarray(faces, dtype=np.uint32)
    tri = pos[idx.reshape(-1, 3)]
    fnorm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    normals = np.zeros_like(pos)
    for k, face in enumerate(idx.reshape(-1, 3)):
        normals[face] += fnorm[k]
    normals = _normalize(normals).astype(np.float32)
    return pos, normals, np.asarray(uv, dtype=np.float32), idx


def _combine(name: str, parts: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]], material: int, extras: dict) -> MeshData:
    positions=[]; normals=[]; uv=[]; indices=[]; offset=0
    for p,n,t,i in parts:
        positions.append(p); normals.append(n); uv.append(t); indices.append(i + offset); offset += len(p)
    pos=np.concatenate(positions); nor=np.concatenate(normals); tex=np.concatenate(uv); ind=np.concatenate(indices)
    joints=np.zeros((len(pos),4),dtype=np.uint16); weights=np.zeros((len(pos),4),dtype=np.float32)
    return MeshData(name,pos,nor,tex,ind,joints,weights,material,extras)


JOINT_NAMES = [
    "RigRoot", "Hips", "Spine", "Chest", "Neck", "Head",
    "UpperArm_L", "LowerArm_L", "Hand_L", "UpperArm_R", "LowerArm_R", "Hand_R",
    "UpperLeg_L", "LowerLeg_L", "UpperLeg_R", "LowerLeg_R",
    "TunicHem_L", "TunicHem_C", "TunicHem_R", "SkirtHem_L", "SkirtHem_R",
    "CapeHem_L", "CapeHem_C", "CapeHem_R"
]
JOINT = {n:i for i,n in enumerate(JOINT_NAMES)}
JOINT_TRANSLATIONS = {
    "RigRoot": (0,0,0), "Hips": (0,0.95,0), "Spine": (0,0.28,0), "Chest": (0,0.32,0), "Neck": (0,0.28,0), "Head": (0,0.22,0),
    "UpperArm_L": (0.36,0.22,0), "LowerArm_L": (0.38,0,0), "Hand_L": (0.34,0,0),
    "UpperArm_R": (-0.36,0.22,0), "LowerArm_R": (-0.38,0,0), "Hand_R": (-0.34,0,0),
    "UpperLeg_L": (0.18,-0.12,0), "LowerLeg_L": (0,-0.55,0), "UpperLeg_R": (-0.18,-0.12,0), "LowerLeg_R": (0,-0.55,0),
    "TunicHem_L": (0.32,-0.56,0), "TunicHem_C": (0,-0.58,0.02), "TunicHem_R": (-0.32,-0.56,0),
    "SkirtHem_L": (0.34,-0.78,0), "SkirtHem_R": (-0.34,-0.78,0),
    "CapeHem_L": (0.46,-0.78,-0.10), "CapeHem_C": (0,-0.90,-0.14), "CapeHem_R": (-0.46,-0.78,-0.10),
}
PARENT = {
    "RigRoot": None, "Hips":"RigRoot", "Spine":"Hips", "Chest":"Spine", "Neck":"Chest", "Head":"Neck",
    "UpperArm_L":"Chest", "LowerArm_L":"UpperArm_L", "Hand_L":"LowerArm_L",
    "UpperArm_R":"Chest", "LowerArm_R":"UpperArm_R", "Hand_R":"LowerArm_R",
    "UpperLeg_L":"Hips", "LowerLeg_L":"UpperLeg_L", "UpperLeg_R":"Hips", "LowerLeg_R":"UpperLeg_R",
    "TunicHem_L":"Chest", "TunicHem_C":"Chest", "TunicHem_R":"Chest",
    "SkirtHem_L":"Hips", "SkirtHem_R":"Hips", "CapeHem_L":"Chest", "CapeHem_C":"Chest", "CapeHem_R":"Chest",
}


def _global_joint_matrices() -> list[np.ndarray]:
    globals_: dict[str,np.ndarray] = {}
    for name in JOINT_NAMES:
        local=np.eye(4,dtype=np.float32); local[:3,3]=JOINT_TRANSLATIONS[name]
        parent=PARENT[name]
        globals_[name] = local if parent is None else globals_[parent] @ local
    return [globals_[n] for n in JOINT_NAMES]


def _set_weight(mesh: MeshData, selector: np.ndarray, joint_ids: list[int], values: list[float]) -> None:
    ids=np.asarray(joint_ids,dtype=np.uint16); vals=np.asarray(values,dtype=np.float32); vals/=vals.sum()
    mesh.joints[selector,:len(ids)] = ids
    mesh.weights[selector,:len(vals)] = vals


def make_tunic(material: int) -> MeshData:
    parts=[]
    for side in (1,-1):
        def panel(u,v,side=side):
            y=1.68-v*0.82
            half=0.31+0.10*v+0.035*math.sin(v*math.pi)
            x=(u*2-1)*half
            fold=0.018*math.sin(u*math.pi*8)*(0.35+0.65*v)
            z=side*(0.205+0.015*math.cos((u-.5)*math.pi*2))+fold
            return x,y,z
        p,n,t,i=_grid_surface(30,28,panel,(2.5,2.2))
        if side < 0:
            i=i.reshape(-1,3)[:,::-1].reshape(-1)
            n=-n
        parts.append((p,n,t,i))
    for arm_side in (1,-1):
        def sleeve(u,v,s=arm_side):
            theta=(u-.5)*math.pi*1.65
            length=v*0.62
            x=s*(0.29+length)
            y=1.58-0.08*length+0.14*math.cos(theta)
            z=0.13*math.sin(theta)*(1-0.2*v)
            return x,y,z
        parts.append(_grid_surface(20,20,sleeve,(1.5,2.0)))
    m=_combine("Garment_Tunic",parts,material,{
        "asset_id":"garmentforge.tunic.v1","garment_class":"upper_body","detachable":True,
        "panels":["front","back","sleeve_left","sleeve_right"],"seams":["shoulder","side","sleeve","hem","neckline"],
        "fit_profile":"relaxed","collision_zones":["torso","shoulders","upper_arms"],
        "fabric":{"fiber":"cotton-linen","areal_density_g_m2":185,"stretch_warp":0.035,"stretch_weft":0.055,"bending":"medium-soft"},
        "provenance":{"construction":"first_party_procedural","external_finished_model":False}
    })
    y=m.positions[:,1]; x=m.positions[:,0]
    top=y>1.35; hem=y<1.08; sleeves=np.abs(x)>.42
    _set_weight(m,top & ~sleeves,[JOINT["Chest"],JOINT["Spine"]],[.8,.2])
    _set_weight(m,sleeves & (x>0),[JOINT["UpperArm_L"],JOINT["LowerArm_L"]],[.78,.22])
    _set_weight(m,sleeves & (x<0),[JOINT["UpperArm_R"],JOINT["LowerArm_R"]],[.78,.22])
    _set_weight(m,hem & (x>.12),[JOINT["Chest"],JOINT["TunicHem_L"]],[.45,.55])
    _set_weight(m,hem & (x<-.12),[JOINT["Chest"],JOINT["TunicHem_R"]],[.45,.55])
    _set_weight(m,hem & (np.abs(x)<=.12),[JOINT["Chest"],JOINT["TunicHem_C"]],[.42,.58])
    unset=m.weights.sum(axis=1)==0; _set_weight(m,unset,[JOINT["Chest"],JOINT["Spine"]],[.7,.3])
    return m


def make_skirt(material: int) -> MeshData:
    def surf(u,v):
        theta=-math.pi+u*(math.pi*2.18)
        y=1.00-v*0.78
        radius=0.32+v*0.18+0.018*math.sin(theta*10)*(v**1.2)
        return radius*math.sin(theta),y,radius*math.cos(theta)
    p,n,t,i=_grid_surface(54,30,surf,(4.0,2.5))
    m=_combine("Garment_WrapSkirt",[(p,n,t,i)],material,{
        "asset_id":"garmentforge.wrap-skirt.v1","garment_class":"lower_body","detachable":True,
        "panels":["wrap_panel"],"seams":["waistband","overlap_edge","hem"],"closures":["waist_tie"],
        "fit_profile":"wrapped","collision_zones":["hips","upper_legs"],
        "fabric":{"fiber":"woven-cotton","areal_density_g_m2":225,"stretch_warp":0.025,"stretch_weft":0.04,"bending":"medium"},
        "provenance":{"construction":"first_party_procedural","external_finished_model":False}
    })
    y=m.positions[:,1]; x=m.positions[:,0]
    waist=y>.78; hem=y<.48
    _set_weight(m,waist,[JOINT["Hips"]],[1])
    _set_weight(m,hem & (x>=0),[JOINT["Hips"],JOINT["SkirtHem_L"]],[.32,.68])
    _set_weight(m,hem & (x<0),[JOINT["Hips"],JOINT["SkirtHem_R"]],[.32,.68])
    unset=m.weights.sum(axis=1)==0; _set_weight(m,unset,[JOINT["Hips"],JOINT["Spine"]],[.85,.15])
    return m


def make_mantle(material: int) -> MeshData:
    def surf(u,v):
        y=1.68-v*1.05
        half=.34+v*.48
        x=(u*2-1)*half
        fold=.055*math.sin(u*math.pi*10)*(0.15+v*.85)
        z=-.235-v*.16-fold
        return x,y,z
    p,n,t,i=_grid_surface(44,34,surf,(3.8,3.0))
    i=i.reshape(-1,3)[:,::-1].reshape(-1); n=-n
    m=_combine("Garment_Mantle",[(p,n,t,i)],material,{
        "asset_id":"garmentforge.mantle.v1","garment_class":"outer_layer_and_decor","detachable":True,"decor_reusable":True,
        "panels":["single_draped_panel"],"seams":["neck_binding","edge_finish","hem"],"closures":["shoulder_clasp"],
        "fit_profile":"draped","collision_zones":["shoulders","back","arms"],
        "fabric":{"fiber":"wool-silk","areal_density_g_m2":260,"stretch_warp":0.02,"stretch_weft":0.03,"bending":"soft-heavy"},
        "provenance":{"construction":"first_party_procedural","external_finished_model":False}
    })
    y=m.positions[:,1]; x=m.positions[:,0]
    shoulder=y>1.48; hem=y<.92
    _set_weight(m,shoulder,[JOINT["Chest"]],[1])
    _set_weight(m,hem & (x>.18),[JOINT["Chest"],JOINT["CapeHem_L"]],[.22,.78])
    _set_weight(m,hem & (x<-.18),[JOINT["Chest"],JOINT["CapeHem_R"]],[.22,.78])
    _set_weight(m,hem & (np.abs(x)<=.18),[JOINT["Chest"],JOINT["CapeHem_C"]],[.20,.80])
    unset=m.weights.sum(axis=1)==0; _set_weight(m,unset,[JOINT["Chest"],JOINT["Spine"]],[.8,.2])
    return m


def make_hanging_textile(material: int) -> MeshData:
    def surf(u,v):
        x=(u*2-1)*.58
        y=1.62-v*1.28
        z=-.82+0.035*math.sin(u*math.pi*12)*(0.2+0.8*v)
        return x,y,z
    p,n,t,i=_grid_surface(48,42,surf,(4.0,4.0))
    m=_combine("Textile_HangingPanel",[(p,n,t,i)],material,{
        "asset_id":"garmentforge.hanging-textile.v1","garment_class":"scene_textile_decor","detachable":True,"decor_reusable":True,
        "panels":["hanging_panel"],"seams":["top_sleeve","edge_finish","weighted_hem"],
        "fabric":{"fiber":"linen","areal_density_g_m2":210,"bending":"soft"},
        "provenance":{"construction":"first_party_procedural","external_finished_model":False}
    })
    y=m.positions[:,1]
    _set_weight(m,y>1.45,[JOINT["Chest"]],[1])
    _set_weight(m,y<.60,[JOINT["Chest"],JOINT["CapeHem_C"]],[.20,.80])
    unset=m.weights.sum(axis=1)==0; _set_weight(m,unset,[JOINT["Chest"],JOINT["CapeHem_C"]],[.65,.35])
    return m


def make_body(material: int) -> MeshData:
    meshes=[]
    def add_ellipsoid(center,scale,sub=2):
        s=trimesh.creation.icosphere(subdivisions=sub,radius=1.0)
        s.apply_scale(scale); s.apply_translation(center); meshes.append(s)
    add_ellipsoid((0,1.35,0),(0.34,.48,.23),3)
    add_ellipsoid((0,1.92,0),(0.19,.24,.19),2)
    add_ellipsoid((0,0.88,0),(.29,.22,.22),2)
    for side in (-1,1):
        add_ellipsoid((side*.53,1.49,0),(.28,.12,.12),2)
        add_ellipsoid((side*.91,1.43,0),(.26,.10,.10),2)
        add_ellipsoid((side*.20,.54,0),(.13,.40,.14),2)
        add_ellipsoid((side*.20,-.05,0),(.12,.35,.13),2)
    s=trimesh.util.concatenate(meshes)
    p=np.asarray(s.vertices,dtype=np.float32); n=np.asarray(s.vertex_normals,dtype=np.float32); i=np.asarray(s.faces.reshape(-1),dtype=np.uint32)
    uv=np.stack([(np.arctan2(p[:,2],p[:,0])/(2*math.pi)+.5), np.clip((p[:,1]+.45)/2.65,0,1)],axis=1).astype(np.float32)
    m=MeshData("Embodied_Mannequin",p,n,uv,i,np.zeros((len(p),4),np.uint16),np.zeros((len(p),4),np.float32),material,{
        "asset_id":"avatarforge.neutral-mannequin.v1","layer":"embodied","garment_ownership":False,"provenance":{"construction":"first_party_procedural"}
    })
    y=p[:,1]; x=p[:,0]
    _set_weight(m,(y>1.68)&(np.abs(x)<.35),[JOINT["Head"],JOINT["Neck"]],[.8,.2])
    _set_weight(m,(y>1.30)&(np.abs(x)<.42),[JOINT["Chest"],JOINT["Spine"]],[.75,.25])
    _set_weight(m,(y<=1.30)&(y>.70)&(np.abs(x)<.42),[JOINT["Hips"],JOINT["Spine"]],[.75,.25])
    _set_weight(m,(x>.38)&(x<.78),[JOINT["UpperArm_L"],JOINT["Chest"]],[.85,.15])
    _set_weight(m,x>=.78,[JOINT["LowerArm_L"],JOINT["UpperArm_L"]],[.8,.2])
    _set_weight(m,(x<-.38)&(x>-.78),[JOINT["UpperArm_R"],JOINT["Chest"]],[.85,.15])
    _set_weight(m,x<=-.78,[JOINT["LowerArm_R"],JOINT["UpperArm_R"]],[.8,.2])
    _set_weight(m,(y<=.70)&(x>=0),[JOINT["UpperLeg_L"],JOINT["LowerLeg_L"]],[.7,.3])
    _set_weight(m,(y<=.70)&(x<0),[JOINT["UpperLeg_R"],JOINT["LowerLeg_R"]],[.7,.3])
    unset=m.weights.sum(axis=1)==0; _set_weight(m,unset,[JOINT["Hips"]],[1])
    return m


class GarmentSystemBuilder:
    capability_id="GarmentForge.clothing_construction.v1"

    def __init__(self):
        self.builder=GLBBuilder()
        self.materials={}
        self.meshes={}
        self.node_indices={}

    def add_materials(self):
        specs={
            "body":((164,121,96),9,(196,154,123),.78,[.08,.05,.04]),
            "tunic":((52,93,116),8,(108,157,178),.68,[.16,.22,.26]),
            "skirt":((145,89,53),7,(205,151,91),.76,[.25,.15,.08]),
            "mantle":((84,45,92),10,(151,92,161),.70,[.22,.10,.25]),
            "decor":((180,154,92),6,(230,207,138),.74,[.26,.22,.12]),
        }
        for name,(color,weave,accent,rough,sheen) in specs.items():
            base,normal=_texture(color,weave,accent)
            bi=self.builder.add_image(base,f"{name}_weave_base")
            ni=self.builder.add_image(normal,f"{name}_weave_normal")
            bt=self.builder.add_texture(bi); nt=self.builder.add_texture(ni)
            self.materials[name]=self.builder.add_material(f"Fabric_{name.title()}",bt,nt,[1,1,1,1],rough,sheen)

    def add_skeleton(self):
        doc=self.builder.document
        for name in JOINT_NAMES:
            node={"name":name,"translation":list(JOINT_TRANSLATIONS[name]),"extras":{"semantic_role":"cloth_secondary_joint" if "Hem" in name else "humanoid_joint"}}
            doc["nodes"].append(node); self.node_indices[name]=len(doc["nodes"])-1
        for name in JOINT_NAMES:
            parent=PARENT[name]
            if parent:
                doc["nodes"][self.node_indices[parent]].setdefault("children",[]).append(self.node_indices[name])
        globals_=_global_joint_matrices()
        ibm=np.asarray([np.linalg.inv(m).T for m in globals_],dtype=np.float32)
        ibm_acc=self.builder.accessor(ibm)
        doc["skins"].append({"name":"GarmentForgeHumanoidSkin","inverseBindMatrices":ibm_acc,"skeleton":self.node_indices["RigRoot"],"joints":[self.node_indices[n] for n in JOINT_NAMES],"extras":{"standard":"glTF skin","secondary_cloth_joints":[n for n in JOINT_NAMES if "Hem" in n]}})

    def add_mesh(self, mesh: MeshData) -> int:
        attrs={
            "POSITION":self.builder.accessor(mesh.positions,34962),
            "NORMAL":self.builder.accessor(mesh.normals,34962),
            "TEXCOORD_0":self.builder.accessor(mesh.uv,34962),
            "JOINTS_0":self.builder.accessor(mesh.joints,34962),
            "WEIGHTS_0":self.builder.accessor(mesh.weights,34962),
        }
        index=self.builder.accessor(mesh.indices,34963)
        self.builder.document["meshes"].append({"name":mesh.name,"primitives":[{"attributes":attrs,"indices":index,"material":mesh.material}],"extras":mesh.extras | {"vertex_count":len(mesh.positions),"triangle_count":mesh.triangle_count}})
        mi=len(self.builder.document["meshes"])-1
        self.meshes[mesh.name]=(mi,mesh)
        return mi

    def add_animation(self):
        times=np.asarray([0,1.0,2.2,3.4,4.6,6.0],dtype=np.float32)
        time_acc=self.builder.accessor(times)
        channels=[]; samplers=[]
        tracks={
            "Chest":[_quat((0,0,1),a) for a in (0,.04,-.055,.06,-.03,0)],
            "UpperArm_L":[_quat((0,0,1),a) for a in (0,-.15,-.52,-.30,-.08,0)],
            "UpperArm_R":[_quat((0,0,1),a) for a in (0,.08,.32,.18,.04,0)],
            "TunicHem_L":[_quat((1,0,0),a) for a in (0,.04,.16,-.12,.07,0)],
            "TunicHem_C":[_quat((1,0,0),a) for a in (0,.02,.10,-.08,.05,0)],
            "TunicHem_R":[_quat((1,0,0),a) for a in (0,-.03,-.13,.11,-.06,0)],
            "SkirtHem_L":[_quat((0,0,1),a) for a in (0,.05,.18,-.14,.09,0)],
            "SkirtHem_R":[_quat((0,0,1),a) for a in (0,-.04,-.16,.12,-.08,0)],
            "CapeHem_L":[_quat((1,0,0),a) for a in (0,.08,.26,-.20,.11,0)],
            "CapeHem_C":[_quat((1,0,0),a) for a in (0,.06,.21,-.17,.10,0)],
            "CapeHem_R":[_quat((1,0,0),a) for a in (0,.04,.18,-.15,.08,0)],
        }
        for name,values in tracks.items():
            out=self.builder.accessor(np.asarray(values,dtype=np.float32))
            samplers.append({"input":time_acc,"output":out,"interpolation":"LINEAR"})
            channels.append({"sampler":len(samplers)-1,"target":{"node":self.node_indices[name],"path":"rotation"},"extras":{"motion_class":"independent_secondary_cloth" if "Hem" in name else "body_driver"}})
        self.builder.document["animations"].append({"name":"body_motion_with_secondary_textile_response","samplers":samplers,"channels":channels,"extras":{"duration_seconds":6.0,"cloth_response":"authored spring-bone approximation","full_cloth_solver":False}})

    def build(self, include_body=True, selected: tuple[str,...] = ("Garment_Tunic","Garment_WrapSkirt","Garment_Mantle","Textile_HangingPanel"), multi_scene=True) -> bytes:
        self.add_materials(); self.add_skeleton()
        body=make_body(self.materials["body"])
        all_meshes={
            "Embodied_Mannequin":body,
            "Garment_Tunic":make_tunic(self.materials["tunic"]),
            "Garment_WrapSkirt":make_skirt(self.materials["skirt"]),
            "Garment_Mantle":make_mantle(self.materials["mantle"]),
            "Textile_HangingPanel":make_hanging_textile(self.materials["decor"]),
        }
        for name,mesh in all_meshes.items():
            if name=="Embodied_Mannequin" and not include_body: continue
            if name!="Embodied_Mannequin" and name not in selected: continue
            self.add_mesh(mesh)
        doc=self.builder.document
        active_nodes=[]
        if include_body:
            mi,_=self.meshes["Embodied_Mannequin"]
            doc["nodes"].append({"name":"Layer_Embodied_Body","mesh":mi,"skin":0,"extras":{"layer":"embodied","detachable":False}}); active_nodes.append(len(doc["nodes"])-1)
        for name in selected:
            mi,mesh=self.meshes[name]
            doc["nodes"].append({"name":name,"mesh":mi,"skin":0,"extras":{"layer":"artifact","asset_id":mesh.extras["asset_id"],"detachable":True,"default_state":"worn" if not name.startswith("Textile") else "decor"}})
            active_nodes.append(len(doc["nodes"])-1)
        self.add_animation()
        base=[self.node_indices["RigRoot"]]+active_nodes
        doc["scenes"].append({"name":"Dressed_Character_And_Textile_Decor","nodes":base,"extras":{"garment_state":"assembled","supports_remove_replace":True}})
        if multi_scene and include_body:
            body_node=active_nodes[0]
            doc["scenes"].append({"name":"Body_Only_Verification","nodes":[self.node_indices["RigRoot"],body_node],"extras":{"garment_state":"removed"}})
            gallery=[]
            for k,name in enumerate(selected):
                mi,mesh=self.meshes[name]
                doc["nodes"].append({"name":f"Gallery_{name}","mesh":mi,"translation":[(k-1.5)*1.5,0,0],"extras":{"layer":"artifact_gallery","asset_id":mesh.extras["asset_id"],"state":"detached"}})
                gallery.append(len(doc["nodes"])-1)
            doc["scenes"].append({"name":"Detached_Garment_Gallery","nodes":gallery,"extras":{"garment_state":"detached_and_manipulable"}})
        doc["extras"]={
            "capability_id":self.capability_id,
            "contract":"body and textiles remain separately owned and reusable",
            "interaction":{"attachments":["shoulders","waist","back"],"collision_zones":["torso","arms","hips","legs"],"solver":"skinning plus bounded secondary cloth joints"},
            "verification":{"reopen":True,"alternate_pose":True,"alternate_garment_state":True,"alternate_camera":True},
            "truth_boundary":"This GLB demonstrates retained skinned garments and secondary textile motion. It does not claim continuum cloth simulation or tailoring-grade pattern accuracy."
        }
        return self.builder.finish()


def build_package(output: Path) -> dict:
    output.mkdir(parents=True,exist_ok=True)
    assets={
        "clothing-system.glb":GarmentSystemBuilder().build(),
        "tunic.glb":GarmentSystemBuilder().build(include_body=False,selected=("Garment_Tunic",),multi_scene=False),
        "wrap-skirt.glb":GarmentSystemBuilder().build(include_body=False,selected=("Garment_WrapSkirt",),multi_scene=False),
        "mantle.glb":GarmentSystemBuilder().build(include_body=False,selected=("Garment_Mantle",),multi_scene=False),
        "hanging-textile.glb":GarmentSystemBuilder().build(include_body=False,selected=("Textile_HangingPanel",),multi_scene=False),
    }
    for name,data in assets.items(): (output/name).write_bytes(data)
    inventory=[]
    for name,data in assets.items():
        doc,_=parse_glb(data)
        inventory.append({"path":name,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),"mesh_count":len(doc.get("meshes",[])),"animation_count":len(doc.get("animations",[])),"scene_count":len(doc.get("scenes",[]))})
    viewer_dir=output/"viewer"; viewer_dir.mkdir(exist_ok=True); viewer_path=viewer_dir/"index.html"; viewer_path.write_text(viewer_html(),encoding="utf-8")
    inventory.append({"path":"viewer/index.html","bytes":viewer_path.stat().st_size,"sha256":hashlib.sha256(viewer_path.read_bytes()).hexdigest(),"kind":"inspection_viewer"})
    manifest={
        "schema_version":"1.0.0","kind":"garmentforge.delivery-manifest","capability_id":GarmentSystemBuilder.capability_id,
        "canonical_scene":"clothing-system.glb","detachable_assets":["tunic.glb","wrap-skirt.glb","mantle.glb","hanging-textile.glb"],
        "file_format":"glTF 2.0 binary (.glb)","external_finished_model_provider":False,
        "physics_boundary":{"implemented":"skinning, attachment ownership, collision-zone metadata, secondary cloth-joint animation","not_claimed":"continuum cloth simulation, manufacturing-ready patterns"},
        "files":inventory,
    }
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return manifest
