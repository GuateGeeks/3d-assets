import {stageForBounds,stageScale} from './stage';
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import demo from './demo.scene.json';
import {createBuiltin,loadGLB} from './assets';
import {Runtime,ResourceScope,bindHold,projectAnchor,validateScene,type Asset,type Mode,type SceneSpec} from './runtime';
export function mountPreview(host:HTMLElement):()=>void{
 host.innerHTML='<main class="studio"><header><a class="brand" href="./">3D<span>LAB</span></a><span class="divider"></span><span class="subbrand">Scene preview</span><button id="load" class="quiet">Load scene ↗</button></header><section class="workspace"><div class="stage"><div class="stage-heading"><p class="eyebrow">WORKSPACE / 01</p><h1 id="title">Interactive workbench</h1><p id="status" role="status">Preparing scene…</p></div><div id="viewport" tabindex="0" aria-label="3D scene. Drag to orbit, scroll to zoom."><div id="labels"></div></div><div class="stage-foot"><span class="live-dot"></span><span id="view-hint">Drag to orbit · Scroll to zoom</span><button id="frame" class="quiet">Frame scene</button></div></div><aside><p class="eyebrow">SCENE OBJECTS</p><nav id="objects" aria-label="Scene objects"></nav><div class="inspector"><p class="eyebrow">INSPECTOR</p><h2 id="selection">Select an object</h2><p id="description"></p><div id="control"></div><div class="property"><span>Channel value</span><strong data-testid="channel-value" id="value">—</strong></div><div class="property"><span>Animation</span><select id="clip" aria-label="Animation clip"></select></div><p id="ownership" class="hint"></p></div><details class="view-options"><summary>View options</summary><div class="options-grid"><label><input id="anchors" type="checkbox" checked> Anchors</label><label><input id="bounds" type="checkbox"> Bounds</label><label><input id="rig" type="checkbox"> Rig</label><label><input id="loop" type="checkbox" checked> Loop</label><label><input id="allow-motion" type="checkbox"> Allow motion</label><label>Playback speed<select id="speed" aria-label="Playback speed"><option value="0.5">0.5×</option><option value="1" selected>1×</option><option value="2">2×</option></select></label></div><p class="hint" data-testid="diagnostics" id="diagnostics"></p><button id="capture" class="quiet">Capture PNG</button></details><div class="help"><span class="help-mark">i</span><p>Choose an object to inspect its controls. Switch to timeline to play the authored sequence.</p></div></aside></section><footer><div class="transport"><button id="play" aria-label="Play timeline">▶</button><button id="reset" class="quiet" aria-label="Reset scene">↺</button><div class="time"><strong id="clock">0.00</strong><span id="duration"> / 4.00 s</span></div></div><div class="scrubber"><label class="sr-only" for="timeline">Timeline position</label><input id="timeline" type="range" min="0" max="4" step="0.01" value="0"><div class="ticks"><span>0 s</span><span id="end-tick">4 s</span></div></div><label class="mode">Mode<select id="mode" aria-label="Mode"><option value="interactive">Interactive</option><option value="timeline">Timeline</option></select></label></footer><div id="error" role="alert" hidden></div><dialog><form><p class="eyebrow">OPEN A SCENE</p><h2>Load scene</h2><label for="scene-url">Scene URL</label><input id="scene-url" placeholder="project/scene.json" required><p class="hint">A scene JSON URL on this server.</p><div class="dialog-actions"><button type="button" id="close-dialog" class="quiet">Cancel</button><button type="submit">Open scene</button></div></form></dialog></main>';
 const q=<T extends HTMLElement=HTMLElement>(selector:string)=>host.querySelector<T>(selector)!;
 const viewport=q('#viewport'),labels=q('#labels'),error=q('#error');
 const scene=new THREE.Scene();scene.background=new THREE.Color(0xe9ece9);scene.fog=new THREE.Fog(0xe9ece9,12,35);
 const camera=new THREE.PerspectiveCamera(38,1,.05,100);camera.position.set(6.5,5,8);
 let renderer:THREE.WebGLRenderer;
 try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:false})}catch(e){error.hidden=false;error.textContent='WebGL is unavailable. Enable hardware acceleration to preview this scene.';return()=>host.replaceChildren()}
 renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.2;
 renderer.domElement.setAttribute('aria-hidden','true');viewport.prepend(renderer.domElement);
 const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,.6,0);controls.enableDamping=false;controls.maxPolarAngle=Math.PI/2-.03;controls.minDistance=2;controls.maxDistance=22;
 scene.add(new THREE.HemisphereLight(0xf5f8ff,0xa3a99f,3));
 const sun=new THREE.DirectionalLight(0xfff4e3,4);sun.position.set(-3,7,5);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);sun.shadow.camera.left=-8;sun.shadow.camera.right=8;sun.shadow.camera.top=8;sun.shadow.camera.bottom=-8;sun.shadow.normalBias=.03;scene.add(sun);
 const scope=new ResourceScope();scope.own(sun.shadow);
 const ground=new THREE.Mesh(scope.own(new THREE.PlaneGeometry(200,200)),scope.own(new THREE.MeshStandardMaterial({color:0xdde2dc,roughness:.9})));ground.rotation.x=-Math.PI/2;ground.position.y=-.012;ground.receiveShadow=true;scene.add(ground);
 const grid=new THREE.GridHelper(30,60,0xbdc9bf,0xd0d8cf);grid.position.y=-.008;scene.add(grid);scope.own(grid.geometry);for(const m of Array.isArray(grid.material)?grid.material:[grid.material])scope.own(m);
 let runtime:Runtime|undefined,selected='',disposed=false,generation=0,requestGeneration=0,loadController:AbortController|undefined,jsonController:AbortController|undefined,unbindHold:(()=>void)|undefined;
 const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
 const listeners:(()=>void)[]=[];const on=(target:EventTarget,type:string,fn:EventListener)=>{target.addEventListener(type,fn);listeners.push(()=>target.removeEventListener(type,fn))};
 const timeline=q<HTMLInputElement>('#timeline'),mode=q<HTMLSelectElement>('#mode'),play=q<HTMLButtonElement>('#play'),dialog=q<HTMLDialogElement>('dialog');
 function fail(e:unknown){if(disposed||(e instanceof DOMException&&e.name==='AbortError'))return;error.hidden=false;error.textContent=e instanceof Error?e.message:String(e)}
 function sync(){
  if(!runtime)return;timeline.value=String(runtime.time);q('#clock').textContent=runtime.time.toFixed(2);
  play.textContent=runtime.playing?'Ⅱ':'▶';play.setAttribute('aria-label',runtime.playing?'Pause timeline':'Play timeline');
  const a=runtime.assets.get(selected);let value='—';
  if(a?.channels.includes('pressed'))value=runtime.value(selected,'pressed')>=.5?'Pressed':'Released';
  if(a?.channels.includes('angle'))value=Math.round(runtime.value(selected,'angle'))+'°';
  q('#value').textContent=value;const slider=q<HTMLInputElement>('#angle');if(slider)slider.value=String(runtime.value(selected,'angle'));
 }
 function select(id:string){
  if(!runtime)return;unbindHold?.();selected=id;
  for(const node of q('#objects').querySelectorAll('button'))node.setAttribute('aria-pressed',String(node.dataset.id===id));
  for(const node of labels.querySelectorAll('button'))node.classList.toggle('selected',node.dataset.id===id);
  const asset=runtime.assets.get(id)!;q('#selection').textContent=id;const clip=q<HTMLSelectElement>('#clip');clip.replaceChildren();asset.clips.forEach((c,index)=>{const option=document.createElement('option');option.value=String(index);option.textContent=c.name;clip.append(option)});if(!asset.clips.length){const none=document.createElement('option');none.value='0';none.textContent='None';clip.append(none)}clip.value=String(asset.clipIndex);clip.disabled=!asset.clips.length;
  const channel=asset.channels[0],owner=runtime.owner(id,channel),owned=!!owner;
  q('#description').textContent=channel==='pressed'?'A momentary mechanical switch.':channel==='angle'?'A rotary actuator with a moving horn.':'An articulated character with a skeletal animation clip.';
  q('#ownership').textContent=owner?.kind==='timeline'?'Timeline controls this channel.':owner?owner.source+' controls this channel.':reduced.matches?'Reduced motion: use the scrubber to inspect each pose.':'Interactive controls are ready.';
  const control=q('#control');control.replaceChildren();
  if(channel==='pressed'){
   const b=document.createElement('button');b.textContent='Hold button';b.className='hold';b.disabled=owned;control.append(b);
   unbindHold=bindHold(b,window,v=>{if(!b.disabled){runtime?.input(id,'pressed',v);sync()}});
  }else if(channel==='angle'){
   const label=document.createElement('label');label.textContent='Servo angle';label.htmlFor='angle';
   const slider=document.createElement('input');slider.id='angle';slider.type='range';slider.min='-180';slider.max='180';slider.step='1';slider.disabled=owned;slider.value=String(runtime.value(id,'angle'));slider.addEventListener('input',()=>{runtime?.input(id,'angle',Number(slider.value));sync()});control.append(label,slider);
  }else{const p=document.createElement('p');p.className='hint';p.textContent='Scrub the timeline to inspect the selected clip.';control.append(p)}
  sync();
 }
 // The stage (camera near, zoom limits, shadow, fog, grid) follows the scene's world size; scenes >= 2 m keep the original constants.
 function applyStage(longest:number){
  const stage=stageForBounds(longest),f=stageScale(longest);
  camera.near=stage.near;camera.far=100*f;camera.updateProjectionMatrix();
  controls.minDistance=stage.minDistance;controls.maxDistance=stage.maxDistance;
  sun.position.set(-3,7,5).multiplyScalar(f);const sc=sun.shadow.camera;sc.left=-stage.shadowExtent;sc.right=stage.shadowExtent;sc.top=stage.shadowExtent;sc.bottom=-stage.shadowExtent;sc.near=.5*f;sc.far=500*f;sc.updateProjectionMatrix();sun.shadow.normalBias=.03*f;
  (scene.fog as THREE.Fog).near=stage.fogNear;(scene.fog as THREE.Fog).far=stage.fogFar;
  grid.scale.setScalar(stage.gridSize/30);ground.scale.setScalar(f);ground.position.y=stage.groundY;grid.position.y=stage.gridY;
  return stage;
 }
 function frame(){if(!runtime)return;if(!runtime.assets.size){applyStage(0);return}const box=new THREE.Box3();for(const a of runtime.assets.values())box.expandByObject(a.root);const center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3());const stage=applyStage(Math.max(size.x,size.y,size.z));const aspect=viewport.clientWidth/Math.max(viewport.clientHeight,1);const distance=Math.max(size.y,size.x/aspect,size.z,stage.frameFloor)/(2*Math.tan(THREE.MathUtils.degToRad(camera.fov/2)))*1.55;controls.target.copy(center);camera.position.copy(center).add(new THREE.Vector3(.7,.55,1).normalize().multiplyScalar(distance));controls.update()}
 async function load(raw:unknown,baseURL:string){
  const spec=validateScene(raw),ticket=++generation;loadController?.abort();const controller=new AbortController();loadController=controller;
  const next=new Runtime(spec,reduced.matches&&!q<HTMLInputElement>('#allow-motion').checked);next.speed=Number(q<HTMLSelectElement>('#speed').value);next.loop=q<HTMLInputElement>('#loop').checked;
  try{
   for(const i of spec.instances){
    const asset:Asset=['button','servo','character'].includes(i.asset)?createBuiltin(i.asset):await loadGLB(new URL(i.asset,baseURL).href,controller.signal);
    if(disposed||ticket!==generation){asset.dispose();next.dispose();return}next.add(i.id,asset);
   }
   if(disposed||ticket!==generation){next.dispose();return}
   unbindHold?.();clearOverlays();runtime?.dispose();runtime=next;for(const a of next.assets.values())scene.add(a.root);
   q('#title').textContent=spec.title;q('#status').textContent='Ready · '+spec.instances.length+' object'+(spec.instances.length===1?'':'s');
   q('#duration').textContent=' / '+spec.duration.toFixed(2)+' s';q('#end-tick').textContent=spec.duration+' s';timeline.max=String(spec.duration);mode.value=spec.mode;
   q('#objects').replaceChildren();labels.replaceChildren();
   spec.instances.forEach((i,index)=>{
    const b=document.createElement('button');b.dataset.id=i.id;b.setAttribute('aria-label',i.id+' / '+String(index+1).padStart(2,'0'));
    const name=document.createElement('span');name.textContent=i.id;const number=document.createElement('small');number.textContent=String(index+1).padStart(2,'0');b.append(name,number);b.addEventListener('click',()=>select(i.id));q('#objects').append(b);
    const tag=document.createElement('button');tag.className='anchor-label';tag.dataset.id=i.id;tag.textContent=i.id;tag.addEventListener('click',()=>select(i.id));labels.append(tag);
   });
   if(spec.instances[0])select(spec.instances[0].id);else{selected='';q('#selection').textContent='Empty scene';q('#control').replaceChildren();sync()}
   error.hidden=true;refreshOverlays();frame();
  }catch(e){next.dispose();if(!(e instanceof DOMException&&e.name==='AbortError'))throw e}
 }
 async function openURL(relative:string){const request=++requestGeneration;jsonController?.abort();const controller=new AbortController();jsonController=controller;
  const url=new URL(relative,location.href);if(url.origin!==location.origin||!['http:','https:'].includes(url.protocol))throw new Error('Choose a scene URL on this server.');
  const response=await fetch(url,{signal:controller.signal});if(request!==requestGeneration||disposed)return;if(!response.ok||!response.headers.get('content-type')?.includes('json'))throw new Error('Scene request failed: '+response.status);const raw=await response.json();if(request!==requestGeneration||disposed)return;await load(raw,url.href);
 }
 on(q('#load'),'click',()=>dialog.showModal());on(q('#close-dialog'),'click',()=>dialog.close());
 on(q('form'),'submit',e=>{e.preventDefault();dialog.close();openURL(q<HTMLInputElement>('#scene-url').value).catch(fail)});
 on(q('#frame'),'click',frame);on(mode,'change',()=>{runtime?.setMode(mode.value as Mode);if(selected)select(selected)});
 on(timeline,'input',()=>{runtime?.seek(Number(timeline.value));sync()});
 on(play,'click',()=>{if(runtime){if(runtime.playing)runtime.playing=false;else runtime.play();sync()}});
 on(q('#reset'),'click',()=>{if(runtime){runtime.reset();if(selected)select(selected);sync()}});
 on(window,'blur',()=>{runtime?.release();if(runtime)runtime.playing=false;sync()});
 on(document,'visibilitychange',()=>{if(document.hidden){runtime?.release();if(runtime)runtime.playing=false;sync()}});
 on(reduced,'change',()=>{if(runtime){runtime.playing=false;runtime.reducedMotion=reduced.matches&&!q<HTMLInputElement>('#allow-motion').checked}sync()});
 let overlays:THREE.Object3D[]=[];let overlayScope=new ResourceScope();
 function clearOverlays(){for(const o of overlays)o.removeFromParent();overlayScope.dispose();overlayScope=new ResourceScope();overlays=[]}
 function refreshOverlays(){clearOverlays();if(!runtime)return;for(const a of runtime.assets.values()){
 if(q<HTMLInputElement>('#bounds').checked){const h=new THREE.BoxHelper(a.root,0x859777);scene.add(h);overlays.push(h);overlayScope.own(h.geometry);overlayScope.own(h.material)}
 if(q<HTMLInputElement>('#rig').checked){const h=new THREE.SkeletonHelper(a.root);scene.add(h);overlays.push(h);overlayScope.own(h.geometry);for(const m of Array.isArray(h.material)?h.material:[h.material])overlayScope.own(m)}
 }}
 on(q('#bounds'),'change',refreshOverlays);on(q('#rig'),'change',refreshOverlays);on(q('#anchors'),'change',()=>{labels.style.visibility=q<HTMLInputElement>('#anchors').checked?'visible':'hidden'});
 on(q('#clip'),'change',()=>{runtime?.assets.get(selected)?.setClip(Number(q<HTMLSelectElement>('#clip').value));runtime?.seek(runtime.time)});
 on(q('#speed'),'change',()=>{if(runtime)runtime.speed=Number(q<HTMLSelectElement>('#speed').value)});on(q('#loop'),'change',()=>{if(runtime)runtime.loop=q<HTMLInputElement>('#loop').checked});
 on(q('#allow-motion'),'change',()=>{if(runtime){runtime.reducedMotion=reduced.matches&&!q<HTMLInputElement>('#allow-motion').checked;if(runtime.reducedMotion)runtime.playing=false}sync()});
 function download(blob:Blob,name:string){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url)}
 on(q('#capture'),'click',()=>{
  if(!runtime)return;
  scene.updateMatrixWorld(true);camera.updateMatrixWorld(true);renderer.render(scene,camera);
  const gl=renderer.getContext(),stamp=new Date().toISOString(),name='3d-lab-'+stamp.replace(/[:.]/g,'-');
  const size=renderer.getDrawingBufferSize(new THREE.Vector2());
  // Freeze the receipt beside the pixels before asynchronous PNG encoding.
  const receipt={schemaVersion:1,kind:'preview-capture',capturedAt:stamp,
   viewport:{cssWidth:renderer.domElement.clientWidth,cssHeight:renderer.domElement.clientHeight,pixelWidth:size.x,pixelHeight:size.y,devicePixelRatio:window.devicePixelRatio,rendererPixelRatio:renderer.getPixelRatio()},
   camera:{type:camera.type,position:camera.position.toArray(),quaternion:camera.quaternion.toArray(),target:controls.target.toArray(),fov:camera.fov,aspect:camera.aspect,near:camera.near,far:camera.far,matrixWorld:camera.matrixWorld.toArray(),projectionMatrix:camera.projectionMatrix.toArray()},
   renderer:{webglVersion:gl.getParameter(gl.VERSION),renderer:gl.getParameter(gl.RENDERER),vendor:gl.getParameter(gl.VENDOR),antialias:gl.getContextAttributes()?.antialias,outputColorSpace:renderer.outputColorSpace,toneMapping:renderer.toneMapping,toneMappingExposure:renderer.toneMappingExposure,shadows:renderer.shadowMap.enabled,shadowType:renderer.shadowMap.type},
   runtime:{three:THREE.REVISION,preview:'1.0.0',userAgent:navigator.userAgent},
   overlays:{anchors:q<HTMLInputElement>('#anchors').checked,bounds:q<HTMLInputElement>('#bounds').checked,rig:q<HTMLInputElement>('#rig').checked},
   scene:{spec:structuredClone(runtime.spec),time:runtime.time,mode:runtime.mode,speed:runtime.speed,loop:runtime.loop,playing:runtime.playing,reducedMotion:runtime.reducedMotion,selected,
    instances:[...runtime.assets].map(([id,a])=>({id,position:a.root.position.toArray(),rotation:a.root.rotation.toArray(),scale:a.root.scale.toArray(),clipIndex:a.clipIndex,clip:a.clips[a.clipIndex]?.name??null,channels:Object.fromEntries(a.channels.map(c=>[c,runtime!.value(id,c)]))}))}};
  renderer.domElement.toBlob(blob=>{if(!blob||disposed)return;
   void blob.arrayBuffer().then(bytes=>crypto.subtle.digest('SHA-256',bytes)).then(hash=>{
    if(disposed)return;const image={name:name+'.png',sha256:Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join(''),bytes:blob.size};
    download(blob,image.name);download(new Blob([JSON.stringify({...receipt,image},null,2)],{type:'application/json'}),name+'.json');
   }).catch(fail);
  },'image/png');
 });
 const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2();let startX=0,startY=0;
 on(renderer.domElement,'pointerdown',e=>{const p=e as PointerEvent;startX=p.clientX;startY=p.clientY});
 on(renderer.domElement,'pointerup',e=>{
  const p=e as PointerEvent;if(Math.hypot(p.clientX-startX,p.clientY-startY)>5||!runtime)return;
  const rect=renderer.domElement.getBoundingClientRect();pointer.set((p.clientX-rect.left)/rect.width*2-1,-(p.clientY-rect.top)/rect.height*2+1);raycaster.setFromCamera(pointer,camera);
  const hit=raycaster.intersectObjects([...runtime.assets.values()].map(a=>a.root),true)[0];if(hit){let node:THREE.Object3D|null=hit.object;while(node&&!node.userData.instanceId)node=node.parent;if(node)select(node.userData.instanceId)}
 });
 const resize=new ResizeObserver(()=>{const w=viewport.clientWidth,h=viewport.clientHeight;if(w&&h){renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix()}});resize.observe(viewport);
 let handle=0,last=0;function tick(now:number){if(disposed)return;const dt=last?(now-last)/1000:0;last=now;runtime?.advance(dt);controls.update();scene.updateMatrixWorld();
  if(runtime){for(const tag of labels.querySelectorAll<HTMLElement>('button')){const a=runtime.assets.get(tag.dataset.id!)!;const p=projectAnchor(a.root,a.anchors.control,camera,viewport.clientWidth,viewport.clientHeight);tag.style.transform='translate(-50%,-100%) translate('+p.x+'px,'+p.y+'px)';tag.hidden=!p.visible}sync()}
  for(const o of overlays)if(o instanceof THREE.BoxHelper)o.update();renderer.render(scene,camera);q('#diagnostics').textContent='WebGL 2 · '+renderer.info.render.calls+' draw calls · '+renderer.info.render.triangles.toLocaleString()+' triangles';handle=requestAnimationFrame(tick)
 }handle=requestAnimationFrame(tick);
 const initial=new URLSearchParams(location.search).get('scene');(initial?openURL(initial):load(demo,location.href)).catch(fail);
 return()=>{if(disposed)return;disposed=true;generation++;requestGeneration++;jsonController?.abort();loadController?.abort();cancelAnimationFrame(handle);unbindHold?.();for(const unbind of listeners)unbind();resize.disconnect();controls.dispose();clearOverlays();runtime?.dispose();scope.dispose();renderer.dispose();renderer.forceContextLoss();host.replaceChildren()};
}
