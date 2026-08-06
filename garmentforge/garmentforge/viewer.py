from __future__ import annotations
import textwrap

def viewer_html()->str:
    return textwrap.dedent(r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GarmentForge Textile Inspector</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui;color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b0e13;color:#eef3f8}
#app{display:grid;grid-template-columns:minmax(0,1fr) 340px;height:100vh}#view{min-width:0;position:relative}canvas{display:block;width:100%;height:100%}
aside{padding:18px;background:#111720;border-left:1px solid #283342;overflow:auto}h1{font-size:19px;margin:0 0 3px}.sub{font-size:12px;opacity:.65;margin-bottom:15px}
section{border-top:1px solid #283342;padding:13px 0}button,select,input{width:100%;padding:9px;border-radius:8px;border:1px solid #3a4b60;background:#1a2430;color:#eef3f8;margin:3px 0}
button{cursor:pointer}button:hover{background:#253346}.row{display:grid;grid-template-columns:1fr 1fr;gap:7px}.status{font-size:12px;line-height:1.5}.ok{color:#78e4ad}.warn{color:#f0c875}
.layer{display:flex;gap:8px;align-items:center}.layer input{width:auto}.layer label{font-size:13px;flex:1}.metric{font-size:11px;opacity:.68}
#drop{position:absolute;inset:22px;border:1px dashed #50647c;border-radius:14px;display:grid;place-items:center;pointer-events:none;opacity:.0;transition:.15s;background:#101720cc}
#drop.show{opacity:1}.pill{display:inline-block;padding:4px 7px;border-radius:99px;background:#1d2a38;font-size:10px;margin:2px}
</style><script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.179.1/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.179.1/examples/jsm/"}}</script>
</head><body><div id="app"><main id="view"><div id="drop">Drop a GarmentForge .glb</div></main><aside>
<h1>Textile Inspector</h1><div class="sub">Detachable GLB garments · skinning · secondary textile motion · embedded PBR weave</div>
<section><input id="file" type="file" accept=".glb,model/gltf-binary"><button id="sample">Load packaged clothing-system.glb</button><div id="status" class="status">Choose or drop a GLB.</div></section>
<section><label>Retained scene</label><select id="scene"></select><div class="row"><button id="play">Play motion</button><button id="pause">Pause</button></div></section>
<section><strong>Layers</strong><div id="layers"></div></section>
<section><div class="row"><button id="wire">Wireframe</button><button id="skeleton">Skeleton</button></div><div class="row"><button id="bounds">Bounds</button><button id="reset">Reset camera</button></div></section>
<section><label>Environment light</label><input id="light" type="range" min="0" max="5" step=".1" value="2.3"></section>
<section><span class="pill">dressed</span><span class="pill">body-only</span><span class="pill">detached gallery</span><span class="pill">10 embedded maps</span></section>
</aside></div>
<script type="module">
import * as THREE from 'three'; import {OrbitControls} from 'three/addons/controls/OrbitControls.js'; import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const host=document.querySelector('#view'), renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(devicePixelRatio);renderer.setSize(host.clientWidth,host.clientHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.shadowMap.enabled=true;host.prepend(renderer.domElement);
const world=new THREE.Scene();world.background=new THREE.Color(0x141a22);const camera=new THREE.PerspectiveCamera(38,host.clientWidth/host.clientHeight,.03,100);camera.position.set(3.4,2.2,5.0);const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,1.0,0);controls.enableDamping=true;
const hemi=new THREE.HemisphereLight(0xdce8ff,0x3a2d28,2.3);world.add(hemi);const key=new THREE.DirectionalLight(0xffe4c6,3.0);key.position.set(-3,5,4);key.castShadow=true;world.add(key);const floor=new THREE.Mesh(new THREE.CircleGeometry(4,96),new THREE.MeshStandardMaterial({color:0x27313d,roughness:.85}));floor.rotation.x=-Math.PI/2;floor.position.y=-.42;floor.receiveShadow=true;world.add(floor);
let gltf,current,mixer,helper=[],paused=false;const clock=new THREE.Clock(), loader=new GLTFLoader();const status=document.querySelector('#status'),layers=document.querySelector('#layers'),sceneSel=document.querySelector('#scene');
function clear(){if(current)world.remove(current);helper.forEach(h=>world.remove(h));helper=[];layers.innerHTML='';sceneSel.innerHTML='';mixer=null}
function install(g){clear();gltf=g;g.scenes.forEach((s,i)=>{const o=document.createElement('option');o.value=i;o.textContent=s.name||`Scene ${i+1}`;sceneSel.appendChild(o)});showScene(g.scene===g.scenes[0]?0:g.scenes.indexOf(g.scene));status.innerHTML=`<span class="ok">GLB opened</span><br>${g.scenes.length} retained scene states · ${g.animations.length} animation clip(s)`}
function showScene(i){if(current)world.remove(current);current=gltf.scenes[i];world.add(current);current.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true}});mixer=new THREE.AnimationMixer(current);if(gltf.animations[0])mixer.clipAction(gltf.animations[0]).play();buildLayers();fit()}
function buildLayers(){layers.innerHTML='';const named=[];current.traverse(o=>{if(o.isMesh&&!named.some(x=>x.name===o.name))named.push(o)});named.forEach(o=>{const row=document.createElement('div');row.className='layer';const cb=document.createElement('input');cb.type='checkbox';cb.checked=o.visible;cb.onchange=()=>o.visible=cb.checked;const label=document.createElement('label');label.textContent=o.name||'Unnamed mesh';const m=document.createElement('span');m.className='metric';m.textContent=o.userData?.asset_id?'asset':'';row.append(cb,label,m);layers.append(row)})}
function fit(){const box=new THREE.Box3().setFromObject(current);if(box.isEmpty())return;const sphere=box.getBoundingSphere(new THREE.Sphere());controls.target.copy(sphere.center);camera.position.copy(sphere.center).add(new THREE.Vector3(sphere.radius*1.5,sphere.radius*.6,sphere.radius*2.4));camera.near=Math.max(.01,sphere.radius/100);camera.far=sphere.radius*100;camera.updateProjectionMatrix()}
async function loadArray(buffer){loader.parse(buffer,'',install,e=>status.innerHTML='<span class="warn">Load failed:</span> '+e.message)}
document.querySelector('#file').onchange=e=>e.target.files[0]?.arrayBuffer().then(loadArray);document.querySelector('#sample').onclick=async()=>{try{loadArray(await (await fetch('../clothing-system.glb')).arrayBuffer())}catch(e){status.textContent='Serve this folder locally or choose the GLB with the file picker.'}};
sceneSel.onchange=e=>showScene(+e.target.value);document.querySelector('#play').onclick=()=>{paused=false;if(mixer)mixer.timeScale=1};document.querySelector('#pause').onclick=()=>{paused=!paused;if(mixer)mixer.timeScale=paused?0:1};document.querySelector('#wire').onclick=()=>current?.traverse(o=>{if(o.isMesh){const mats=Array.isArray(o.material)?o.material:[o.material];mats.forEach(m=>m.wireframe=!m.wireframe)}});
document.querySelector('#skeleton').onclick=()=>{const h=new THREE.SkeletonHelper(current);world.add(h);helper.push(h)};document.querySelector('#bounds').onclick=()=>{const h=new THREE.BoxHelper(current,0x69d6ff);world.add(h);helper.push(h)};document.querySelector('#reset').onclick=fit;document.querySelector('#light').oninput=e=>hemi.intensity=+e.target.value;
for(const event of ['dragenter','dragover'])addEventListener(event,e=>{e.preventDefault();document.querySelector('#drop').classList.add('show')});for(const event of ['dragleave','drop'])addEventListener(event,e=>{e.preventDefault();document.querySelector('#drop').classList.remove('show')});addEventListener('drop',e=>e.dataTransfer.files[0]?.arrayBuffer().then(loadArray));
addEventListener('resize',()=>{camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix();renderer.setSize(host.clientWidth,host.clientHeight)});renderer.setAnimationLoop(()=>{const dt=clock.getDelta();if(mixer)mixer.update(dt);controls.update();renderer.render(world,camera)});
</script></body></html>''')
