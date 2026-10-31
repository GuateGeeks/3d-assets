import * as THREE from 'three';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {ResourceScope,type Asset,type Channel} from './runtime';
const material=(color:number,metalness=.1)=>new THREE.MeshStandardMaterial({color,metalness,roughness:.4});
function mesh(root:THREE.Object3D,geometry:THREE.BufferGeometry,mat:THREE.Material,x=0,y=0,z=0){
 const m=new THREE.Mesh(geometry,mat);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;root.add(m);return m;
}
export function base(root:THREE.Group,scope:ResourceScope,channels:Channel[],anchors:Record<string,THREE.Vector3>,set:Asset['set'],clips:THREE.AnimationClip[]=[],mixer?:THREE.AnimationMixer):Asset{
 scope.track(root);
 // Scene time controls repetition. Every clip samples once and holds its endpoint.
 const asset:Asset={root,channels,anchors,clips,clipIndex:0,set,
  setClip(index){if(mixer&&clips[index]){this.clipIndex=index;mixer.stopAllAction();const action=mixer.clipAction(clips[index]);action.reset();action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play()}},
  seek(time){if(mixer&&clips[this.clipIndex]){const action=mixer.clipAction(clips[this.clipIndex]);action.paused=false;action.enabled=true;mixer.setTime(THREE.MathUtils.clamp(time,0,clips[this.clipIndex].duration))}},
  dispose(){mixer?.stopAllAction();mixer?.uncacheRoot(root);scope.dispose();root.removeFromParent()}};
 asset.setClip(0);return asset;
}
export function createBuiltin(kind:string):Asset{
 const root=new THREE.Group(),scope=new ResourceScope();
 if(kind==='button'){
  const dark=material(0x263444,.6),metal=material(0x91a2b0,.7),accent=material(0xf1a65a);
  mesh(root,new THREE.CylinderGeometry(.57,.62,.24,48),dark,0,.12);
  mesh(root,new THREE.TorusGeometry(.47,.05,12,48),metal,0,.265).rotation.x=Math.PI/2;
  const cap=mesh(root,new THREE.CylinderGeometry(.42,.45,.20,48),accent,0,.34);
  mesh(root,new THREE.BoxGeometry(.15,.035,.45),metal,0,.025,.66);
  return base(root,scope,['pressed'],{control:new THREE.Vector3(0,.58,0)},(c,v)=>{if(c==='pressed')cap.position.y=.34-.12*v});
 }
 if(kind==='servo'){
  const body=material(0x344e66,.4),metal=material(0xc0cbd2,.7),dark=material(0x15212e,.4);
  mesh(root,new THREE.BoxGeometry(1,.64,.65),body,0,.32);
  mesh(root,new THREE.BoxGeometry(1.32,.1,.64),body,0,.23);
  for(const x of [-.58,.58])mesh(root,new THREE.CylinderGeometry(.045,.045,.12,16),dark,x,.30);
  mesh(root,new THREE.CylinderGeometry(.17,.17,.17,32),metal,0,.72);
  const pivot=new THREE.Group();pivot.position.y=.84;root.add(pivot);
  mesh(pivot,new THREE.BoxGeometry(.85,.07,.16),metal,.28);
  mesh(pivot,new THREE.CylinderGeometry(.08,.08,.08,20),dark,.6,.01);
  return base(root,scope,['angle'],{control:new THREE.Vector3(0,1.02,0)},(c,v)=>{if(c==='angle')pivot.rotation.y=THREE.MathUtils.degToRad(v)});
 }
 if(kind!=='character')throw new Error('Unknown built-in asset');
 const hips=new THREE.Bone();hips.name='Hips';hips.position.y=.85;
 const spine=new THREE.Bone();spine.name='Spine';spine.position.y=.35;hips.add(spine);
 const head=new THREE.Bone();head.name='Head';head.position.y=.58;spine.add(head);
 const left=new THREE.Bone();left.name='LeftArm';left.position.set(-.39,.28,0);spine.add(left);
 const right=new THREE.Bone();right.name='RightArm';right.position.set(.39,.28,0);spine.add(right);
 const ll=new THREE.Bone();ll.name='LeftLeg';ll.position.x=-.17;hips.add(ll);
 const rl=new THREE.Bone();rl.name='RightLeg';rl.position.x=.17;hips.add(rl);root.add(hips);
 const bones=[hips,spine,head,left,right,ll,rl];
 const parts:[number,number[],number[]][]=[
  [0,[.45,.24,.34],[0,.88,0]],[1,[.64,.55,.35],[0,1.25,0]],[2,[.48,.44,.40],[0,1.84,0]],
  [3,[.18,.61,.22],[-.44,1.22,0]],[4,[.18,.61,.22],[.44,1.22,0]],
  [5,[.23,.72,.27],[-.17,.47,0]],[6,[.23,.72,.27],[.17,.47,0]],
  [5,[.25,.13,.39],[-.17,.09,.06]],[6,[.25,.13,.39],[.17,.09,.06]]];
 const geometries=parts.map(([bone,size,pos])=>{
  const g=new THREE.BoxGeometry(...size as [number,number,number]);g.translate(...pos as [number,number,number]);
  const n=g.getAttribute('position').count,indices=new Uint16Array(n*4),weights=new Float32Array(n*4);
  for(let i=0;i<n;i++){indices[i*4]=bone;weights[i*4]=1}
  g.setAttribute('skinIndex',new THREE.Uint16BufferAttribute(indices,4));g.setAttribute('skinWeight',new THREE.Float32BufferAttribute(weights,4));return g;
 });
 const geometry=mergeGeometries(geometries)!;geometries.forEach(g=>g.dispose());
 const skin=new THREE.SkinnedMesh(geometry,material(0xd3dfd9,.25));skin.castShadow=true;root.add(skin);root.updateMatrixWorld(true);skin.bind(new THREE.Skeleton(bones));
 // Eyes are attached to the head bone and move with the rig.
 for(const x of [-.11,.11])mesh(head,new THREE.SphereGeometry(.042,12,8),material(0x17283b),x,.08,.215);
 const times=[0,1,2,3,4],quats=(angles:number[])=>angles.flatMap(a=>new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),a).toArray());
 const clip=new THREE.AnimationClip('Wave',4,[
  new THREE.QuaternionKeyframeTrack('LeftArm.quaternion',times,quats([0,-1.7,-1.1,-1.7,0])),
  new THREE.QuaternionKeyframeTrack('Head.quaternion',times,quats([0,.12,0,-.12,0]))
 ]);
 const idle=new THREE.AnimationClip('Idle',4,[new THREE.QuaternionKeyframeTrack('Head.quaternion',times,quats([0,.18,0,-.18,0]))]);
 const mixer=new THREE.AnimationMixer(root);mixer.clipAction(clip).play();
 return base(root,scope,[],{control:new THREE.Vector3(0,2.2,0)},()=>{},[clip,idle],mixer);
}
export async function parseGLB(url:string,signal:AbortSignal):Promise<{scene:THREE.Group;animations:THREE.AnimationClip[]}>{
 const response=await fetch(url,{signal});if(!response.ok)throw new Error('GLB request failed: '+response.status);
 const data=await response.arrayBuffer();const loader=new GLTFLoader();
 // GLB may contain textures and buffers internally; prohibit all external dependencies.
 loader.manager.setURLModifier(path=>{if(path.startsWith('blob:')||path.startsWith('data:'))return path;throw new Error('Use a self-contained GLB without external dependencies')});
 const gltf=await loader.parseAsync(data,'');
 return {scene:gltf.scene,animations:gltf.animations};
}
export async function loadGLB(url:string,signal:AbortSignal):Promise<Asset>{
 const gltf=await parseGLB(url,signal);
 const root=new THREE.Group();root.add(gltf.scene);const scope=new ResourceScope();scope.track(root);
 const mixer=new THREE.AnimationMixer(root);if(gltf.animations[0])mixer.clipAction(gltf.animations[0]).play();
 const asset=base(root,scope,[],{control:new THREE.Vector3(0,2,0)},()=>{},gltf.animations,mixer);
 if(signal.aborted){asset.dispose();throw new DOMException('Scene replaced','AbortError')}return asset;
}
