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
from PIL import Image, ImageFilter

from .gltf import GLBBuilder, parse_glb
from .viewer import construction_viewer_html, viewer_html


def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-9)


def _smoothstep(edge0: float, edge1: float, x: np.ndarray | float) -> np.ndarray:
    t = np.clip((np.asarray(x) - edge0) / max(edge1 - edge0, 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _quat(axis: tuple[float, float, float], angle: float) -> list[float]:
    a = np.asarray(axis, dtype=float)
    a /= np.linalg.norm(a)
    s = math.sin(angle / 2.0)
    return [float(a[0] * s), float(a[1] * s), float(a[2] * s), float(math.cos(angle / 2.0))]


def _fabric_maps(color: tuple[int, int, int], weave: int, accent: tuple[int, int, int], seed: int) -> tuple[bytes, bytes, bytes]:
    size = 256
    y, x = np.mgrid[0:size, 0:size]
    rng = np.random.default_rng(seed)
    macro_small = rng.normal(0, 1, (32, 32))
    macro = Image.fromarray(np.uint8(np.clip((macro_small - macro_small.min()) / np.ptp(macro_small) * 255, 0, 255)))
    macro = macro.resize((size, size), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(7))
    macro_arr = np.asarray(macro, dtype=np.float32) / 255.0
    warp = np.sin((x / weave) * math.pi * 2)
    weft = np.sin((y / (weave + 3)) * math.pi * 2)
    herring = np.sin(((x + (y % (weave * 4)) * 0.32) / (weave * 1.4)) * math.pi * 2)
    grain = 0.76 + 0.06 * warp + 0.05 * weft + 0.035 * herring + 0.10 * (macro_arr - 0.5)
    seam_shadow = 1.0 - 0.04 * np.exp(-((x - size * 0.5) / 3.5) ** 2)
    rgb = np.asarray(color, dtype=np.float32)[None, None, :] * grain[..., None] * seam_shadow[..., None]
    highlights = (warp + weft > 1.55)[..., None]
    rgb = np.where(highlights, np.asarray(accent)[None, None, :] * 0.34 + rgb * 0.66, rgb)
    image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    base = io.BytesIO(); image.save(base, format="PNG", optimize=True)

    height = 0.5 + 0.08 * warp + 0.065 * weft + 0.03 * herring + 0.08 * (macro_arr - 0.5)
    gy, gx = np.gradient(height)
    normal = _normalize(np.stack([-gx * 2.2, -gy * 2.2, np.ones_like(gx)], axis=-1))
    normal = ((normal * 0.5 + 0.5) * 255).astype(np.uint8)
    nimg = Image.fromarray(normal, "RGB")
    norm = io.BytesIO(); nimg.save(norm, format="PNG", optimize=True)

    rough = np.clip(0.62 + 0.18 * macro_arr + 0.06 * np.abs(warp) - 0.04 * np.abs(weft), 0, 1)
    mr = np.zeros((size, size, 3), dtype=np.uint8)
    mr[..., 1] = np.uint8(rough * 255)
    rimg = Image.fromarray(mr, "RGB")
    rbuf = io.BytesIO(); rimg.save(rbuf, format="PNG", optimize=True)
    return base.getvalue(), norm.getvalue(), rbuf.getvalue()


@dataclass
class SurfacePart:
    name: str
    positions: np.ndarray
    normals: np.ndarray
    uv: np.ndarray
    indices: np.ndarray
    rows: list[list[int]]
    boundaries: dict[str, list[int]]
    source_quad_count: int
    adaptive_row_counts: list[int]


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


def _surface_normals(positions: np.ndarray, indices: np.ndarray) -> np.ndarray:
    tri = positions[indices.reshape(-1, 3)]
    fnorm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    normals = np.zeros_like(positions)
    for k, face in enumerate(indices.reshape(-1, 3)):
        normals[face] += fnorm[k]
    return _normalize(normals).astype(np.float32)


def _connect_rows(rows: list[list[int]], u_rows: list[np.ndarray]) -> np.ndarray:
    faces: list[int] = []
    for row_index in range(len(rows) - 1):
        a = rows[row_index]
        b = rows[row_index + 1]
        ua = u_rows[row_index]
        ub = u_rows[row_index + 1]
        i = j = 0
        while i < len(a) - 1 or j < len(b) - 1:
            next_a = ua[i + 1] if i < len(a) - 1 else math.inf
            next_b = ub[j + 1] if j < len(b) - 1 else math.inf
            if abs(next_a - next_b) < 1e-8:
                faces.extend((a[i], b[j], a[i + 1], a[i + 1], b[j], b[j + 1]))
                i += 1; j += 1
            elif next_a < next_b:
                faces.extend((a[i], b[j], a[i + 1]))
                i += 1
            else:
                faces.extend((a[i], b[j], b[j + 1]))
                j += 1
    return np.asarray(faces, dtype=np.uint32)


def _adaptive_surface(name: str, v_samples: np.ndarray, row_counts: list[int], fn: Callable[[float, float], tuple[float, float, float]], uv_scale=(1.0, 1.0), reverse=False) -> SurfacePart:
    if len(v_samples) != len(row_counts):
        raise ValueError("v_samples and row_counts must match")
    positions: list[tuple[float, float, float]] = []
    texcoords: list[tuple[float, float]] = []
    rows: list[list[int]] = []
    u_rows: list[np.ndarray] = []
    for v, count in zip(v_samples, row_counts):
        u_values = np.linspace(0.0, 1.0, count)
        row = []
        for u in u_values:
            row.append(len(positions))
            positions.append(fn(float(u), float(v)))
            texcoords.append((float(u) * uv_scale[0], float(v) * uv_scale[1]))
        rows.append(row)
        u_rows.append(u_values)
    pos = np.asarray(positions, dtype=np.float32)
    uv = np.asarray(texcoords, dtype=np.float32)
    idx = _connect_rows(rows, u_rows)
    if reverse:
        idx = idx.reshape(-1, 3)[:, ::-1].reshape(-1)
    normals = _surface_normals(pos, idx)
    boundaries = {
        "top": list(rows[0]),
        "bottom": list(rows[-1]),
        "left": [row[0] for row in rows],
        "right": [row[-1] for row in rows],
    }
    return SurfacePart(name, pos, normals, uv, idx, rows, boundaries, sum((len(rows[i]) - 1) for i in range(len(rows) - 1)), list(row_counts))


def _uniform_surface(name: str, nx: int, ny: int, fn: Callable[[float, float], tuple[float, float, float]], uv_scale=(1.0, 1.0), reverse=False) -> SurfacePart:
    return _adaptive_surface(name, np.linspace(0.0, 1.0, ny + 1), [nx + 1] * (ny + 1), fn, uv_scale, reverse)


def _combine_parts(name: str, parts: list[SurfacePart], material: int, extras: dict) -> MeshData:
    positions=[]; normals=[]; uv=[]; indices=[]; offset=0
    component_ranges=[]; boundaries={}; row_counts={}; quad_count=0
    for part in parts:
        start=offset
        positions.append(part.positions); normals.append(part.normals); uv.append(part.uv); indices.append(part.indices + offset)
        offset += len(part.positions)
        component_ranges.append({"name":part.name,"vertex_start":start,"vertex_count":len(part.positions)})
        boundaries[part.name]={key:[int(value+start) for value in values] for key,values in part.boundaries.items()}
        row_counts[part.name]=part.adaptive_row_counts
        quad_count += part.source_quad_count
    pos=np.concatenate(positions); nor=np.concatenate(normals); tex=np.concatenate(uv); ind=np.concatenate(indices)
    joints=np.zeros((len(pos),4),dtype=np.uint16); weights=np.zeros((len(pos),4),dtype=np.float32)
    merged_extras=extras | {
        "component_vertex_ranges":component_ranges,
        "component_boundaries":boundaries,
        "adaptive_row_counts":row_counts,
        "source_quad_count":quad_count,
    }
    return MeshData(name,pos,nor,tex,ind,joints,weights,material,merged_extras)


def _resample_boundary(values: list[int], count: int) -> list[int]:
    if count <= 1:
        return [values[0]]
    positions=np.linspace(0,len(values)-1,count)
    return [int(values[int(round(position))]) for position in positions]


def _seam(name: str, a: list[int], b: list[int], closure: str="sewn", reverse_b: bool=True, rest_distance: float=0.0) -> dict:
    count=min(len(a),len(b))
    aa=_resample_boundary(a,count)
    bb=_resample_boundary(b,count)
    if reverse_b:
        bb=list(reversed(bb))
    return {
        "seam_id":name,
        "closure_type":closure,
        "ordered_vertex_pairs":[[int(x),int(y)] for x,y in zip(aa,bb)],
        "rest_distance":rest_distance,
        "simulation_constraint":"distance_pair",
    }


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


def _apply_smooth_weights(mesh: MeshData, mode: str) -> None:
    p=mesh.positions; x=p[:,0]; y=p[:,1]
    scores=np.zeros((len(p),len(JOINT_NAMES)),dtype=np.float32)
    if mode=="tunic":
        scores[:,JOINT["Chest"]]=0.65+0.25*_smoothstep(1.05,1.55,y)
        scores[:,JOINT["Spine"]]=0.42*(1-_smoothstep(1.28,1.65,y))
        arm=np.abs(x)
        left=_smoothstep(.32,.95,x); right=_smoothstep(.32,.95,-x)
        scores[:,JOINT["UpperArm_L"]]=left*(.55+.25*_smoothstep(.45,.95,arm))
        scores[:,JOINT["LowerArm_L"]]=left*.32*_smoothstep(.66,1.05,arm)
        scores[:,JOINT["UpperArm_R"]]=right*(.55+.25*_smoothstep(.45,.95,arm))
        scores[:,JOINT["LowerArm_R"]]=right*.32*_smoothstep(.66,1.05,arm)
        hem=_smoothstep(1.22,.82,y)
        scores[:,JOINT["TunicHem_L"]]=hem*_smoothstep(-.05,.45,x)*.75
        scores[:,JOINT["TunicHem_R"]]=hem*_smoothstep(-.05,.45,-x)*.75
        scores[:,JOINT["TunicHem_C"]]=hem*(1-_smoothstep(.08,.38,np.abs(x)))*.72
    elif mode=="skirt":
        hem=_smoothstep(.70,.18,y)
        scores[:,JOINT["Hips"]]=.8*(1-.48*hem)+.15
        scores[:,JOINT["Spine"]]=.12*(1-hem)
        scores[:,JOINT["SkirtHem_L"]]=hem*(.25+.75*_smoothstep(-.35,.35,x))
        scores[:,JOINT["SkirtHem_R"]]=hem*(.25+.75*_smoothstep(-.35,.35,-x))
    elif mode=="mantle":
        hem=_smoothstep(1.25,.55,y)
        scores[:,JOINT["Chest"]]=.78*(1-.62*hem)+.12
        scores[:,JOINT["Spine"]]=.20*(1-hem)
        scores[:,JOINT["CapeHem_L"]]=hem*_smoothstep(-.12,.45,x)*.88
        scores[:,JOINT["CapeHem_R"]]=hem*_smoothstep(-.12,.45,-x)*.88
        scores[:,JOINT["CapeHem_C"]]=hem*(1-_smoothstep(.10,.48,np.abs(x)))*.86
    elif mode=="decor":
        hem=_smoothstep(1.30,.34,y)
        scores[:,JOINT["Chest"]]=.72*(1-.65*hem)+.1
        scores[:,JOINT["CapeHem_C"]]=.92*hem
        scores[:,JOINT["CapeHem_L"]]=.25*hem*_smoothstep(0,.5,x)
        scores[:,JOINT["CapeHem_R"]]=.25*hem*_smoothstep(0,.5,-x)
    elif mode=="body":
        head=_smoothstep(1.62,1.95,y)
        torso=np.clip(1-head,0,1)*_smoothstep(.65,1.45,y)
        hips=(1-_smoothstep(.65,1.08,y))*_smoothstep(-.2,.7,y)
        left_arm=_smoothstep(.35,.92,x)*_smoothstep(1.05,1.65,y)
        right_arm=_smoothstep(.35,.92,-x)*_smoothstep(1.05,1.65,y)
        left_leg=_smoothstep(-.25,.25,x)*(1-_smoothstep(.45,.82,y))
        right_leg=_smoothstep(-.25,.25,-x)*(1-_smoothstep(.45,.82,y))
        scores[:,JOINT["Head"]]=head*.85; scores[:,JOINT["Neck"]]=head*.15
        scores[:,JOINT["Chest"]]=torso*.70; scores[:,JOINT["Spine"]]=torso*.30
        scores[:,JOINT["Hips"]]=hips*.75+.05
        scores[:,JOINT["UpperArm_L"]]=left_arm*.72; scores[:,JOINT["LowerArm_L"]]=left_arm*.28
        scores[:,JOINT["UpperArm_R"]]=right_arm*.72; scores[:,JOINT["LowerArm_R"]]=right_arm*.28
        scores[:,JOINT["UpperLeg_L"]]=left_leg*.72; scores[:,JOINT["LowerLeg_L"]]=left_leg*.28
        scores[:,JOINT["UpperLeg_R"]]=right_leg*.72; scores[:,JOINT["LowerLeg_R"]]=right_leg*.28
    else:
        raise ValueError(mode)
    top=np.argpartition(scores,-4,axis=1)[:,-4:]
    values=np.take_along_axis(scores,top,axis=1)
    order=np.argsort(values,axis=1)[:,::-1]
    top=np.take_along_axis(top,order,axis=1)
    values=np.take_along_axis(values,order,axis=1)
    values_sum=values.sum(axis=1,keepdims=True)
    zero=values_sum[:,0]<=1e-8
    top[zero,0]=JOINT["Hips"] if mode in ("skirt","body") else JOINT["Chest"]
    values[zero,0]=1.0
    values_sum=values.sum(axis=1,keepdims=True)
    mesh.joints[:]=top.astype(np.uint16)
    mesh.weights[:]=values/np.maximum(values_sum,1e-8)


def _tunic_parts(adaptive: bool) -> list[SurfacePart]:
    if adaptive:
        v=np.array([0,.035,.08,.15,.24,.34,.46,.58,.69,.78,.86,.92,.96,1.0])
        counts=[30,28,25,22,20,19,18,18,19,21,24,27,29,31]
        sleeve_v=np.array([0,.05,.12,.22,.35,.50,.65,.78,.88,.95,1.0])
        sleeve_counts=[26,24,22,20,18,17,17,18,20,22,25]
        make=lambda name,fn,scale,rev=False:_adaptive_surface(name,v,counts,fn,scale,rev)
        make_s=lambda name,fn,rev=False:_adaptive_surface(name,sleeve_v,sleeve_counts,fn,(1.8,2.0),rev)
    else:
        make=lambda name,fn,scale,rev=False:_uniform_surface(name,8,9,fn,scale,rev)
        make_s=lambda name,fn,rev=False:_uniform_surface(name,8,7,fn,(1.8,2.0),rev)
    parts=[]
    for side,label in ((1,"front"),(-1,"back")):
        def panel(u,v,side=side):
            y=1.68-v*.82
            half=.31+.10*v+.03*math.sin(v*math.pi)
            x=(u*2-1)*half
            macro=.012*math.sin(u*math.pi*3)*math.sin(v*math.pi*2)
            micro=.006*math.sin(u*math.pi*10)*(0.25+0.75*v)
            z=side*(.205+.012*math.cos((u-.5)*math.pi*2))+side*(macro+micro)
            return x,y,z
        parts.append(make(label,panel,(2.4,2.2),side<0))
    for arm_side,label in ((1,"sleeve_left"),(-1,"sleeve_right")):
        def sleeve(u,v,s=arm_side):
            theta=(u-.5)*math.pi*1.72
            length=v*.64
            x=s*(.29+length)
            y=1.58-.09*length+.145*math.cos(theta)
            z=.135*math.sin(theta)*(1-.15*v)
            return x,y,z
        parts.append(make_s(label,sleeve,arm_side<0))
    return parts


def _skirt_part(adaptive: bool) -> SurfacePart:
    if adaptive:
        v=np.array([0,.03,.07,.13,.21,.31,.43,.55,.66,.76,.84,.90,.95,.98,1.0])
        counts=[38,34,31,28,26,24,23,24,26,29,33,37,41,44,46]
        maker=lambda fn:_adaptive_surface("wrap_panel",v,counts,fn,(4.0,2.5))
    else:
        maker=lambda fn:_uniform_surface("wrap_panel",12,10,fn,(4.0,2.5))
    def surf(u,v):
        theta=-math.pi+u*(math.pi*2.18)
        y=1.00-v*.78
        radius=.32+v*.18+.012*math.sin(theta*7)*(v**1.25)+.006*math.sin(theta*13)
        return radius*math.sin(theta),y,radius*math.cos(theta)
    return maker(surf)


def _mantle_part(adaptive: bool) -> SurfacePart:
    if adaptive:
        v=np.array([0,.03,.08,.15,.24,.35,.47,.59,.70,.79,.87,.93,.97,1.0])
        counts=[33,31,28,25,23,21,20,21,23,26,30,34,38,41]
        maker=lambda fn:_adaptive_surface("draped_panel",v,counts,fn,(3.8,3.0),True)
    else:
        maker=lambda fn:_uniform_surface("draped_panel",11,10,fn,(3.8,3.0),True)
    def surf(u,v):
        y=1.68-v*1.05
        half=.34+v*.48
        x=(u*2-1)*half
        fold=.038*math.sin(u*math.pi*7)*(0.12+v*.88)+.014*math.sin(u*math.pi*3+v*4)
        z=-.235-v*.16-fold
        return x,y,z
    return maker(surf)


def _decor_part(adaptive: bool) -> SurfacePart:
    if adaptive:
        v=np.array([0,.025,.07,.14,.24,.36,.50,.63,.74,.83,.90,.95,.98,1.0])
        counts=[35,33,30,27,24,22,21,22,24,27,31,35,39,43]
        maker=lambda fn:_adaptive_surface("hanging_panel",v,counts,fn,(4.0,4.0))
    else:
        maker=lambda fn:_uniform_surface("hanging_panel",12,11,fn,(4.0,4.0))
    def surf(u,v):
        x=(u*2-1)*.58
        y=1.62-v*1.28
        z=-.82+.026*math.sin(u*math.pi*9)*(0.18+v*.82)+.008*math.sin(v*math.pi*5)
        return x,y,z
    return maker(surf)


def _base_extras(asset_id: str, garment_class: str, panels: list[str], seams: list[str], fabric: dict, topology_role: str) -> dict:
    return {
        "asset_id":asset_id,"garment_class":garment_class,"detachable":True,"panels":panels,"seams":seams,
        "fabric":fabric,"provenance":{"construction":"first_party_procedural","external_finished_model":False},
        "topology_role":topology_role,
    }


def make_tunic(material: int, *, cage=False) -> MeshData:
    parts=_tunic_parts(not cage)
    extras=_base_extras("garmentforge.tunic.v2","upper_body",[p.name for p in parts],["shoulder_left","shoulder_right","side_left","side_right","sleeve_left","sleeve_right","hem","neckline"],{"fiber":"cotton-linen","areal_density_g_m2":185,"bending":"medium-soft"},"simulation_cage" if cage else "render_surface")
    extras.update({"fit_profile":"relaxed","collision_zones":["torso","shoulders","upper_arms"]})
    mesh=_combine_parts("Cage_Tunic" if cage else "Garment_Tunic",parts,material,extras)
    b=mesh.extras["component_boundaries"]
    mesh.extras["seam_constraints"]=[
        _seam("side_left",b["front"]["left"],b["back"]["right"]),
        _seam("side_right",b["front"]["right"],b["back"]["left"]),
        _seam("shoulder",b["front"]["top"],b["back"]["top"]),
        _seam("sleeve_left_attachment",b["sleeve_left"]["top"],b["front"]["right"],rest_distance=.01),
        _seam("sleeve_right_attachment",b["sleeve_right"]["top"],b["front"]["left"],rest_distance=.01),
    ]
    mesh.extras.update({
        "cage_asset_id":"garmentforge.tunic.cage.v2" if cage else None,
        "render_asset_id":None if cage else "garmentforge.tunic.render.v2",
        "quad_source":True,"triangulated_for_glb":True,"adaptive_density":not cage,
        "construction_reveal":"uv_coverage_mask","reveal_v_max":2.2,
    })
    _apply_smooth_weights(mesh,"tunic")
    return mesh


def make_skirt(material: int, *, cage=False) -> MeshData:
    part=_skirt_part(not cage)
    extras=_base_extras("garmentforge.wrap-skirt.v2","lower_body",["wrap_panel"],["waistband","overlap_edge","hem"],{"fiber":"woven-cotton","areal_density_g_m2":225,"bending":"medium"},"simulation_cage" if cage else "render_surface")
    extras.update({"fit_profile":"wrapped","collision_zones":["hips","upper_legs"],"closures":["waist_tie"],"seam_constraints":[{"seam_id":"wrap_overlap","closure_type":"overlap","ordered_vertex_pairs":[],"rest_distance":.012,"simulation_constraint":"layered_contact"}],"quad_source":True,"triangulated_for_glb":True,"adaptive_density":not cage,"construction_reveal":"uv_coverage_mask","reveal_v_max":2.5})
    mesh=_combine_parts("Cage_WrapSkirt" if cage else "Garment_WrapSkirt",[part],material,extras)
    _apply_smooth_weights(mesh,"skirt")
    return mesh


def make_mantle(material: int, *, cage=False) -> MeshData:
    part=_mantle_part(not cage)
    extras=_base_extras("garmentforge.mantle.v2","outer_layer_and_decor",["draped_panel"],["neck_binding","edge_finish","hem"],{"fiber":"wool-silk","areal_density_g_m2":260,"bending":"soft-heavy"},"simulation_cage" if cage else "render_surface")
    extras.update({"fit_profile":"draped","collision_zones":["shoulders","back","arms"],"closures":["shoulder_clasp"],"decor_reusable":True,"seam_constraints":[{"seam_id":"shoulder_clasp","closure_type":"fastener","ordered_vertex_pairs":[],"rest_distance":0.0,"simulation_constraint":"pin_pair"}],"quad_source":True,"triangulated_for_glb":True,"adaptive_density":not cage,"construction_reveal":"uv_coverage_mask","reveal_v_max":3.0})
    mesh=_combine_parts("Cage_Mantle" if cage else "Garment_Mantle",[part],material,extras)
    _apply_smooth_weights(mesh,"mantle")
    return mesh


def make_hanging_textile(material: int, *, cage=False) -> MeshData:
    part=_decor_part(not cage)
    extras=_base_extras("garmentforge.hanging-textile.v2","scene_textile_decor",["hanging_panel"],["top_sleeve","edge_finish","weighted_hem"],{"fiber":"linen","areal_density_g_m2":210,"bending":"soft"},"simulation_cage" if cage else "render_surface")
    extras.update({"decor_reusable":True,"collision_zones":[],"seam_constraints":[{"seam_id":"top_sleeve","closure_type":"rod_channel","ordered_vertex_pairs":[],"rest_distance":0.0,"simulation_constraint":"pinned_boundary"}],"quad_source":True,"triangulated_for_glb":True,"adaptive_density":not cage,"construction_reveal":"uv_coverage_mask","reveal_v_max":4.0})
    mesh=_combine_parts("Cage_HangingPanel" if cage else "Textile_HangingPanel",[part],material,extras)
    _apply_smooth_weights(mesh,"decor")
    return mesh


def make_body(material: int) -> MeshData:
    meshes=[]
    def add_ellipsoid(center,scale,sub=2):
        s=trimesh.creation.icosphere(subdivisions=sub,radius=1.0)
        s.apply_scale(scale); s.apply_translation(center); meshes.append(s)
    add_ellipsoid((0,1.35,0),(0.34,.48,.23),2)
    add_ellipsoid((0,1.92,0),(0.19,.24,.19),2)
    add_ellipsoid((0,.88,0),(.29,.22,.22),2)
    for side in (-1,1):
        add_ellipsoid((side*.53,1.49,0),(.28,.12,.12),1)
        add_ellipsoid((side*.91,1.43,0),(.26,.10,.10),1)
        add_ellipsoid((side*.20,.54,0),(.13,.40,.14),2)
        add_ellipsoid((side*.20,-.05,0),(.12,.35,.13),2)
    s=trimesh.util.concatenate(meshes)
    p=np.asarray(s.vertices,dtype=np.float32); n=np.asarray(s.vertex_normals,dtype=np.float32); i=np.asarray(s.faces.reshape(-1),dtype=np.uint32)
    uv=np.stack([(np.arctan2(p[:,2],p[:,0])/(2*math.pi)+.5),np.clip((p[:,1]+.45)/2.65,0,1)],axis=1).astype(np.float32)
    m=MeshData("Embodied_Mannequin",p,n,uv,i,np.zeros((len(p),4),np.uint16),np.zeros((len(p),4),np.float32),material,{"asset_id":"avatarforge.neutral-mannequin.v2","layer":"embodied","garment_ownership":False,"material_system":"plain_body","provenance":{"construction":"first_party_procedural"}})
    _apply_smooth_weights(m,"body")
    return m


class GarmentSystemBuilder:
    capability_id="GarmentForge.clothing_construction.v2"

    def __init__(self):
        self.builder=GLBBuilder(); self.materials={}; self.meshes={}; self.node_indices={}

    def add_materials(self):
        self.materials["body"]=self.builder.add_plain_material("Body_Skin_Plain",[.72,.52,.40,1],.68)
        specs={
            "tunic":((52,93,116),8,(108,157,178),.68,[.16,.22,.26],11),
            "skirt":((145,89,53),7,(205,151,91),.76,[.25,.15,.08],23),
            "mantle":((84,45,92),10,(151,92,161),.70,[.22,.10,.25],37),
            "decor":((180,154,92),6,(230,207,138),.74,[.26,.22,.12],41),
        }
        for name,(color,weave,accent,rough,sheen,seed) in specs.items():
            base,normal,roughmap=_fabric_maps(color,weave,accent,seed)
            bi=self.builder.add_image(base,f"{name}_base_macro_weave")
            ni=self.builder.add_image(normal,f"{name}_normal_macro_weave")
            ri=self.builder.add_image(roughmap,f"{name}_roughness_variation")
            bt=self.builder.add_texture(bi); nt=self.builder.add_texture(ni); rt=self.builder.add_texture(ri)
            self.materials[name]=self.builder.add_textile_material(f"Fabric_{name.title()}",bt,nt,rt,[1,1,1,1],rough,sheen)

    def add_skeleton(self):
        doc=self.builder.document
        for name in JOINT_NAMES:
            doc["nodes"].append({"name":name,"translation":list(JOINT_TRANSLATIONS[name]),"extras":{"semantic_role":"cloth_secondary_joint" if "Hem" in name else "humanoid_joint"}})
            self.node_indices[name]=len(doc["nodes"])-1
        for name in JOINT_NAMES:
            parent=PARENT[name]
            if parent:
                doc["nodes"][self.node_indices[parent]].setdefault("children",[]).append(self.node_indices[name])
        ibm=np.asarray([np.linalg.inv(m).T for m in _global_joint_matrices()],dtype=np.float32)
        doc["skins"].append({"name":"GarmentForgeHumanoidSkin","inverseBindMatrices":self.builder.accessor(ibm),"skeleton":self.node_indices["RigRoot"],"joints":[self.node_indices[n] for n in JOINT_NAMES],"extras":{"standard":"glTF skin","secondary_cloth_joints":[n for n in JOINT_NAMES if "Hem" in n],"smooth_weight_fields":True}})

    def add_mesh(self, mesh: MeshData) -> int:
        attrs={
            "POSITION":self.builder.accessor(mesh.positions,34962),
            "NORMAL":self.builder.accessor(mesh.normals,34962),
            "TEXCOORD_0":self.builder.accessor(mesh.uv,34962),
            "JOINTS_0":self.builder.accessor(mesh.joints,34962),
            "WEIGHTS_0":self.builder.accessor(mesh.weights,34962),
        }
        index=self.builder.accessor(mesh.indices,34963)
        self.builder.document["meshes"].append({"name":mesh.name,"primitives":[{"attributes":attrs,"indices":index,"material":mesh.material}],"extras":mesh.extras | {"vertex_count":len(mesh.positions),"triangle_count":mesh.triangle_count,"unique_weight_vectors":len(np.unique(np.round(mesh.weights,3),axis=0))}})
        mi=len(self.builder.document["meshes"])-1; self.meshes[mesh.name]=(mi,mesh); return mi

    def add_animation(self):
        times=np.asarray([0,1,2.2,3.4,4.6,6],dtype=np.float32); time_acc=self.builder.accessor(times)
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
        channels=[]; samplers=[]
        for name,values in tracks.items():
            out=self.builder.accessor(np.asarray(values,dtype=np.float32)); samplers.append({"input":time_acc,"output":out,"interpolation":"LINEAR"})
            channels.append({"sampler":len(samplers)-1,"target":{"node":self.node_indices[name],"path":"rotation"},"extras":{"motion_class":"independent_secondary_cloth" if "Hem" in name else "body_driver"}})
        self.builder.document["animations"].append({"name":"body_motion_with_smooth_secondary_textile_response","samplers":samplers,"channels":channels,"extras":{"duration_seconds":6.0,"cloth_response":"smooth skin field plus secondary joints","full_cloth_solver":False}})

    def build(self, include_body=True, selected=("Garment_Tunic","Garment_WrapSkirt","Garment_Mantle","Textile_HangingPanel"), multi_scene=True) -> bytes:
        self.add_materials(); self.add_skeleton()
        render={
            "Garment_Tunic":make_tunic(self.materials["tunic"]),
            "Garment_WrapSkirt":make_skirt(self.materials["skirt"]),
            "Garment_Mantle":make_mantle(self.materials["mantle"]),
            "Textile_HangingPanel":make_hanging_textile(self.materials["decor"]),
        }
        cages={
            "Garment_Tunic":make_tunic(self.materials["tunic"],cage=True),
            "Garment_WrapSkirt":make_skirt(self.materials["skirt"],cage=True),
            "Garment_Mantle":make_mantle(self.materials["mantle"],cage=True),
            "Textile_HangingPanel":make_hanging_textile(self.materials["decor"],cage=True),
        }
        if include_body:
            self.add_mesh(make_body(self.materials["body"]))
        for name in selected:
            self.add_mesh(render[name]); self.add_mesh(cages[name])
        doc=self.builder.document; active=[]; body_node=None
        if include_body:
            mi,_=self.meshes["Embodied_Mannequin"]
            doc["nodes"].append({"name":"Layer_Embodied_Body","mesh":mi,"skin":0,"extras":{"layer":"embodied","detachable":False}}); body_node=len(doc["nodes"])-1; active.append(body_node)
        for name in selected:
            mi,mesh=self.meshes[name]
            doc["nodes"].append({"name":name,"mesh":mi,"skin":0,"extras":{"layer":"artifact","asset_id":mesh.extras["asset_id"],"detachable":True,"default_state":"worn" if not name.startswith("Textile") else "decor","render_surface":True}})
            active.append(len(doc["nodes"])-1)
        cage_nodes=[]
        for index,name in enumerate(selected):
            cage_name={"Garment_Tunic":"Cage_Tunic","Garment_WrapSkirt":"Cage_WrapSkirt","Garment_Mantle":"Cage_Mantle","Textile_HangingPanel":"Cage_HangingPanel"}[name]
            mi,mesh=self.meshes[cage_name]
            doc["nodes"].append({"name":cage_name,"mesh":mi,"skin":0,"translation":[(index-1.5)*1.35,0,0],"extras":{"layer":"simulation_cage","asset_id":mesh.extras["asset_id"],"seam_constraints":mesh.extras["seam_constraints"]}})
            cage_nodes.append(len(doc["nodes"])-1)
        self.add_animation()
        doc["scenes"].append({"name":"Dressed_Character_And_Textile_Decor","nodes":[self.node_indices["RigRoot"]]+active,"extras":{"garment_state":"assembled","supports_remove_replace":True,"visible_topology":"render_surface"}})
        if multi_scene and include_body:
            doc["scenes"].append({"name":"Body_Only_Verification","nodes":[self.node_indices["RigRoot"],body_node],"extras":{"garment_state":"removed"}})
            gallery=[]
            for index,name in enumerate(selected):
                mi,mesh=self.meshes[name]
                doc["nodes"].append({"name":f"Gallery_{name}","mesh":mi,"translation":[(index-1.5)*1.5,0,0],"extras":{"layer":"artifact_gallery","asset_id":mesh.extras["asset_id"],"state":"detached","render_surface":True}})
                gallery.append(len(doc["nodes"])-1)
            doc["scenes"].append({"name":"Detached_Garment_Gallery","nodes":gallery,"extras":{"garment_state":"detached_and_manipulable"}})
            doc["scenes"].append({"name":"Simulation_Cages_And_Seams","nodes":[self.node_indices["RigRoot"]]+cage_nodes,"extras":{"garment_state":"simulation_cage_verification","cages_separate_from_render_surfaces":True}})
        doc["extras"]={
            "capability_id":self.capability_id,
            "contract":"body, simulation cages, and adaptive render surfaces remain separately owned",
            "interaction":{"attachments":["shoulders","waist","back"],"collision_zones":["torso","arms","hips","legs"],"solver_boundary":"explicit ordered seam constraints plus smooth skin transfer"},
            "construction_animation":{"method":"viewer_shader_uv_coverage_mask","topology_spawn":False,"continuous_surface":True},
            "verification":{"reopen":True,"alternate_pose":True,"alternate_garment_state":True,"alternate_camera":True,"simulation_cage_scene":True},
            "truth_boundary":"This GLB demonstrates separate simulation cages, explicit seam mappings, adaptive render topology, smooth skin fields, and coverage-based construction reveal. It does not claim continuum cloth simulation or manufacturing fit approval.",
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
    viewer_dir=output/"viewer"; viewer_dir.mkdir(exist_ok=True)
    for filename,content in (("index.html",viewer_html()),("construction.html",construction_viewer_html())):
        path=viewer_dir/filename; path.write_text(content,encoding="utf-8")
        inventory.append({"path":f"viewer/{filename}","bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"kind":"inspection_viewer"})
    manifest={
        "schema_version":"2.0.0","kind":"garmentforge.delivery-manifest","capability_id":GarmentSystemBuilder.capability_id,
        "canonical_scene":"clothing-system.glb","detachable_assets":["tunic.glb","wrap-skirt.glb","mantle.glb","hanging-textile.glb"],
        "file_format":"glTF 2.0 binary (.glb)","external_finished_model_provider":False,
        "topology":{"simulation_cage":"coarse quad source triangulated only in GLB","render_surface":"adaptive variable-row triangulation","seams":"ordered cage boundary constraints"},
        "construction_animation":{"viewer":"viewer/construction.html","method":"continuous UV coverage reveal","geometry_spawn":False},
        "physics_boundary":{"implemented":"cage/render separation, explicit seam pairs, smooth skin transfer, secondary cloth joints","not_claimed":"continuum cloth simulation, manufacturing-ready patterns"},
        "files":inventory,
    }
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return manifest
