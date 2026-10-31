import {describe,it,expect,vi} from 'vitest';
import * as THREE from 'three';
import contract from '../../examples/microbit/node-contract.json';
import {createMicrobit} from '../src/microbit';
import {makeContractBoard} from './fixtures/contract-board';
const part=(root:THREE.Object3D,id:string)=>{let found:THREE.Object3D|undefined;root.traverse(o=>{if(o.userData.part_id===id)found=o});if(!found)throw new Error('no '+id);return found as THREE.Mesh};
const led=(root:THREE.Object3D,x:number,y:number)=>(part(root,`led_${x}_${y}`).material as THREE.MeshStandardMaterial);
describe('micro:bit node contract',()=>{
 it('lists every spec part exactly once',()=>{
  const ids=contract.parts.map(p=>p.id);expect(new Set(ids).size).toBe(ids.length);expect(ids.length).toBe(46);
  for(const id of ['pcb','edge_connector','pin_3v','pin_gnd','btn_a_cap','btn_b_cap','logo_touch','led_0_0','led_4_4','usb','reset_btn','battery_socket','speaker','mic','mic_led','processor','antenna','accel_compass'])expect(ids).toContain(id);
  for(const p of contract.parts)expect(p.label.length).toBeGreaterThan(0);
 });
 it('fixture builds a board of about 52 x 42 mm',()=>{
  const size=new THREE.Box3().setFromObject(makeContractBoard()).getSize(new THREE.Vector3());
  expect(size.x).toBeCloseTo(.052,3);expect(size.z).toBeCloseTo(.042,3);expect(size.y).toBeLessThan(.01);
 });
});
describe('createMicrobit',()=>{
 it('rejects a board missing led_3_4',()=>{
  const board=makeContractBoard();part(board,'led_3_4').removeFromParent();
  expect(()=>createMicrobit(board)).toThrow(/led_3_4/);
 });
 it('rejects duplicate part_id',()=>{
  const board=makeContractBoard();part(board,'usb').userData.part_id='mic';
  expect(()=>createMicrobit(board)).toThrow(/mic/);
 });
 it('rejects LEDs sharing a material',()=>{
  const board=makeContractBoard();part(board,'led_0_1').material=part(board,'led_0_0').material;
  expect(()=>createMicrobit(board)).toThrow(/distinct material/);
 });
 it('rest state: every LED emissiveIntensity is 0 and emissive color equals the contract color',()=>{
  const asset=createMicrobit(makeContractBoard());
  for(let y=0;y<5;y++)for(let x=0;x<5;x++){const m=led(asset.root,x,y);expect(m.emissiveIntensity).toBe(0);expect('#'+m.emissive.getHexString()).toBe(contract.ledEmissive.color)}
 });
 it("set('led.1.2',255) lights only that LED to maxIntensity; set(...,0) restores 0",()=>{
  const asset=createMicrobit(makeContractBoard());asset.set('led.1.2',255);
  for(let y=0;y<5;y++)for(let x=0;x<5;x++)expect(led(asset.root,x,y).emissiveIntensity).toBe(x===1&&y===2?contract.ledEmissive.maxIntensity:0);
  asset.set('led.1.2',0);expect(led(asset.root,1,2).emissiveIntensity).toBe(0);
 });
 it("set('led.1.2',128) is half intensity",()=>{
  const asset=createMicrobit(makeContractBoard());asset.set('led.1.2',128);
  expect(led(asset.root,1,2).emissiveIntensity).toBeCloseTo(128/255*contract.ledEmissive.maxIntensity,6);
 });
 it("set('a',1) moves btn_a_cap down by pressTravelMeters along local Y; set('a',0) restores the exact original position; btn_b_cap untouched",()=>{
  const board=makeContractBoard(),asset=createMicrobit(board);
  const cap=part(asset.root,'btn_a_cap'),other=part(asset.root,'btn_b_cap'),orig=cap.position.clone(),otherOrig=other.position.clone();
  asset.set('a',1);expect(cap.position.y).toBeCloseTo(orig.y-contract.pressTravelMeters,9);expect(cap.position.x).toBe(orig.x);expect(cap.position.z).toBe(orig.z);expect(other.position.equals(otherOrig)).toBe(true);
  asset.set('a',.5);asset.set('a',1);asset.set('a',0);expect(cap.position.equals(orig)).toBe(true);
 });
 it('logo gives feedback and returns exactly to rest',()=>{
  const asset=createMicrobit(makeContractBoard()),logo=part(asset.root,'logo_touch'),orig=logo.position.clone(),mat=logo.material as THREE.MeshStandardMaterial,rest={e:mat.emissive.getHex(),i:mat.emissiveIntensity};
  asset.set('logo',1);expect(logo.position.y).toBeLessThan(orig.y);expect(mat.emissive.getHex()).not.toBe(rest.e);
  asset.set('logo',0);expect(logo.position.equals(orig)).toBe(true);expect(mat.emissive.getHex()).toBe(rest.e);expect(mat.emissiveIntensity).toBe(rest.i);
 });
 it("pick maps btn_b_cap child -> 'b', logo_touch -> 'logo', pcb -> undefined",()=>{
  const asset=createMicrobit(makeContractBoard());
  const child=new THREE.Object3D();part(asset.root,'btn_b_cap').add(child);
  expect(asset.pick!(child)).toBe('b');expect(asset.pick!(part(asset.root,'btn_a'))).toBe('a');expect(asset.pick!(part(asset.root,'logo_touch'))).toBe('logo');
  expect(asset.pick!(part(asset.root,'pcb'))).toBeUndefined();expect(asset.pick!(new THREE.Object3D())).toBeUndefined();
 });
 it('channels has 28 unique entries',()=>{
  const asset=createMicrobit(makeContractBoard());expect(asset.channels.length).toBe(28);expect(new Set(asset.channels).size).toBe(28);
  expect(asset.channels).toContain('led.4.4');expect(asset.channels).toContain('logo');
 });
 it('parts: one per contract part with a label, anchor on the top surface, and channel for pickables',()=>{
  const asset=createMicrobit(makeContractBoard()),parts=asset.parts!;expect(parts.length).toBe(contract.parts.length);
  const byId=new Map(parts.map(p=>[p.id,p]));
  for(const p of contract.parts){const info=byId.get(p.id)!;expect(info.label).toBe(p.label);expect(info.channel).toBe((contract.pickable as Record<string,string>)[p.id])}
  const cap=byId.get('btn_a_cap')!,box=new THREE.Box3().setFromObject(part(asset.root,'btn_a_cap'));
  expect(cap.anchor.y).toBeCloseTo(box.max.y,9);expect(cap.anchor.x).toBeCloseTo((box.min.x+box.max.x)/2,9);
  expect(asset.anchors.control).toBeInstanceOf(THREE.Vector3);
 });
 it('dispose() releases geometry/materials once and a second dispose is a no-op',()=>{
  const board=makeContractBoard(),geo=vi.spyOn(part(board,'pcb').geometry,'dispose'),mat=vi.spyOn(led(board,2,2),'dispose');
  const asset=createMicrobit(board);asset.dispose();expect(geo).toHaveBeenCalledTimes(1);expect(mat).toHaveBeenCalledTimes(1);
  asset.dispose();expect(geo).toHaveBeenCalledTimes(1);expect(mat).toHaveBeenCalledTimes(1);
 });
});
describe('logo feedback never mutates a shared material',()=>{
 const state=(m:THREE.MeshStandardMaterial)=>({e:m.emissive.getHex(),i:m.emissiveIntensity});
 for(const other of ['pcb','btn_a_cap','pin_1']){
  it(`logo sharing ${other}'s material lights only the logo and restores exactly`,()=>{
   const board=makeContractBoard(),shared=part(board,other).material as THREE.MeshStandardMaterial;part(board,'logo_touch').material=shared;
   const before=state(shared),asset=createMicrobit(board),logo=part(asset.root,'logo_touch'),logoMat=logo.material as THREE.MeshStandardMaterial,otherMat=part(asset.root,other).material as THREE.MeshStandardMaterial;
   expect(otherMat).toBe(shared);expect(logoMat).not.toBe(shared);const rest=state(logoMat);
   asset.set('logo',1);expect(state(logoMat)).not.toEqual(rest);expect(state(shared)).toEqual(before);
   asset.set('logo',0);expect(state(logoMat)).toEqual(rest);expect(state(shared)).toEqual(before);
  });
 }
 it('disposes the shared material and the logo clone exactly once each',()=>{
  const board=makeContractBoard(),shared=part(board,'pcb').material as THREE.MeshStandardMaterial;part(board,'logo_touch').material=shared;
  const asset=createMicrobit(board),clone=part(asset.root,'logo_touch').material as THREE.MeshStandardMaterial,a=vi.spyOn(shared,'dispose'),b=vi.spyOn(clone,'dispose');
  asset.dispose();asset.dispose();expect(a).toHaveBeenCalledTimes(1);expect(b).toHaveBeenCalledTimes(1);
 });
 it('rejects a logo whose material cannot take an emissive colour',()=>{
  const board=makeContractBoard();part(board,'logo_touch').material=new THREE.MeshBasicMaterial();
  expect(()=>createMicrobit(board)).toThrow(/logo_touch.*MeshStandardMaterial/);
 });
});
