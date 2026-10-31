import {describe,it,expect,vi} from 'vitest';
import * as THREE from 'three';
import fixtureJson from '../../tests/fixtures/microbit-scene-cases.json';
import {Runtime,ResourceScope,validateScene,bindHold,projectAnchor,MOMENTARY,channelRange,type Asset,type Channel} from '../src/runtime';
import {createBuiltin,loadGLB} from '../src/assets';
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
it('reset clears every interactive channel, clip pose, time and playback while preserving scene transforms',()=>{
 const spec=validateScene({schemaVersion:1,kind:'scene',id:'reset',title:'Reset',duration:4,mode:'interactive',instances:[
 {id:'servo',asset:'servo',position:[2,0,0],rotation:[0,.5,0],scale:[2,2,2]},
 {id:'button',asset:'button',position:[0,0,0],rotation:[0,0,0],scale:[1,1,1]},
 {id:'rig',asset:'character',position:[-2,0,0],rotation:[0,0,0],scale:[1,1,1]}],tracks:[]});
 const r=new Runtime(spec);for(const i of spec.instances)r.add(i.id,createBuiltin(i.asset));
 r.input('servo','angle',90);r.input('button','pressed',1);r.assets.get('rig')!.setClip(1);r.seek(1);r.play();r.reset();
 expect(r.value('servo','angle')).toBe(0);expect(r.value('button','pressed')).toBe(0);expect(r.time).toBe(0);expect(r.playing).toBe(false);
 expect(r.assets.get('rig')!.clipIndex).toBe(0);expect(r.assets.get('rig')!.root.getObjectByName('LeftArm')!.quaternion.z).toBeCloseTo(0);
 expect(r.assets.get('servo')!.root.position.x).toBe(2);expect(r.assets.get('servo')!.root.rotation.y).toBe(.5);expect(r.assets.get('servo')!.root.scale.x).toBe(2);r.dispose();
});
it('timeline reset reapplies authored time-zero values after clearing prior input',()=>{
 const s=scene();s.tracks[0].keyframes[0].value=.25;const r=new Runtime(validateScene(s));r.add('b',createBuiltin('button'));r.seek(2);r.play();r.reset();
 expect(r.value('b','pressed')).toBe(.25);expect(r.time).toBe(0);expect(r.playing).toBe(false);r.dispose();
});

it('holds built-in clip endpoint beyond duration and restores backwards sampling',()=>{
 const a=createBuiltin('character'),arm=a.root.getObjectByName('LeftArm')!;
 a.seek(4);expect(arm.quaternion.z).toBeCloseTo(0);a.seek(5);expect(arm.quaternion.z).toBeCloseTo(0);
 a.seek(1);expect(Math.abs(arm.quaternion.z)).toBeGreaterThan(.1);a.seek(4);expect(arm.quaternion.z).toBeCloseTo(0);a.dispose();
});
const linked=()=>({schemaVersion:1,kind:'scene',id:'link',title:'Link',duration:4,mode:'interactive',instances:[
 {id:'b',asset:'button',position:[0,0,0],rotation:[0,0,0],scale:[1,1,1]},
 {id:'s',asset:'servo',position:[2,0,0],rotation:[0,0,0],scale:[1,1,1]}],
 bindings:[{source:'b',sourceChannel:'pressed',target:'s',targetChannel:'angle',released:0,pressed:90}],
 tracks:[{target:'b',channel:'pressed',keyframes:[{time:0,value:0},{time:2,value:1},{time:4,value:0}]}]});
it('button drives linked servo in both modes with deterministic ownership, release and reset',()=>{
 const r=new Runtime(validateScene(linked()));r.add('b',createBuiltin('button'));r.add('s',createBuiltin('servo'));
 r.input('b','pressed',1);expect(r.value('s','angle')).toBe(90);const horn=r.assets.get('s')!.root.children.find(c=>c.type==='Group')!;expect(horn.rotation.y).toBeCloseTo(Math.PI/2);r.input('s','angle',-45);expect(r.value('s','angle')).toBe(90);
 r.release();expect(r.value('s','angle')).toBe(0);expect(horn.rotation.y).toBe(0);r.input('b','pressed',1);r.reset();expect(r.value('s','angle')).toBe(0);expect(horn.rotation.y).toBe(0);
 r.setMode('timeline');r.seek(2);expect(r.value('s','angle')).toBe(90);r.seek(1);expect(r.value('s','angle')).toBe(45);
 r.input('s','angle',-90);expect(r.value('s','angle')).toBe(45);r.release();expect(r.value('s','angle')).toBe(45);
 r.setMode('interactive');expect(r.value('b','pressed')).toBe(0);expect(r.value('s','angle')).toBe(0);r.dispose();
});
it('timeline target track takes precedence over the binding only in timeline mode',()=>{
 const s=linked();s.tracks.push({target:'s',channel:'angle',keyframes:[{time:0,value:-30},{time:4,value:30}]});
 const r=new Runtime(validateScene(s));r.add('b',createBuiltin('button'));r.add('s',createBuiltin('servo'));
 r.input('b','pressed',1);expect(r.value('s','angle')).toBe(90);r.setMode('timeline');r.seek(2);expect(r.value('s','angle')).toBe(0);
 r.input('b','pressed',0);expect(r.value('s','angle')).toBe(0);r.setMode('interactive');r.input('b','pressed',1);expect(r.value('s','angle')).toBe(90);r.dispose();
});
it('rejects unsafe, unsupported and duplicate bindings',()=>{
 for(const change of [(s:any)=>s.bindings[0].target='missing',(s:any)=>s.bindings[0].source='s',(s:any)=>s.bindings[0].sourceChannel='angle',
 (s:any)=>s.bindings[0].targetChannel='pressed',(s:any)=>s.bindings[0].pressed=181,(s:any)=>s.bindings[0].released=true,
 (s:any)=>s.bindings[0].code='eval()',(s:any)=>s.bindings.push(s.bindings[0]),(s:any)=>s.bindings=null]){
 const s=linked();change(s);expect(()=>validateScene(s)).toThrow();
 }
});

it('loaded GLB holds a nonmatching endpoint and permits backwards seek',async()=>{
 const floats=new Float32Array([0,1,0,0,0,2,0,0]);
 const doc={asset:{version:'2.0'},scene:0,scenes:[{nodes:[0]}],nodes:[{name:'Moving'}],buffers:[{byteLength:floats.byteLength}],
 bufferViews:[{buffer:0,byteOffset:0,byteLength:8},{buffer:0,byteOffset:8,byteLength:24}],
 accessors:[{bufferView:0,componentType:5126,count:2,type:'SCALAR',min:[0],max:[1]},{bufferView:1,componentType:5126,count:2,type:'VEC3'}],
 animations:[{name:'Move',samplers:[{input:0,output:1}],channels:[{sampler:0,target:{node:0,path:'translation'}}]}]};
 const json=new TextEncoder().encode(JSON.stringify(doc));const padded=(json.length+3)&~3;const glb=new ArrayBuffer(28+padded+floats.byteLength),view=new DataView(glb);
 [0x46546c67,2,glb.byteLength,padded,0x4e4f534a].forEach((v,i)=>view.setUint32(i*4,v,true));new Uint8Array(glb,20,padded).fill(32);new Uint8Array(glb,20,json.length).set(json);
 view.setUint32(20+padded,floats.byteLength,true);view.setUint32(24+padded,0x004e4942,true);new Uint8Array(glb,28+padded).set(new Uint8Array(floats.buffer));
 vi.stubGlobal('fetch',async()=>new Response(glb));
 try{const a=await loadGLB('http://localhost/test.glb',new AbortController().signal),moving=a.root.getObjectByName('Moving')!;
 a.seek(1);expect(moving.position.x).toBe(2);a.seek(2);expect(moving.position.x).toBe(2);a.seek(.5);expect(moving.position.x).toBe(1);a.dispose();}finally{vi.unstubAllGlobals()}
});

it('treats a button named timeline as a binding source, without a reserved ID collision',()=>{
 const s=linked();s.instances[0].id='timeline';s.bindings[0].source='timeline';s.tracks[0].target='timeline';
 const r=new Runtime(validateScene(s));r.add('timeline',createBuiltin('button'));r.add('s',createBuiltin('servo'));
 r.input('timeline','pressed',1);expect(r.value('s','angle')).toBe(90);r.setMode('timeline');r.seek(1);expect(r.value('s','angle')).toBe(45);r.dispose();
});

const LEDS=Array.from({length:25},(_,i)=>`led.${i%5}.${Math.floor(i/5)}` as Channel);
const grid=(fill=0,cells:Record<string,number>={})=>Array.from({length:5},(_,y)=>Array.from({length:5},(_,x)=>cells[x+','+y]??fill));
const stubBoard=():Asset&{sets:[Channel,number][]}=>{const sets:[Channel,number][]=[];return {sets,root:new THREE.Group(),anchors:{},channels:['a','b','logo',...LEDS],clips:[],clipIndex:0,setClip(){},set(c,v){sets.push([c,v])},seek(){},dispose(){}}};
const boardScene=(extra:Record<string,unknown>={})=>({schemaVersion:1,kind:'scene',id:'mb',title:'MB',duration:4,mode:'interactive',
 instances:[{id:'mb',asset:'microbit/microbit.glb',behavior:'microbit',position:[0,0,0],rotation:[0,0,0],scale:[1,1,1]}],tracks:[],
 patternBindings:[{source:'a',target:'mb',released:grid(),pressed:grid(0,{'2,2':255})}],...extra});
const boardRuntime=(extra:Record<string,unknown>={})=>{const r=new Runtime(validateScene(boardScene(extra)));const a=stubBoard();r.add('mb',a);return {r,a}};
describe('micro:bit channels and pattern bindings',()=>{
 it('pattern binding lights LEDs only while source pressed',()=>{
  const {r}=boardRuntime();expect(r.value('mb','led.2.2')).toBe(0);
  r.input('mb','a',1);expect(r.value('mb','led.2.2')).toBe(255);
  r.input('mb','a',0);expect(r.value('mb','led.2.2')).toBe(0);
 });
 it('overlapping patterns combine by per-LED maximum',()=>{
  const {r}=boardRuntime({patternBindings:[{source:'a',target:'mb',released:grid(),pressed:grid(0,{'0,0':100})},{source:'b',target:'mb',released:grid(),pressed:grid(0,{'0,0':200})}]});
  r.input('mb','a',1);r.input('mb','b',1);expect(r.value('mb','led.0.0')).toBe(200);
  r.input('mb','b',0);expect(r.value('mb','led.0.0')).toBe(100);
  r.input('mb','a',0);expect(r.value('mb','led.0.0')).toBe(0);
 });
 it('interpolates between released and pressed grids by source value',()=>{
  const {r}=boardRuntime({patternBindings:[{source:'logo',target:'mb',released:grid(40),pressed:grid(200)}]});
  expect(r.value('mb','led.4.4')).toBe(40);r.input('mb','logo',.5);expect(r.value('mb','led.4.4')).toBe(120);
 });
 it('nonzero released grid is the authored rest pose and survives reset()',()=>{
  const {r,a}=boardRuntime({patternBindings:[{source:'a',target:'mb',released:grid(0,{'1,3':80}),pressed:grid(255)}]});
  expect(r.value('mb','led.1.3')).toBe(80);expect(a.sets.some(([c,v])=>c==='led.1.3'&&v===80)).toBe(true);
  r.input('mb','a',1);expect(r.value('mb','led.1.3')).toBe(255);r.reset();
  expect(r.value('mb','a')).toBe(0);expect(r.value('mb','led.1.3')).toBe(80);expect(r.value('mb','led.0.0')).toBe(0);
 });
 it('interactive input cannot write a pattern-owned LED',()=>{
  const {r}=boardRuntime();r.input('mb','led.0.0',50);expect(r.value('mb','led.0.0')).toBe(0);
  expect(r.owner('mb','led.0.0')).toEqual({kind:'pattern',source:'a'});expect(r.owner('mb','a')).toBeUndefined();
  const free=boardRuntime({patternBindings:[]});free.r.input('mb','led.0.0',999);expect(free.r.value('mb','led.0.0')).toBe(255);
  free.r.input('mb','a',7);expect(free.r.value('mb','a')).toBe(1);free.r.input('mb','a',-3);expect(free.r.value('mb','a')).toBe(0);
 });
 it('timeline track on an LED takes precedence in timeline mode; pattern resumes in interactive mode',()=>{
  const {r}=boardRuntime({mode:'timeline',tracks:[{target:'mb',channel:'led.2.2',keyframes:[{time:0,value:0},{time:4,value:200}]}]});
  r.seek(2);expect(r.owner('mb','led.2.2')).toEqual({kind:'timeline'});expect(r.value('mb','led.2.2')).toBe(100);
  r.input('mb','a',1);expect(r.value('mb','led.2.2')).toBe(100);
  r.setMode('interactive');expect(r.owner('mb','led.2.2')).toEqual({kind:'pattern',source:'a'});expect(r.value('mb','led.2.2')).toBe(0);
  r.input('mb','a',1);expect(r.value('mb','led.2.2')).toBe(255);
 });
 it('release() frees pressed, a, b and logo',()=>{
  expect([...MOMENTARY]).toEqual(['pressed','a','b','logo']);
  const {r}=boardRuntime({patternBindings:[]});for(const c of ['a','b','logo'] as const)r.input('mb',c,1);
  r.release();for(const c of ['a','b','logo'] as const)expect(r.value('mb',c)).toBe(0);
  const btn=new Runtime(validateScene(scene()));btn.setMode('interactive');btn.add('b',createBuiltin('button'));btn.input('b','pressed',1);btn.release();expect(btn.value('b','pressed')).toBe(0);
 });
 it('A held with B then B released leaves A pattern, never a blank board',()=>{
  const {r}=boardRuntime({patternBindings:[{source:'a',target:'mb',released:grid(),pressed:grid(0,{'0,0':255})},{source:'b',target:'mb',released:grid(),pressed:grid(0,{'4,4':255})}]});
  r.input('mb','a',1);r.input('mb','b',1);r.input('mb','b',0);expect(r.value('mb','led.0.0')).toBe(255);expect(r.value('mb','led.4.4')).toBe(0);
 });
 it('channel ranges',()=>{
  expect(channelRange('pressed')).toEqual([0,1]);expect(channelRange('a')).toEqual([0,1]);expect(channelRange('b')).toEqual([0,1]);expect(channelRange('logo')).toEqual([0,1]);
  expect(channelRange('angle')).toEqual([-180,180]);expect(channelRange('led.3.1')).toEqual([0,255]);
 });
});
describe('shared scene validation fixture',()=>{
 const fixture=fixtureJson as unknown as {valid:{name:string;scene:unknown}[];invalid:{name:string;scene:unknown}[]};
 it('every case in both groups has a unique name and a scene object',()=>{
  expect(fixture.valid.length).toBe(9);expect(fixture.invalid.length).toBe(44);
  for(const group of [fixture.valid,fixture.invalid])for(const c of group){expect(typeof c.name).toBe('string');expect(c.name.length).toBeGreaterThan(0);expect(typeof c.scene).toBe('object');expect(c.scene).not.toBeNull()}
  const names=[...fixture.valid,...fixture.invalid].map(c=>c.name);expect(new Set(names).size).toBe(names.length);
 });
 for(const c of fixture.valid)it('accepts valid: '+c.name,()=>{expect(()=>validateScene(structuredClone(c.scene))).not.toThrow()});
 for(const c of fixture.invalid)it('rejects invalid: '+c.name,()=>{expect(()=>validateScene(structuredClone(c.scene))).toThrow()});
});
describe('scene camera (authored view)',()=>{
 const scene=(camera:unknown)=>({schemaVersion:1,kind:'scene',id:'cam',title:'Cam',duration:4,mode:'interactive',instances:[{id:'Board',asset:'microbit.glb',behavior:'microbit',position:[0,0,0],rotation:[0,0,0],scale:[1,1,1]}],tracks:[],camera});
 it('keeps a valid camera and treats an absent one as the default view',()=>{
  expect(validateScene(scene({elevation:62,azimuth:0})).camera).toEqual({elevation:62,azimuth:0});
  const plain=scene(undefined);delete (plain as {camera?:unknown}).camera;expect(validateScene(plain).camera).toBeUndefined();
 });
 for(const bad of [{elevation:Number.NaN,azimuth:0},{elevation:Number.POSITIVE_INFINITY,azimuth:0},{elevation:60,azimuth:Number.NEGATIVE_INFINITY},{elevation:60,azimuth:Number.NaN}])
  it('rejects a non-finite camera value '+JSON.stringify(bad),()=>{expect(()=>validateScene(scene(bad))).toThrow()});
});
