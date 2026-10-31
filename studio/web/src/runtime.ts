import * as THREE from 'three';
export type Led=`led.${0|1|2|3|4}.${0|1|2|3|4}`;
export type Channel='pressed'|'angle'|'a'|'b'|'logo'|Led;
export const MOMENTARY:readonly Channel[]=['pressed','a','b','logo'];
const LED=/^led\.[0-4]\.[0-4]$/;
const isChannel=(c:unknown):c is Channel=>typeof c==='string'&&(['pressed','angle','a','b','logo'].includes(c)||LED.test(c));
export function channelRange(c:Channel):[number,number]{return c==='angle'?[-180,180]:c==='pressed'||c==='a'||c==='b'||c==='logo'?[0,1]:[0,255]}
export type Grid=number[][];
export interface PatternBinding {source:'a'|'b'|'logo';target:string;released:Grid;pressed:Grid}
export type Mode='interactive'|'timeline';
export interface Instance {id:string;asset:string;position:[number,number,number];rotation:[number,number,number];scale:[number,number,number];behavior?:'microbit'}
export interface Track {target:string;channel:Channel;keyframes:{time:number;value:number}[]}
export interface ControlBinding {source:string;sourceChannel:'pressed';target:string;targetChannel:'angle';released:number;pressed:number}
export interface SceneSpec {schemaVersion:1;kind:'scene';id:string;title:string;duration:number;mode:Mode;instances:Instance[];tracks:Track[];bindings?:ControlBinding[];patternBindings?:PatternBinding[]}
export interface PartInfo {id:string;label:string;anchor:THREE.Vector3;channel?:Channel}
export interface Asset {parts?:PartInfo[];pick?(object:THREE.Object3D):Channel|undefined;root:THREE.Group;anchors:Record<string,THREE.Vector3>;channels:Channel[];clips:THREE.AnimationClip[];clipIndex:number;setClip(index:number):void;set(channel:Channel,value:number):void;seek(time:number):void;dispose():void}
export function validateScene(raw:unknown):SceneSpec {
 const s=raw as SceneSpec; const fail=()=>{throw new Error('Invalid scene: check version, instances, transforms and tracks.')};
 if(!s||s.schemaVersion!==1||s.kind!=='scene'||typeof s.id!=='string'||!/^([a-zA-Z0-9][a-zA-Z0-9_.-]{0,95})$/.test(s.id)||typeof s.title!=='string'||!s.title.trim()||!Number.isFinite(s.duration)||s.duration<=0||s.duration>300||!['interactive','timeline'].includes(s.mode)||!Array.isArray(s.instances)||s.instances.length<1||s.instances.length>100)fail();
 const ids=new Set<string>();for(const a of s.instances){
  if(!a||typeof a.id!=='string'||!/^([a-zA-Z0-9][a-zA-Z0-9_.-]{0,95})$/.test(a.id)||ids.has(a.id)||typeof a.asset!=='string')fail();ids.add(a.id);
  if(!['button','servo','character'].includes(a.asset)&&!(/^(?:[a-zA-Z0-9_-]+\/)*[a-zA-Z0-9_.-]+\.glb$/.test(a.asset)&&!a.asset.split('/').includes('..')))fail();
  if(a.behavior!==undefined&&(a.behavior!=='microbit'||['button','servo','character'].includes(a.asset)))fail();
  for(const k of ['position','rotation','scale'] as const)if(!Array.isArray(a[k])||a[k].length!==3||!a[k].every(Number.isFinite)||(k==='scale'&&a[k].some(v=>v<=0)))fail();
 }
 if(s.tracks===undefined)s.tracks=[];if(!Array.isArray(s.tracks))fail();
 const owned=new Set<string>();for(const t of s.tracks){
  const key=t.target+':'+t.channel;if(!ids.has(t.target)||!isChannel(t.channel)||owned.has(key)||!Array.isArray(t.keyframes)||!t.keyframes.length)fail();owned.add(key);
  let last=-1;for(const k of t.keyframes){if(!Number.isFinite(k.time)||k.time<0||k.time>s.duration||k.time<=last||!Number.isFinite(k.value)||k.value<channelRange(t.channel)[0]||k.value>channelRange(t.channel)[1])fail();last=k.time}
  const inst=s.instances.find(a=>a.id===t.target)!;if(t.channel==='pressed'?inst.asset!=='button':t.channel==='angle'?inst.asset!=='servo':inst.behavior!=='microbit')fail();
 }
 const bindings=s.bindings??[];if(s.bindings!==undefined&&(!Array.isArray(s.bindings)||s.bindings.length>100))fail();
 const targets=new Set<string>();for(const b of bindings){
  if(!b||typeof b!=='object'||Object.keys(b).sort().join(',')!=='pressed,released,source,sourceChannel,target,targetChannel'
   ||s.instances.find(i=>i.id===b.source)?.asset!=='button'||s.instances.find(i=>i.id===b.target)?.asset!=='servo'
   ||b.sourceChannel!=='pressed'||b.targetChannel!=='angle'||targets.has(b.target)
   ||![b.released,b.pressed].every(v=>Number.isFinite(v)&&typeof v==='number'&&v>=-180&&v<=180))fail();
  targets.add(b.target);
 }
 if(s.patternBindings!==undefined&&(!Array.isArray(s.patternBindings)||s.patternBindings.length>100))fail();
 const grid=(g:unknown)=>Array.isArray(g)&&g.length===5&&g.every(r=>Array.isArray(r)&&r.length===5&&r.every(v=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=255));
 const pairs=new Set<string>();for(const p of s.patternBindings??[]){
  if(!p||typeof p!=='object'||Object.keys(p).sort().join(',')!=='pressed,released,source,target'||!['a','b','logo'].includes(p.source)||typeof p.target!=='string'
   ||s.instances.find(i=>i.id===p.target)?.behavior!=='microbit'||pairs.has(p.source+':'+p.target)||!grid(p.released)||!grid(p.pressed))fail();
  pairs.add(p.source+':'+p.target);
 }
 return s;
}
function sample(track:Track,time:number):number{
 const ks=track.keyframes;if(time<=ks[0].time)return ks[0].value;
 for(let i=1;i<ks.length;i++)if(time<=ks[i].time){const a=ks[i-1],b=ks[i];return a.value+(b.value-a.value)*(time-a.time)/(b.time-a.time)}
 return ks[ks.length-1].value;
}
export class Runtime{
 readonly assets=new Map<string,Asset>();time=0;playing=false;speed=1;loop=true;mode:Mode;
 private values=new Map<string,number>();
 constructor(readonly spec:SceneSpec,public reducedMotion=false){this.mode=spec.mode}
 add(id:string,asset:Asset){if(this.assets.has(id))throw new Error('Duplicate instance: '+id);const i=this.spec.instances.find(i=>i.id===id);if(!i)throw new Error('Unknown instance');
  asset.root.position.fromArray(i.position);asset.root.rotation.fromArray([...i.rotation,'XYZ']);asset.root.scale.fromArray(i.scale);asset.root.userData.instanceId=id;this.assets.set(id,asset);this.seek(this.time)}
 value(id:string,c:Channel){return this.values.get(id+':'+c)??0}
 private apply(id:string,c:Channel,v:number){this.values.set(id+':'+c,v);this.assets.get(id)?.set(c,v)}
 owner(id:string,c:Channel):{kind:'timeline'}|{kind:'binding';source:string}|{kind:'pattern';source:string}|undefined {
  if(this.mode==='timeline'&&this.spec.tracks.some(t=>t.target===id&&t.channel===c))return {kind:'timeline'};
  if(LED.test(c)){const pattern=this.spec.patternBindings?.find(p=>p.target===id);if(pattern)return {kind:'pattern',source:pattern.source}}
  const binding=this.spec.bindings?.find(b=>b.target===id&&b.targetChannel===c);
  return binding?{kind:'binding',source:binding.source}:undefined;
 }
 private applyBindings(){for(const b of this.spec.bindings??[]){
  if(this.owner(b.target,b.targetChannel)?.kind==='timeline')continue;
  this.apply(b.target,b.targetChannel,THREE.MathUtils.lerp(b.released,b.pressed,this.value(b.source,b.sourceChannel)));
 }
  const targets=new Set((this.spec.patternBindings??[]).map(p=>p.target));
  for(const id of targets){const mine=this.spec.patternBindings!.filter(p=>p.target===id);
   for(let y=0;y<5;y++)for(let x=0;x<5;x++){const led=`led.${x}.${y}` as Led;
    if(this.owner(id,led)?.kind==='timeline')continue;
    this.apply(id,led,Math.max(...mine.map(p=>THREE.MathUtils.lerp(p.released[y][x],p.pressed[y][x],this.value(id,p.source)))));
   }}
 }
 input(id:string,c:Channel,v:number){if(!Number.isFinite(v)||!this.assets.get(id)?.channels.includes(c))return;
  if(this.owner(id,c))return;this.apply(id,c,THREE.MathUtils.clamp(v,...channelRange(c)));this.applyBindings()}
 release(){for(const [id,a]of this.assets)for(const c of MOMENTARY)if(a.channels.includes(c))this.input(id,c,0)}
 reset(){this.playing=false;this.values.clear();for(const [id,asset]of this.assets){for(const channel of asset.channels)this.apply(id,channel,0);asset.setClip(0)}this.seek(0)}
 setMode(mode:Mode){this.mode=mode;this.release();this.seek(this.time)}
 seek(time:number){this.time=THREE.MathUtils.clamp(time,0,this.spec.duration);for(const a of this.assets.values())a.seek(this.time);
  if(this.mode==='timeline')for(const t of this.spec.tracks)this.apply(t.target,t.channel,sample(t,this.time));this.applyBindings()}
 play(){if(!this.reducedMotion)this.playing=true}
 advance(dt:number){if(this.playing&&!this.reducedMotion){const next=this.time+(Number.isFinite(dt)?Math.max(0,dt):0)*this.speed;if(next>=this.spec.duration&&!this.loop){this.seek(this.spec.duration);this.playing=false}else this.seek(next%this.spec.duration)}}
 dispose(){this.playing=false;for(const a of this.assets.values())a.dispose();this.assets.clear();this.values.clear()}
}
type Resource={dispose():void};
const refs=new WeakMap<Resource,number>();
export class ResourceScope{
 private resources=new Set<Resource>();private closed=false;
 own<T extends Resource>(r:T):T{if(this.closed){if(!refs.has(r))r.dispose();return r}if(!this.resources.has(r)){this.resources.add(r);refs.set(r,(refs.get(r)??0)+1)}return r}
 track(root:THREE.Object3D){root.traverse(o=>{if(o instanceof THREE.Mesh){this.own(o.geometry);for(const m of Array.isArray(o.material)?o.material:[o.material]){this.own(m);for(const value of Object.values(m))if(value instanceof THREE.Texture)this.own(value)}}if(o instanceof THREE.SkinnedMesh)this.own(o.skeleton)})}
 dispose(){if(this.closed)return;this.closed=true;for(const r of this.resources){const n=(refs.get(r)??1)-1;if(n===0){refs.delete(r);r.dispose()}else refs.set(r,n)}this.resources.clear()}
}
export function projectAnchor(root:THREE.Object3D,local:THREE.Vector3,camera:THREE.Camera,width:number,height:number){
 root.updateWorldMatrix(true,false);const p=root.localToWorld(local.clone()).project(camera);
 return {x:(p.x+1)*width/2,y:(1-p.y)*height/2,visible:p.z>=-1&&p.z<=1&&Math.abs(p.x)<=1&&Math.abs(p.y)<=1};
}
export function bindHold(node:EventTarget,win:EventTarget,change:(value:number)=>void){
 const down=()=>change(1),up=()=>change(0);
 const keydown=(event:Event)=>{const e=event as KeyboardEvent;if([' ','Enter'].includes(e.key)&&!e.repeat){e.preventDefault();down()}};
 const keyup=(event:Event)=>{if([' ','Enter'].includes((event as KeyboardEvent).key)){event.preventDefault();up()}};
 const bindings:[EventTarget,string,EventListener][]=[[node,'pointerdown',down],[node,'pointerup',up],[win,'pointerup',up],[node,'pointercancel',up],[node,'lostpointercapture',up],[win,'blur',up],[node,'keydown',keydown],[node,'keyup',keyup],[node,'blur',up]];
 for(const [target,type,fn]of bindings)target.addEventListener(type,fn);
 return()=>{up();for(const [target,type,fn]of bindings)target.removeEventListener(type,fn)};
}
