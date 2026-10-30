import {describe,it,expect} from 'vitest';
import * as THREE from 'three';
import {Runtime,ResourceScope,validateScene,bindHold,projectAnchor} from '../src/runtime';
import {createBuiltin} from '../src/assets';
const scene = () => ({schemaVersion:1,kind:'scene',id:'test',title:'Test',duration:4,mode:'timeline',instances:[{id:'b',asset:'button',position:[2,0,0],rotation:[0,0,0],scale:[2,2,2]}],tracks:[{target:'b',channel:'pressed',keyframes:[{time:0,value:0},{time:2,value:1},{time:4,value:0}]}]});
describe('deterministic runtime',()=>{
 it('seeks independently of earlier frames and preserves instance transform',()=>{
  const r=new Runtime(validateScene(scene())); const a=createBuiltin('button');r.add('b',a);
  r.seek(3); expect(r.value('b','pressed')).toBe(.5); r.seek(1); expect(r.value('b','pressed')).toBe(.5);
  expect(a.root.position.x).toBe(2); expect(a.root.scale.x).toBe(2);
 });
 it('timeline owns tracked channels; interactive mode transfers ownership',()=>{
  const r=new Runtime(validateScene(scene()));r.add('b',createBuiltin('button'));
  r.input('b','pressed',1);r.seek(0);expect(r.value('b','pressed')).toBe(0);
  r.setMode('interactive');r.input('b','pressed',1);r.seek(0);expect(r.value('b','pressed')).toBe(1);
  r.release();expect(r.value('b','pressed')).toBe(0);
 });
 it('disables autonomous playback for reduced motion but allows explicit seek',()=>{
  const r=new Runtime(validateScene(scene()),true);r.play();r.advance(1);expect(r.time).toBe(0);
  r.seek(2);expect(r.value('b','pressed')).toBe(1);
 });
 it('rejects malformed transforms, unsafe assets and duplicate ids',()=>{
  for(const change of [(s:any)=>s.instances[0].scale=[1,0,1],(s:any)=>s.instances[0].asset='https://x/a.glb',(s:any)=>s.instances.push(s.instances[0]),(s:any)=>s.tracks[0].keyframes[1].time=-1]){
   const s=scene();change(s);expect(()=>validateScene(s)).toThrow();
  }
 });
 it('projects anchors through authored position, rotation and scale',()=>{
  const root=new THREE.Group();root.position.set(2,0,0);root.scale.setScalar(2);
  const camera=new THREE.PerspectiveCamera(60,1,.1,100);camera.position.set(0,0,10);camera.lookAt(0,0,0);camera.updateMatrixWorld();
  const p=projectAnchor(root,new THREE.Vector3(1,0,0),camera,100,100);expect(p.visible).toBe(true);expect(p.x).toBeCloseTo(84.641,2);
  root.rotation.z=Math.PI/2;const rotated=projectAnchor(root,new THREE.Vector3(1,0,0),camera,100,100);expect(rotated.x).toBeCloseTo(67.3205,2);expect(rotated.y).toBeCloseTo(32.6795,2);
 });
 it('releases shared resources once and immediately disposes late allocations',()=>{
  const a=new ResourceScope(),b=new ResourceScope();let count=0;const resource={dispose(){count++}};
  a.own(resource);b.own(resource);a.dispose();expect(count).toBe(0);b.dispose();expect(count).toBe(1);
  a.own({dispose(){count++}});expect(count).toBe(2);a.dispose();expect(count).toBe(2);
 });
 it('restores rig and clips from absolute time, including backwards seek',()=>{
  const character=createBuiltin('character');expect(character.clips.length).toBeGreaterThan(0);
  const bone=character.root.getObjectByName('LeftArm')!;
  character.seek(1);const first=bone.quaternion.clone();character.seek(2);character.seek(1);
  expect(bone.quaternion.angleTo(first)).toBeCloseTo(0);expect(first.angleTo(new THREE.Quaternion())).toBeGreaterThan(.1);
 });
 it('releases hold on pointer cancel, pointer up and window blur',()=>{
  const node=new EventTarget(),win=new EventTarget();let value=0;const unbind=bindHold(node,win,(v)=>value=v);
  for(const end of ['pointerup','pointercancel','blur']){
   node.dispatchEvent(new Event('pointerdown'));expect(value).toBe(1);
   (end==='blur'?win:node).dispatchEvent(new Event(end));expect(value).toBe(0);
  }unbind();node.dispatchEvent(new Event('pointerdown'));expect(value).toBe(0);
 });
});
it('does not advance while reduced motion preference is enabled after mount',()=>{
 const r=new Runtime(validateScene(scene()));r.play();r.advance(.1);expect(r.time).toBe(.1);
 r.reducedMotion=true;r.advance(.1);expect(r.time).toBe(.1);
});
it('applies playback speed and stops at the end when looping is disabled',()=>{
 const r=new Runtime(validateScene(scene()));r.speed=2;r.loop=false;r.seek(3.9);r.play();r.advance(.1);expect(r.time).toBe(4);expect(r.playing).toBe(false);
});
it('clip selection restores the rig before sampling the new clip',()=>{
 const character=createBuiltin('character');character.seek(1);const arm=character.root.getObjectByName('LeftArm')!;
 expect(Math.abs(arm.quaternion.z)).toBeGreaterThan(.1);character.setClip(1);character.seek(1);expect(arm.quaternion.z).toBeCloseTo(0);character.dispose();
});
it('matches analytic poses for equal elapsed time split across frames',()=>{
 const a=new Runtime(validateScene(scene())),b=new Runtime(validateScene(scene()));a.add('b',createBuiltin('button'));b.add('b',createBuiltin('button'));
 a.play();b.play();a.advance(1);for(let i=0;i<10;i++)b.advance(.1);
 expect(a.time).toBeCloseTo(1);expect(b.time).toBeCloseTo(1);expect(a.value('b','pressed')).toBeCloseTo(b.value('b','pressed'));
});
it('rejects duplicate runtime insertion without losing the original resource owner',()=>{
 const r=new Runtime(validateScene(scene())),a=createBuiltin('button');r.add('b',a);expect(()=>r.add('b',createBuiltin('button'))).toThrow();expect(r.assets.get('b')).toBe(a);r.dispose();
});
it('releases a held input when pointer capture is lost',()=>{
 const node=new EventTarget(),win=new EventTarget();let value=0;const stop=bindHold(node,win,v=>value=v);node.dispatchEvent(new Event('pointerdown'));node.dispatchEvent(new Event('lostpointercapture'));expect(value).toBe(0);stop();
});
it('enforces schema IDs, a nonempty title and one or more instances',()=>{
 for(const change of [(s:any)=>s.id='bad id',(s:any)=>s.instances[0].id='bad id',(s:any)=>s.title='',(s:any)=>s.instances=[]]){
  const s=scene();change(s);expect(()=>validateScene(s)).toThrow();
 }
});
