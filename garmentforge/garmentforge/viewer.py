from __future__ import annotations
import textwrap


def _shell(construction: bool) -> str:
    title="GarmentForge Construction Reveal" if construction else "GarmentForge Textile Inspector"
    extra_controls='<button id="construct">Play sewing reveal</button><input id="progress" type="range" min="0" max="1" step=".001" value="1">' if construction else ''
    shader_js=r'''
function installReveal(mesh){
  if(!mesh.isMesh || !mesh.geometry?.attributes?.uv) return;
  const maxV=Number(mesh.userData?.reveal_v_max||4.0);
  const materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];
  materials.forEach(material=>{
    material.transparent=true; material.alphaTest=.04;
    material.onBeforeCompile=shader=>{
      shader.uniforms.uReveal={value:reveal}; shader.uniforms.uRevealMax={value:maxV};
      shader.vertexShader=shader.vertexShader.replace('#include <uv_pars_vertex>','#include <uv_pars_vertex>\nvarying float vGarmentReveal;\nuniform float uRevealMax;').replace('#include <uv_vertex>','#include <uv_vertex>\nvGarmentReveal = uv.y / max(uRevealMax, 0.0001);');
      shader.fragmentShader=shader.fragmentShader.replace('#include <uv_pars_fragment>','#include <uv_pars_fragment>\nvarying float vGarmentReveal;\nuniform float uReveal;').replace('#include <alphatest_fragment>','float stitchWave = 0.012 * sin(vGarmentReveal * 120.0);\nif (vGarmentReveal > uReveal + stitchWave) discard;\n#include <alphatest_fragment>');
      material.userData.revealShader=shader;
    };
    material.needsUpdate=true;
  });
}
function setReveal(value){reveal=value; if(current)current.traverse(o=>{if(o.isMesh){const ms=Array.isArray(o.material)?o.material:[o.material];ms.forEach(m=>{if(m.userData?.revealShader)m.userData.revealShader.uniforms.uReveal.value=value})}})}
'''
    return textwrap.dedent(f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>:root{{font-family:Inter,system-ui;color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;background:#0b0e13;color:#eef3f8}}#app{{display:grid;grid-template-columns:minmax(0,1fr) 330px;height:100vh}}#view{{position:relative;min-width:0}}canvas{{display:block;width:100%;height:100%}}aside{{padding:18px;background:#111720;border-left:1px solid #283342;overflow:auto}}h1{{font-size:19px;margin:0 0 4px}}.sub{{font-size:12px;opacity:.65;margin-bottom:15px}}section{{border-top:1px solid #283342;padding:13px 0}}button,select,input{{width:100%;padding:9px;border-radius:8px;border:1px solid #3a4b60;background:#1a2430;color:#eef3f8;margin:3px 0}}.row{{display:grid;grid-template-columns:1fr 1fr;gap:7px}}.layer{{display:flex;gap:8px;align-items:center}}.layer input{{width:auto}}.layer label{{font-size:13px;flex:1}}</style>
<script type="importmap">{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.179.1/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.179.1/examples/jsm/"}}}}</script></head>
<body><div id="app"><main id="view"></main><aside><h1>{title}</h1><div class="sub">Adaptive render surfaces · separate simulation cages · continuous coverage reveal</div><section><input id="file" type="file" accept=".glb"><button id="sample">Load clothing-system.glb</button></section><section><select id="scene"></select><div class="row"><button id="play">Play motion</button><button id="pause">Pause</button></div>{extra_controls}</section><section><div id="layers"></div></section><section><div class="row"><button id="wire">Wireframe</button><button id="skeleton">Skeleton</button></div></section></aside></div>
<script type="module">
import * as THREE from 'three'; import {{OrbitControls}} from 'three/addons/controls/OrbitControls.js'; import {{GLTFLoader}} from 'three/addons/loaders/GLTFLoader.js';
const host=document.querySelector('#view'),renderer=new THREE.WebGLRenderer({{antialias:true}});renderer.setPixelRatio(devicePixelRatio);renderer.setSize(host.clientWidth,host.clientHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;host.append(renderer.domElement);
const world=new THREE.Scene();world.background=new THREE.Color(0x141a22);const camera=new THREE.PerspectiveCamera(38,host.clientWidth/host.clientHeight,.03,100);camera.position.set(3.4,2.2,5);const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;world.add(new THREE.HemisphereLight(0xdce8ff,0x3a2d28,2.3));const key=new THREE.DirectionalLight(0xffe4c6,3);key.position.set(-3,5,4);world.add(key);
let gltf,current,mixer,reveal=1,playingReveal=false,helper=[];const loader=new GLTFLoader(),clock=new THREE.Clock(),sceneSel=document.querySelector('#scene'),layers=document.querySelector('#layers');
{shader_js}
function clear(){{if(current)world.remove(current);helper.forEach(h=>world.remove(h));helper=[];layers.innerHTML='';sceneSel.innerHTML='';mixer=null}}
function fit(){{const box=new THREE.Box3().setFromObject(current);if(box.isEmpty())return;const sphere=box.getBoundingSphere(new THREE.Sphere());controls.target.copy(sphere.center);camera.position.copy(sphere.center).add(new THREE.Vector3(sphere.radius*1.5,sphere.radius*.6,sphere.radius*2.4));camera.near=Math.max(.01,sphere.radius/100);camera.far=sphere.radius*100;camera.updateProjectionMatrix()}}
function showScene(i){{if(current)world.remove(current);current=gltf.scenes[i];world.add(current);current.traverse(o=>{{if(o.isMesh){{installReveal(o);o.castShadow=true}}}});mixer=new THREE.AnimationMixer(current);if(gltf.animations[0])mixer.clipAction(gltf.animations[0]).play();layers.innerHTML='';current.traverse(o=>{{if(o.isMesh){{const row=document.createElement('div');row.className='layer';const cb=document.createElement('input');cb.type='checkbox';cb.checked=o.visible;cb.onchange=()=>o.visible=cb.checked;const label=document.createElement('label');label.textContent=o.name||o.userData?.asset_id||'mesh';row.append(cb,label);layers.append(row)}}}});setReveal(reveal);fit()}}
function install(g){{clear();gltf=g;g.scenes.forEach((s,i)=>{{const o=document.createElement('option');o.value=i;o.textContent=s.name||`Scene ${{i+1}}`;sceneSel.append(o)}});showScene(0)}}
function load(buffer){{loader.parse(buffer,'',install,console.error)}}
document.querySelector('#file').onchange=e=>e.target.files[0]?.arrayBuffer().then(load);document.querySelector('#sample').onclick=async()=>load(await (await fetch('../clothing-system.glb')).arrayBuffer());sceneSel.onchange=e=>showScene(+e.target.value);document.querySelector('#play').onclick=()=>mixer&&(mixer.timeScale=1);document.querySelector('#pause').onclick=()=>mixer&&(mixer.timeScale=0);document.querySelector('#wire').onclick=()=>current?.traverse(o=>{{if(o.isMesh){{const ms=Array.isArray(o.material)?o.material:[o.material];ms.forEach(m=>m.wireframe=!m.wireframe)}}}});document.querySelector('#skeleton').onclick=()=>{{const h=new THREE.SkeletonHelper(current);world.add(h);helper.push(h)}};
const construct=document.querySelector('#construct'),progress=document.querySelector('#progress');if(progress)progress.oninput=e=>{{playingReveal=false;setReveal(+e.target.value)}};if(construct)construct.onclick=()=>{{reveal=0;playingReveal=true;setReveal(0)}};
addEventListener('resize',()=>{{camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix();renderer.setSize(host.clientWidth,host.clientHeight)}});renderer.setAnimationLoop(()=>{{const dt=clock.getDelta();if(mixer)mixer.update(dt);if(playingReveal){{reveal=Math.min(1,reveal+dt*.22);setReveal(reveal);if(progress)progress.value=String(reveal);if(reveal>=1)playingReveal=false}}controls.update();renderer.render(world,camera)}});
</script></body></html>''')


def viewer_html()->str:
    return _shell(False)


def construction_viewer_html()->str:
    return _shell(True)
