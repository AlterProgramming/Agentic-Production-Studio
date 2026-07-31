from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import trimesh

from objectforge.evaluation.quality import evaluate_builder, evaluate_diversity, evaluate_glb
from objectforge.families.cases import build_case
from objectforge.families.lamps import build_lamp
from objectforge.families.tables import build_table
from objectforge.geometry import sha256_bytes, write_json
from objectforge.planning.planner import ObjectPlan, Scope1Planner
from objectforge.runtime_glb import patch_runtime_glb


def viewer_html(asset_id: str) -> str:
    return textwrap.dedent(f"""\
    <!doctype html><html lang="en"><head><meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>ObjectForge Inspector — {asset_id}</title>
    <style>:root{{color-scheme:dark;font-family:system-ui,sans-serif}}*{{box-sizing:border-box}}body{{margin:0;background:#0a1017;color:#e9f0f7;overflow:hidden}}#app{{display:grid;grid-template-columns:1fr 300px;height:100vh}}canvas{{display:block;width:100%;height:100%}}aside{{padding:18px;background:#101923;border-left:1px solid #273747}}button,input,select{{width:100%;padding:9px;margin:4px 0;border-radius:8px;border:1px solid #344a60;background:#192634;color:#e9f0f7}}.row{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}#status,#selection{{font-size:12px;line-height:1.5;color:#b8c8d7}}</style>
    <script type="importmap">{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/"}}}}</script></head>
    <body><div id="app"><main id="viewport"></main><aside><h2>ObjectForge Inspector</h2><p>{asset_id}</p><div id="status">Loading retained GLB…</div><select id="clips"></select><div class="row"><button id="play">Play</button><button id="pause">Pause</button></div><div class="row"><button id="wire">Wireframe</button><button id="reset">Reset camera</button></div><label>Key light</label><input id="light" type="range" min="0" max="8" step="0.1" value="3.2"/><p id="selection">Click a component to inspect its retained node name.</p></aside></div>
    <script type="module">import * as THREE from 'three';import{{OrbitControls}}from'three/addons/controls/OrbitControls.js';import{{GLTFLoader}}from'three/addons/loaders/GLTFLoader.js';const host=document.querySelector('#viewport'),scene=new THREE.Scene();scene.background=new THREE.Color(0x101822);const camera=new THREE.PerspectiveCamera(42,host.clientWidth/host.clientHeight,.03,100);camera.position.set(4.8,3.2,6.2);const renderer=new THREE.WebGLRenderer({{antialias:true}});renderer.setSize(host.clientWidth,host.clientHeight);renderer.setPixelRatio(devicePixelRatio);renderer.outputColorSpace=THREE.SRGBColorSpace;host.append(renderer.domElement);const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;scene.add(new THREE.HemisphereLight(0xcde1ff,0x24201d,1.35));const key=new THREE.DirectionalLight(0xffe3c7,3.2);key.position.set(-4,6,5);scene.add(key);const rim=new THREE.DirectionalLight(0x78bfff,2.2);rim.position.set(4,4,-5);scene.add(rim);let root,mixer,clips=[],wire=false;const clock=new THREE.Clock();function fit(){{const box=new THREE.Box3().setFromObject(root),c=box.getCenter(new THREE.Vector3()),s=box.getSize(new THREE.Vector3());controls.target.copy(c);camera.position.copy(c).add(new THREE.Vector3(s.length()*.72,s.length()*.42,s.length()*.82));controls.update()}}new GLTFLoader().load('../object-showcase.glb',g=>{{root=g.scene;clips=g.animations;scene.add(root);mixer=new THREE.AnimationMixer(root);const select=document.querySelector('#clips');clips.forEach((clip,i)=>{{const o=document.createElement('option');o.value=i;o.textContent=clip.name;select.append(o)}});document.querySelector('#status').textContent=`Loaded ${{clips.length}} animation clips`;fit()}},undefined,e=>document.querySelector('#status').textContent=e.message);document.querySelector('#play').onclick=()=>{{if(!mixer||!clips.length)return;mixer.stopAllAction();mixer.clipAction(clips[+document.querySelector('#clips').value]).reset().play()}};document.querySelector('#pause').onclick=()=>{{if(mixer)mixer.timeScale=mixer.timeScale?0:1}};document.querySelector('#wire').onclick=()=>{{wire=!wire;root?.traverse(o=>{{if(o.isMesh)o.material.wireframe=wire}})}};document.querySelector('#reset').onclick=fit;document.querySelector('#light').oninput=e=>key.intensity=+e.target.value;const ray=new THREE.Raycaster(),mouse=new THREE.Vector2();renderer.domElement.addEventListener('pointerdown',e=>{{const r=renderer.domElement.getBoundingClientRect();mouse.x=((e.clientX-r.left)/r.width)*2-1;mouse.y=-((e.clientY-r.top)/r.height)*2+1;ray.setFromCamera(mouse,camera);const hit=ray.intersectObject(root,true)[0];if(hit)document.querySelector('#selection').textContent=hit.object.name||'unnamed part'}});addEventListener('resize',()=>{{camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix();renderer.setSize(host.clientWidth,host.clientHeight)}});function tick(){{requestAnimationFrame(tick);mixer?.update(clock.getDelta());controls.update();renderer.render(scene,camera)}}tick();</script></body></html>
    """)


def _builder_for(plan: ObjectPlan):
    if plan.family == "lamp":
        return build_lamp(plan)
    if plan.family == "case":
        return build_case(plan)
    if plan.family == "table":
        return build_table(plan)
    raise ValueError(plan.family)


def build_asset(plan: ObjectPlan, output_root: Path) -> dict[str, Any]:
    builder = _builder_for(plan)
    builder_evaluation = evaluate_builder(builder)
    if not builder_evaluation.passed:
        raise ValueError(f"builder failed: {builder_evaluation.failures}")

    object_dir = output_root / "object"
    showcase_dir = output_root / "showcase"
    behavior_dir = output_root / "behavior"
    construction_dir = output_root / "construction"
    recovery_dir = output_root / "recovery"
    for directory in (object_dir, showcase_dir / "viewer", behavior_dir, construction_dir, recovery_dir):
        directory.mkdir(parents=True, exist_ok=True)

    operation_bytes = builder.operation_jsonl()
    construction_hash = sha256_bytes(operation_bytes)
    canonical = patch_runtime_glb(trimesh.exchange.gltf.export_glb(builder.build_scene(False), include_normals=True), builder=builder, construction_hash=construction_hash, showcase=False)
    showcase = patch_runtime_glb(trimesh.exchange.gltf.export_glb(builder.build_scene(True), include_normals=True), builder=builder, construction_hash=construction_hash, showcase=True)
    (object_dir / "object.glb").write_bytes(canonical)
    (showcase_dir / "object-showcase.glb").write_bytes(showcase)

    write_json(object_dir / "semantic-parts.json", builder.semantic_contract())
    write_json(object_dir / "materials.json", builder.material_contract())
    write_json(behavior_dir / "physics.json", builder.physics_contract())
    write_json(behavior_dir / "animations.json", {"schema_version": "1.0", "clips": ([{"name": "functional_demo", "duration_seconds": 6.0, "loop": True, "joints": [item.id for item in builder.articulations]}] if builder.articulations else []), "embedded_in_glb": bool(builder.articulations)})
    write_json(behavior_dir / "interactions.json", builder.interaction)
    (construction_dir / "operations.jsonl").write_bytes(operation_bytes)
    write_json(construction_dir / "plan.json", plan.to_dict())
    write_json(recovery_dir / "receipt.json", {"schema_version": "1.0", **builder.recovery, "construction_sha256": construction_hash, "external_finished_model_provider": False})
    (showcase_dir / "viewer" / "index.html").write_text(viewer_html(plan.asset_id), encoding="utf-8")

    glb_evaluation = evaluate_glb(canonical, minimum_meshes=int(plan.acceptance["minimum_meshes"]), require_animation=bool(builder.articulations), root_name=builder.root_name)
    validation = {"passed": builder_evaluation.passed and glb_evaluation.passed, "builder": builder_evaluation.metrics, "asset": glb_evaluation.metrics, "failures": list(builder_evaluation.failures + glb_evaluation.failures), "functional": builder.recovery.get("rollback", {}).get("replacement_metrics", {})}
    write_json(output_root / "validation.json", validation)

    files = []
    for path in sorted(item for item in output_root.rglob("*") if item.is_file()):
        payload = path.read_bytes()
        files.append({"path": path.relative_to(output_root).as_posix(), "bytes": len(payload), "sha256": sha256_bytes(payload)})
    manifest = {"schema_version": "1.0", "kind": "objectforge.scope1-asset-manifest", "asset_id": plan.asset_id, "family": plan.family, "variant": plan.variant, "canonical_model": "object/object.glb", "showcase_model": "showcase/object-showcase.glb", "viewer": "showcase/viewer/index.html", "physics": "behavior/physics.json", "construction_history": "construction/operations.jsonl", "recovery_receipt": "recovery/receipt.json", "validation": validation, "grammar_driven": True, "external_finished_model_provider": False, "files": files}
    write_json(output_root / "manifest.json", manifest)
    return manifest


def build_scope1(output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    records = []
    for family, variant in Scope1Planner.variants():
        plan = Scope1Planner.resolve(family, variant)
        asset_root = output_root / family / variant
        manifest = build_asset(plan, asset_root)
        records.append({"asset_id": plan.asset_id, "family": family, "variant": variant, "path": asset_root.relative_to(output_root).as_posix(), "passed": manifest["validation"]["passed"], "metrics": manifest["validation"]["builder"], "canonical_sha256": next(item["sha256"] for item in manifest["files"] if item["path"] == "object/object.glb")})
    diversity = evaluate_diversity(records)
    grammar_matrix: dict[str, list[str]] = {}
    for family, variant in Scope1Planner.variants():
        for grammar in Scope1Planner.resolve(family, variant).grammars:
            grammar_matrix.setdefault(grammar.grammar, []).append(f"{family}/{variant}:{grammar.role}")
    index = {"schema_version": "1.0", "capability_id": "objectforge.grammar-driven-detailed-assets.v1", "scope": "ObjectForge Scope 1", "status": "passed" if diversity.passed and all(item["passed"] for item in records) else "failed", "assets": records, "grammar_reuse": {key: sorted(value) for key, value in sorted(grammar_matrix.items())}, "diversity": {"passed": diversity.passed, "metrics": diversity.metrics, "failures": list(diversity.failures)}, "scope0_regression_required": True, "external_finished_model_provider": False}
    write_json(output_root / "scope1-index.json", index)
    return index
