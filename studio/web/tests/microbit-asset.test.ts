import {describe,it,expect,beforeAll} from 'vitest';
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import contract from '../../examples/microbit/node-contract.json';
import {createMicrobit} from '../src/microbit';
import type {Asset} from '../src/runtime';
// The REAL Blender export (creation-lab run 003-9621bf5caaca) goes through the same GLTFLoader settings as the preview.
// There are no Node typings in this project, so the two Node built-ins are loaded through an untyped dynamic import.
const builtin=async(name:string)=>(await import(/* @vite-ignore */ name)) as any;
const GLB=new URL('../../examples/microbit/microbit.glb',import.meta.url);
async function parseReal():Promise<THREE.Group>{
 const {readFileSync}=await builtin('node:fs'),bytes=readFileSync(GLB) as Uint8Array;
 const data=bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength) as ArrayBuffer;
 const loader=new GLTFLoader();loader.manager.setURLModifier(path=>{if(path.startsWith('blob:')||path.startsWith('data:'))return path;throw new Error('external dependency')});
 return (await loader.parseAsync(data,'')).scene;
}
const part=(root:THREE.Object3D,id:string)=>{let found:THREE.Object3D|undefined;root.traverse(o=>{if(o.userData.part_id===id)found=o});if(!found)throw new Error('no '+id);return found as THREE.Mesh};
const led=(root:THREE.Object3D,x:number,y:number)=>part(root,`led_${x}_${y}`).material as THREE.MeshStandardMaterial;
const centre=(o:THREE.Object3D)=>new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3());
describe('real Blender micro:bit GLB through the factory',()=>{
 let source:THREE.Group,asset:Asset;
 beforeAll(async()=>{source=await parseReal();asset=createMicrobit(source)});
 it('is the file recorded in PROVENANCE.md and fits the GLB budget',async()=>{
  const {readFileSync}=await builtin('node:fs'),{createHash}=await builtin('node:crypto');
  const bytes=readFileSync(GLB),provenance=readFileSync(new URL('../../examples/microbit/PROVENANCE.md',import.meta.url),'utf8') as string;
  const sha=createHash('sha256').update(bytes).digest('hex');
  expect(provenance).toContain(sha);expect(bytes.length).toBe(1117164);expect(bytes.length).toBeLessThanOrEqual(3145728);
 });
 it('exposes the 28 channels and resolves all 46 contract parts',()=>{
  expect(asset.channels.length).toBe(28);expect(new Set(asset.channels).size).toBe(28);
  expect(asset.parts!.length).toBe(46);expect(contract.parts.length).toBe(46);
  for(const p of contract.parts)expect(part(asset.root,p.id).userData.part_id).toBe(p.id);
  const ids=new Map<string,number>();asset.root.traverse(o=>{const id=o.userData.part_id;if(typeof id==='string')ids.set(id,(ids.get(id)??0)+1)});
  expect(ids.size).toBe(46);for(const n of ids.values())expect(n).toBe(1);
 });
 it('keeps the 25 LED materials distinct, at rest dark with the contract emissive colour',()=>{
  const seen=new Set<THREE.Material>();
  for(let y=0;y<5;y++)for(let x=0;x<5;x++){const m=led(asset.root,x,y);seen.add(m);expect(m.emissiveIntensity).toBe(0);expect('#'+m.emissive.getHexString()).toBe(contract.ledEmissive.color)}
  expect(seen.size).toBe(25);
  // No other part shares an LED material.
  asset.root.traverse(o=>{if(o instanceof THREE.Mesh&&!/^led_/.test(o.userData.part_id))expect(seen.has(o.material as THREE.Material)).toBe(false)});
 });
 it('gives the logo feedback without touching any other material, and the touch tint restores exactly',()=>{
  const logo=part(asset.root,'logo_touch'),mat=logo.material as THREE.MeshStandardMaterial,rest={e:mat.emissive.getHex(),i:mat.emissiveIntensity};
  asset.root.traverse(o=>{if(o instanceof THREE.Mesh&&o!==logo)expect(o.material).not.toBe(mat)});
  asset.set('logo',1);expect(mat.emissive.getHex()).not.toBe(rest.e);
  asset.set('logo',0);expect(mat.emissive.getHex()).toBe(rest.e);expect(mat.emissiveIntensity).toBe(rest.i);
 });
 it("set('led.2.2',255) raises exactly that LED",()=>{
  asset.set('led.2.2',255);
  for(let y=0;y<5;y++)for(let x=0;x<5;x++)expect(led(asset.root,x,y).emissiveIntensity).toBe(x===2&&y===2?contract.ledEmissive.maxIntensity:0);
  asset.set('led.2.2',0);expect(led(asset.root,2,2).emissiveIntensity).toBe(0);
 });
 for(const [channel,cap] of [['a','btn_a_cap'],['b','btn_b_cap']] as const){
  it(`set('${channel}',1) moves ${cap} by pressTravelMeters along its local Y and set('${channel}',0) restores the exact position`,()=>{
   const node=part(asset.root,cap),rest=node.position.clone(),before=centre(node);
   // The Blender Z-up to Y-up export must leave the node unrotated and unscaled, otherwise "local Y" would not be the visual press axis.
   expect(node.quaternion.angleTo(new THREE.Quaternion())).toBeLessThan(1e-6);expect(node.scale.toArray()).toEqual([1,1,1]);
   asset.set(channel,1);
   expect(node.position.x).toBeCloseTo(rest.x,12);expect(node.position.z).toBeCloseTo(rest.z,12);expect(node.position.y).toBeCloseTo(rest.y-contract.pressTravelMeters,9);
   const moved=centre(node).sub(before);expect(moved.x).toBeCloseTo(0,9);expect(moved.z).toBeCloseTo(0,9);expect(moved.y).toBeCloseTo(-contract.pressTravelMeters,9);
   asset.set(channel,0);expect(node.position.equals(rest)).toBe(true);
  });
 }
 it('pick maps buttons, caps and the logo to their channel and the board to nothing',()=>{
  const child=new THREE.Object3D();part(asset.root,'btn_a').add(child);
  expect(asset.pick!(child)).toBe('a');expect(asset.pick!(part(asset.root,'btn_a_cap'))).toBe('a');
  const bChild=new THREE.Object3D();part(asset.root,'btn_b_cap').add(bChild);expect(asset.pick!(bChild)).toBe('b');expect(asset.pick!(part(asset.root,'btn_b'))).toBe('b');
  const lChild=new THREE.Object3D();part(asset.root,'logo_touch').add(lChild);expect(asset.pick!(lChild)).toBe('logo');
  expect(asset.pick!(part(asset.root,'pcb'))).toBeUndefined();expect(asset.pick!(part(asset.root,'led_2_2'))).toBeUndefined();expect(asset.pick!(part(asset.root,'usb'))).toBeUndefined();
 });
 it('picks through the real mesh hierarchy: every mesh under a pickable part maps to its channel, every other mesh to nothing',()=>{
  // Blender exports some parts as several primitives (a Group in three.js), so the raycast hit is a child of the part node.
  const expected:Record<string,string>=contract.pickable,hits=new Map<string,number>();
  asset.root.traverse(o=>{
   if(!(o instanceof THREE.Mesh))return;
   let owner:string|undefined;for(let p:THREE.Object3D|null=o;p&&!owner;p=p.parent)if(typeof p.userData.part_id==='string')owner=p.userData.part_id;
   expect(owner).toBeDefined();expect(asset.pick!(o)).toBe(expected[owner!]);hits.set(owner!,(hits.get(owner!)??0)+1);
  });
  for(const id of Object.keys(expected))expect(hits.get(id)).toBeGreaterThan(0);
 });
 it('a press at the centre of the touch logo ring reaches the logo, not the board below it',()=>{
  // The real logo is an open ring: a ray through its centre would otherwise fall through the hole onto the pcb and press nothing.
  asset.root.updateMatrixWorld(true);
  const box=new THREE.Box3().setFromObject(part(asset.root,'logo_touch')),raycaster=new THREE.Raycaster();let misses=0;
  for(let i=1;i<10;i++)for(let j=1;j<10;j++){
   raycaster.set(new THREE.Vector3(box.min.x+(box.max.x-box.min.x)*i/10,.1,box.min.z+(box.max.z-box.min.z)*j/10),new THREE.Vector3(0,-1,0));
   const hit=raycaster.intersectObject(asset.root,true)[0];if(asset.pick!(hit.object)!=='logo')misses++;
  }
  // Only the corners cut off by the ring's rounded ends may reach the board.
  expect(misses).toBeLessThanOrEqual(4);
  raycaster.set(new THREE.Vector3(...box.getCenter(new THREE.Vector3()).toArray()).setY(.1),new THREE.Vector3(0,-1,0));
  expect(asset.pick!(raycaster.intersectObject(asset.root,true)[0].object)).toBe('logo');
 });
 it('is 51.6 mm long on X, flat on Y with the LED face up, in metres, with no rescale',()=>{
  asset.root.updateMatrixWorld(true);
  const size=new THREE.Box3().setFromObject(asset.root).getSize(new THREE.Vector3());
  expect(Math.abs(size.x-.0516)/.0516).toBeLessThan(.01);
  expect(size.x).toBeGreaterThan(size.z);expect(size.z).toBeGreaterThan(size.y);expect(size.y).toBeLessThan(.0125);
  // Run manifest: 51.6 x 43.25 x 11.65 mm, the USB connector overhanging the 42 mm board edge.
  expect(size.z).toBeCloseTo(.04325,4);expect(size.y).toBeCloseTo(.01165,4);
  expect(asset.root.scale.toArray()).toEqual([1,1,1]);
  const pcb=new THREE.Box3().setFromObject(part(asset.root,'pcb')).getSize(new THREE.Vector3());
  expect(pcb.x).toBeCloseTo(.0516,3);expect(pcb.z).toBeGreaterThan(.040);expect(pcb.z).toBeLessThan(.043);expect(pcb.y).toBeLessThan(.003);
 });
 it('follows the Studio orientation: LED face +Y, edge connector +Z, LED x to the right, y down the board, A left of B, logo above the grid',()=>{
  const c=(id:string)=>centre(part(asset.root,id)),pcb=c('pcb');
  expect(c('led_2_2').y).toBeGreaterThan(pcb.y);expect(c('btn_a').y).toBeGreaterThan(pcb.y);
  expect(c('edge_connector').z).toBeGreaterThan(c('led_2_2').z+.01);
  for(let i=0;i<4;i++){expect(c(`led_${i+1}_2`).x).toBeGreaterThan(c(`led_${i}_2`).x);expect(c(`led_2_${i+1}`).z).toBeGreaterThan(c(`led_2_${i}`).z)}
  expect(c('btn_a').x).toBeLessThan(c('led_0_2').x);expect(c('btn_b').x).toBeGreaterThan(c('led_4_2').x);
  expect(c('logo_touch').z).toBeLessThan(c('led_2_0').z);
  const pins=['pin_0','pin_1','pin_2','pin_3v','pin_gnd'].map(id=>c(id).x);for(let i=0;i<4;i++)expect(pins[i+1]).toBeGreaterThan(pins[i]);
  // The back-face parts are modelled under the board.
  for(const id of ['usb','reset_btn','battery_socket','speaker'])expect(c(id).y).toBeLessThan(pcb.y);
 });
 it('every part has an anchor inside the board footprint and a label',()=>{
  const box=new THREE.Box3().setFromObject(asset.root).expandByScalar(1e-6);
  for(const p of asset.parts!){expect(p.label.length).toBeGreaterThan(0);expect(box.containsPoint(p.anchor)).toBe(true)}
 });
});
