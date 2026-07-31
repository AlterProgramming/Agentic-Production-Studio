from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path
from typing import Any

import trimesh

from .builder import TaskLampBuilder
from .geometry import sha256_bytes, write_json
from .gltf import parse_glb
from .gltf_patch import patch_glb


def viewer_html() -> str:
    return textwrap.dedent("""\
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>ObjectForge Task Lamp Inspector</title>
      <style>
        :root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif}
        *{box-sizing:border-box} body{margin:0;background:#0b1017;color:#eaf1f8;overflow:hidden}
        #app{display:grid;grid-template-columns:1fr 320px;height:100vh}
        canvas{display:block;width:100%;height:100%}
        aside{padding:18px;background:linear-gradient(180deg,#121a24,#0d131c);border-left:1px solid #263444;overflow:auto}
        h1{font-size:18px;margin:0 0 4px}.sub{opacity:.64;font-size:12px;margin-bottom:18px}
        section{padding:12px 0;border-top:1px solid #263444}label{display:block;font-size:12px;opacity:.78;margin:9px 0 4px}
        button,select,input{width:100%;background:#1b2734;color:#eaf1f8;border:1px solid #34485d;border-radius:8px;padding:9px}
        button{cursor:pointer;margin:4px 0}button:hover{background:#243447}.row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
        .chip{padding:6px 8px;border-radius:99px;background:#1b2734;font-size:11px;display:inline-block;margin:2px}
        #status{font-size:12px;line-height:1.5;color:#b9c8d7}.ok{color:#7ee2a8}
      </style>
      <script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/"}}</script>
    </head>
    <body><div id="app"><main id="viewport"></main><aside>
      <h1>Task Lamp Inspector</h1><div class="sub">Procedural retained asset · GLB · PBR · articulation · physics metadata</div>
      <section><div id="status">Loading retained model…</div></section>
      <section><label>Animation</label><select id="animation"></select><div class="row"><button id="play">Play</button><button id="pause">Pause</button></div></section>
      <section><label>Inspection</label><div class="row"><button id="wire">Wireframe</button><button id="bounds">Bounds</button></div><button id="reset">Reset camera</button></section>
      <section><label>Key light intensity</label><input id="light" type="range" min="0" max="8" step="0.1" value="3.2"/></section>
      <section><label>Semantic parts</label><div id="parts"></div></section>
      <section><label>Retained behavior</label><div class="chip">3 hinge joints</div><div class="chip">collision proxies</div><div class="chip">mass + friction</div><div class="chip">emissive light</div></section>
    </aside></div>
    <script type="module">
      import * as THREE from 'three';
      import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
      import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
      const host=document.querySelector('#viewport');
      const renderer=new THREE.WebGLRenderer({antialias:true}); renderer.setPixelRatio(devicePixelRatio); renderer.setSize(host.clientWidth,host.clientHeight);
      renderer.outputColorSpace=THREE.SRGBColorSpace; renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1.05; renderer.shadowMap.enabled=true; host.appendChild(renderer.domElement);
      const scene=new THREE.Scene(); scene.background=new THREE.Color(0x111923);
      const camera=new THREE.PerspectiveCamera(42,host.clientWidth/host.clientHeight,.03,100); camera.position.set(5.2,3.5,6.6);
      const controls=new OrbitControls(camera,renderer.domElement); controls.target.set(.75,1.6,0); controls.enableDamping=true;
      const floor=new THREE.Mesh(new THREE.CircleGeometry(4.2,96),new THREE.MeshStandardMaterial({color:0x313a45,roughness:.72})); floor.rotation.x=-Math.PI/2; floor.position.y=-.18; floor.receiveShadow=true; scene.add(floor);
      const key=new THREE.SpotLight(0xffe1bd,3.2,18,.72,.42,1); key.position.set(-3.2,6.2,4.8); key.castShadow=true; scene.add(key);
      const fill=new THREE.PointLight(0x75a8ff,1.7,15); fill.position.set(4.8,3.6,3.5); scene.add(fill);
      const rim=new THREE.PointLight(0x5bd7ff,1.4,14); rim.position.set(1.0,5.2,-4.2); scene.add(rim);
      let root,mixer,helpers=[],clips=[]; const clock=new THREE.Clock();
      const status=document.querySelector('#status'), parts=document.querySelector('#parts'), animation=document.querySelector('#animation');
      new GLTFLoader().load('../../object/object.glb',gltf=>{root=gltf.scene; root.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true}}); scene.add(root);
        mixer=new THREE.AnimationMixer(root); clips=gltf.animations; clips.forEach((clip,i)=>{const op=document.createElement('option');op.value=i;op.textContent=clip.name;animation.appendChild(op)});
        const names=[];root.traverse(o=>{const id=o.userData?.semantic_part;if(id&&!names.includes(id))names.push(id)}); names.sort().forEach(name=>{const chip=document.createElement('button');chip.textContent=name;chip.onclick=()=>{root.traverse(o=>{if(o.isMesh)o.material.emissive?.setHex(o.userData?.semantic_part===name?0x224466:0x000000)})};parts.appendChild(chip)});
        status.innerHTML='<span class="ok">Model reopened</span><br>Embedded textures and PBR materials<br>Animation clips: '+gltf.animations.length+'<br>Physics: behavior/physics.json';
      },undefined,e=>status.textContent='Load failed: '+e.message);
      document.querySelector('#play').onclick=()=>{if(mixer&&clips.length){mixer.stopAllAction();mixer.timeScale=1;mixer.clipAction(clips[+animation.value]).reset().play()}};
      document.querySelector('#pause').onclick=()=>{if(mixer)mixer.timeScale=mixer.timeScale===0?1:0};
      document.querySelector('#wire').onclick=()=>root?.traverse(o=>{if(o.isMesh)o.material.wireframe=!o.material.wireframe});
      document.querySelector('#bounds').onclick=()=>{helpers.forEach(h=>scene.remove(h));helpers=[];if(root){const h=new THREE.BoxHelper(root,0x64d9ff);scene.add(h);helpers.push(h)}};
      document.querySelector('#reset').onclick=()=>{camera.position.set(5.2,3.5,6.6);controls.target.set(.75,1.6,0)};
      document.querySelector('#light').oninput=e=>key.intensity=+e.target.value;
      addEventListener('resize',()=>{camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix();renderer.setSize(host.clientWidth,host.clientHeight)});
      renderer.setAnimationLoop(()=>{const dt=clock.getDelta();if(mixer)mixer.update(dt);controls.update();renderer.render(scene,camera)});
    </script></body></html>
    """)


def build_package(output_root: Path) -> dict[str, Any]:
    builder = TaskLampBuilder()
    recovery = builder.plan_and_recover()
    builder.build_geometry()

    object_dir = output_root / "object"
    showcase_dir = output_root / "showcase"
    behavior_dir = output_root / "behavior"
    construction_dir = output_root / "construction"
    recovery_dir = output_root / "recovery"
    for directory in [object_dir, showcase_dir / "viewer", behavior_dir, construction_dir, recovery_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    physics = builder.physics_contract()
    semantic = builder.semantic_contract()
    operations = [operation.__dict__ for operation in builder.operations]
    operation_bytes = ("\n".join(json.dumps(item, sort_keys=True) for item in operations) + "\n").encode("utf-8")
    construction_hash = sha256_bytes(operation_bytes)

    object_raw = trimesh.exchange.gltf.export_glb(builder.build_scene(include_showcase=False), include_normals=True)
    object_glb = patch_glb(object_raw, construction_hash=construction_hash, physics=physics, semantic=semantic, showcase=False)
    (object_dir / "object.glb").write_bytes(object_glb)

    showcase_raw = trimesh.exchange.gltf.export_glb(builder.build_scene(include_showcase=True), include_normals=True)
    showcase_glb = patch_glb(showcase_raw, construction_hash=construction_hash, physics=physics, semantic=semantic, showcase=True)
    (showcase_dir / "object-showcase.glb").write_bytes(showcase_glb)

    write_json(object_dir / "semantic-parts.json", semantic)
    write_json(object_dir / "materials.json", {
        "schema_version": "1.0",
        "materials": [spec.__dict__ for spec, _ in builder.materials.values()],
        "embedded_in_glb": True,
        "texture_generation": "first_party_procedural",
        "external_providers": False,
    })
    write_json(behavior_dir / "physics.json", physics)
    write_json(behavior_dir / "animations.json", {
        "schema_version": "1.0",
        "clips": [{"name": "articulation_demo", "duration_seconds": 6.0, "loop": True,
                   "joints": ["base_hinge", "elbow_hinge", "shade_hinge"]}],
        "embedded_in_glb": True,
    })
    write_json(behavior_dir / "interactions.json", {
        "schema_version": "1.0",
        "viewer_actions": ["orbit", "pan", "zoom", "wireframe", "adjust_light", "play_animation", "select_semantic_part"],
        "drag_joints": ["LowerArmPivot", "UpperArmPivot", "ShadePivot"],
    })
    (construction_dir / "operations.jsonl").write_bytes(operation_bytes)
    write_json(construction_dir / "initial-field.json", {
        "representation": "semantic_constructive_field",
        "seed": {"primitive": "ellipsoid", "dimensions": [0.55, 0.55, 0.55]},
        "development_frontier": ["support", "reach", "articulation", "directional shade", "surface detail", "materials", "physics"],
    })
    write_json(recovery_dir / "receipt.json", {
        "schema_version": "1.0",
        "status": "recovered",
        "forced_failure": {"operation": recovery["rejected_operation"], "finding": "unstable upper-arm reach",
                           "metrics": recovery["rejected"]},
        "rollback": {"preserved_prior_state": True, "replacement_metrics": recovery["recovered"]},
        "source_overwritten": False,
        "external_provider": False,
        "construction_sha256": construction_hash,
    })
    (showcase_dir / "viewer" / "index.html").write_text(viewer_html(), encoding="utf-8")

    document, binary = parse_glb(object_glb)
    required_nodes = {"LampRoot", "LowerArmPivot", "UpperArmPivot", "ShadePivot", "ShadeShell", "BulbEmitter"}
    node_names = {node.get("name") for node in document.get("nodes", [])}
    validation = {
        "reopened_scene": bool(document.get("meshes")) and bool(document.get("accessors")) and bool(binary) and required_nodes.issubset(node_names),
        "geometry_count": len(document.get("meshes", [])),
        "node_count": len(document.get("nodes", [])),
        "material_count": len(document.get("materials", [])),
        "embedded_image_count": len(document.get("images", [])),
        "animation_count": len(document.get("animations", [])),
        "lights_extension": "KHR_lights_punctual" in document.get("extensionsUsed", []),
        "external_uris": [image.get("uri") for image in document.get("images", []) if image.get("uri")],
    }
    validation["passed"] = all([
        validation["reopened_scene"], validation["geometry_count"] >= 25, validation["material_count"] >= 7,
        validation["embedded_image_count"] >= 6, validation["animation_count"] >= 1,
        validation["lights_extension"], not validation["external_uris"],
    ])
    write_json(output_root / "validation.json", validation)

    files = []
    for path in sorted(candidate for candidate in output_root.rglob("*") if candidate.is_file()):
        payload = path.read_bytes()
        files.append({"path": path.relative_to(output_root).as_posix(), "bytes": len(payload), "sha256": sha256_bytes(payload)})
    manifest = {
        "schema_version": "1.0",
        "kind": "objectforge.delivery-manifest",
        "asset_id": "objectforge-task-lamp-scope0",
        "canonical_model": "object/object.glb",
        "showcase_model": "showcase/object-showcase.glb",
        "viewer": "showcase/viewer/index.html",
        "physics": "behavior/physics.json",
        "construction_history": "construction/operations.jsonl",
        "recovery_receipt": "recovery/receipt.json",
        "validation": validation,
        "external_model_generation_provider": False,
        "files": files,
    }
    write_json(output_root / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the ObjectForge Scope 0 detailed articulated task lamp.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_package(args.output)
    print(json.dumps({"status": "completed" if manifest["validation"]["passed"] else "failed",
                      "canonical_model": str(args.output / manifest["canonical_model"]),
                      "showcase_model": str(args.output / manifest["showcase_model"]),
                      "validation": manifest["validation"]}, indent=2))
