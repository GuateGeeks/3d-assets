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
 it('ledGrid.columns and rows are 5 and match the led_x_y parts (the 5x5 size is hard-coded elsewhere, so the contract must not drift)',()=>{
  expect(contract.ledGrid.columns).toBe(5);expect(contract.ledGrid.rows).toBe(5);
  expect(contract.parts.filter(p=>/^led_\d+_\d+$/.test(p.id)).length).toBe(contract.ledGrid.columns*contract.ledGrid.rows);
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
 it('rest look: all 25 LEDs get the contract base colour and roughness at load, whatever the GLB carried',()=>{
  const board=makeContractBoard();led(board,3,3).color.set(0xffffff);led(board,3,3).roughness=.1;
  const asset=createMicrobit(board),rest=new THREE.Color(contract.ledRest.color);
  for(let y=0;y<5;y++)for(let x=0;x<5;x++){const m=led(asset.root,x,y);expect(m.color.getHex()).toBe(rest.getHex());expect(m.roughness).toBe(contract.ledRest.roughness)}
  expect(rest.r+rest.g+rest.b).toBeLessThan(.1);// a dark body, so the red emission is not washed out
 });
 it('lit intensity is monotonic in the channel value and 80 reads clearly dimmer than 255',()=>{
  const asset=createMicrobit(makeContractBoard()),at=(v:number)=>{asset.set('led.2.2',v);return led(asset.root,2,2).emissiveIntensity};
  const levels=[0,1,40,80,128,200,255].map(at);for(let i=1;i<levels.length;i++)expect(levels[i]).toBeGreaterThan(levels[i-1]);
  expect(at(80)/at(255)).toBeLessThanOrEqual(.4);expect(at(255)).toBe(contract.ledEmissive.maxIntensity);expect(at(300)).toBe(contract.ledEmissive.maxIntensity);expect(at(-5)).toBe(0);
  // Lighting an LED never changes its body colour.
  asset.set('led.2.2',255);expect(led(asset.root,2,2).color.getHex()).toBe(new THREE.Color(contract.ledRest.color).getHex());
 });
 it("set('led.1.2',255) lights only that LED to maxIntensity; set(...,0) restores 0",()=>{
  const asset=createMicrobit(makeContractBoard());asset.set('led.1.2',255);
  for(let y=0;y<5;y++)for(let x=0;x<5;x++)expect(led(asset.root,x,y).emissiveIntensity).toBe(x===1&&y===2?contract.ledEmissive.maxIntensity:0);
  asset.set('led.1.2',0);expect(led(asset.root,1,2).emissiveIntensity).toBe(0);
 });
 it("set('led.1.2',128) follows the contract's brightness curve",()=>{
  const asset=createMicrobit(makeContractBoard());asset.set('led.1.2',128);
  expect(led(asset.root,1,2).emissiveIntensity).toBeCloseTo((128/255)**contract.ledEmissive.brightnessGamma*contract.ledEmissive.maxIntensity,6);
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
describe('touch logo hit area',()=>{
 // A ring: the natural place to press is an open hole, so the factory must add an invisible hit area over the footprint.
 const ringBoard=()=>{
  const board=makeContractBoard(),logo=part(board,'logo_touch'),shape=new THREE.Shape().absarc(0,0,.003,0,Math.PI*2,false);
  shape.holes.push(new THREE.Path().absarc(0,0,.0018,0,Math.PI*2,true));
  const geometry=new THREE.ExtrudeGeometry(shape,{depth:.0003,bevelEnabled:false});geometry.rotateX(-Math.PI/2);geometry.translate(logo.position.x,.0008,logo.position.z);
  logo.geometry.dispose();logo.geometry=geometry;logo.position.set(0,0,0);return board;
 };
 const down=(root:THREE.Object3D,x:number,z:number)=>{const r=new THREE.Raycaster(new THREE.Vector3(x,.1,z),new THREE.Vector3(0,-1,0));return r.intersectObject(root,true)[0]};
 it('the ring fixture is open at its centre: a ray straight down reaches the board',()=>{
  const board=ringBoard();board.updateMatrixWorld(true);expect(down(board,0,-.016).object.userData.part_id).toBe('pcb');
 });
 it('a ray through the hole of the logo ring picks the logo; rays well outside it still pick nothing',()=>{
  const asset=createMicrobit(ringBoard());asset.root.updateMatrixWorld(true);
  const hit=down(asset.root,0,-.016);expect(asset.pick!(hit.object)).toBe('logo');
  expect(asset.pick!(down(asset.root,0,-.0075).object)).toBeUndefined();expect(asset.pick!(down(asset.root,.0105,-.016).object)).toBeUndefined();
 });
 it('the hit area is invisible, does not change the bounds, follows the press, and is disposed once with the asset',()=>{
  const board=ringBoard(),before=new THREE.Box3().setFromObject(board),asset=createMicrobit(board),logo=part(asset.root,'logo_touch');
  const proxies=logo.children.filter(o=>o instanceof THREE.Mesh) as THREE.Mesh[];expect(proxies.length).toBe(1);
  const proxy=proxies[0],material=proxy.material as THREE.Material;expect(material.visible).toBe(false);
  const after=new THREE.Box3().setFromObject(asset.root);expect(after.min.distanceTo(before.min)).toBeLessThan(1e-9);expect(after.max.distanceTo(before.max)).toBeLessThan(1e-9);
  const low=()=>{asset.root.updateMatrixWorld(true);return new THREE.Box3().setFromObject(proxy).min.y},rest=low();asset.set('logo',1);expect(low()).toBeLessThan(rest);asset.set('logo',0);expect(low()).toBe(rest);
  const g=vi.spyOn(proxy.geometry,'dispose'),m=vi.spyOn(material,'dispose');asset.dispose();asset.dispose();expect(g).toHaveBeenCalledTimes(1);expect(m).toHaveBeenCalledTimes(1);
 });
 it('adds nothing to the node contract: no part_id on the hit area and still one logo_touch',()=>{
  const asset=createMicrobit(ringBoard());let logos=0;asset.root.traverse(o=>{if(o.userData.part_id==='logo_touch')logos++});expect(logos).toBe(1);
  expect(asset.parts!.length).toBe(46);
 });
});
