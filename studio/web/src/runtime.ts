import * as THREE from 'three';
export type Channel='pressed'|'angle';
export type Mode='interactive'|'timeline';
export interface Instance {id:string;asset:string;position:[number,number,number];rotation:[number,number,number];scale:[number,number,number]}
export interface Track {target:string;channel:Channel;keyframes:{time:number;value:number}[]}
export interface SceneSpec {schemaVersion:1;kind:'scene';id:string;title:string;duration:number;mode:Mode;instances:Instance[];tracks:Track[]}
export interface Asset {root:THREE.Group;anchors:Record<string,THREE.Vector3>;channels:Channel[];clips:THREE.AnimationClip[];clipIndex:number;setClip(index:number):void;set(channel:Channel,value:number):void;seek(time:number):void;dispose():void}
export function validateScene(raw:unknown):SceneSpec {
 const s=raw as SceneSpec; const fail=()=>{throw new Error('Invalid scene: check version, instances, transforms and tracks.')};
 if(!s||s.schemaVersion!==1||s.kind!=='scene'||typeof s.id!=='string'||!/^([a-zA-Z0-9][a-zA-Z0-9_.-]{0,95})$/.test(s.id)||typeof s.title!=='string'||!s.title.trim()||!Number.isFinite(s.duration)||s.duration<=0||s.duration>300||!['interactive','timeline'].includes(s.mode)||!Array.isArray(s.instances)||s.instances.length<1||s.instances.length>100)fail();
 const ids=new Set<string>();for(const a of s.instances){
  if(!a||typeof a.id!=='string'||!/^([a-zA-Z0-9][a-zA-Z0-9_.-]{0,95})$/.test(a.id)||ids.has(a.id)||typeof a.asset!=='string')fail();ids.add(a.id);
  if(!['button','servo','character'].includes(a.asset)&&!(/^(?:[a-zA-Z0-9_-]+\/)*[a-zA-Z0-9_.-]+\.glb$/.test(a.asset)&&!a.asset.split('/').includes('..')))fail();
  for(const k of ['position','rotation','scale'] as const)if(!Array.isArray(a[k])||a[k].length!==3||!a[k].every(Number.isFinite)||(k==='scale'&&a[k].some(v=>v<=0)))fail();
 }
 if(s.tracks===undefined)s.tracks=[];if(!Array.isArray(s.tracks))fail();
 const owned=new Set<string>();for(const t of s.tracks){
  const key=t.target+':'+t.channel;if(!ids.has(t.target)||!['pressed','angle'].includes(t.channel)||owned.has(key)||!Array.isArray(t.keyframes)||!t.keyframes.length)fail();owned.add(key);
  let last=-1;for(const k of t.keyframes){if(!Number.isFinite(k.time)||k.time<0||k.time>s.duration||k.time<=last||!Number.isFinite(k.value)||(t.channel==='pressed'&&(k.value<0||k.value>1))||(t.channel==='angle'&&(k.value< -180||k.value>180)))fail();last=k.time}
  const asset=s.instances.find(a=>a.id===t.target)!.asset;if((t.channel==='pressed'&&asset!=='button')||(t.channel==='angle'&&asset!=='servo'))fail();
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
 input(id:string,c:Channel,v:number){if(!Number.isFinite(v)||!this.assets.get(id)?.channels.includes(c))return;
  if(this.mode==='timeline'&&this.spec.tracks.some(t=>t.target===id&&t.channel===c))return;this.apply(id,c,THREE.MathUtils.clamp(v,c==='pressed'?0:-180,c==='pressed'?1:180))}
 release(){for(const [id,a]of this.assets)if(a.channels.includes('pressed'))this.input(id,'pressed',0)}
 reset(){this.playing=false;this.values.clear();for(const [id,asset]of this.assets){for(const channel of asset.channels)this.apply(id,channel,0);asset.setClip(0)}this.seek(0)}
 setMode(mode:Mode){this.release();this.mode=mode;this.seek(this.time)}
 seek(time:number){this.time=THREE.MathUtils.clamp(time,0,this.spec.duration);for(const a of this.assets.values())a.seek(this.time);
  if(this.mode==='timeline')for(const t of this.spec.tracks)this.apply(t.target,t.channel,sample(t,this.time))}
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
