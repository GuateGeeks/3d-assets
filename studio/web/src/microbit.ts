import * as THREE from 'three';
import contractJson from '../../examples/microbit/node-contract.json';
import {ResourceScope,type Asset,type Channel,type PartInfo} from './runtime';
import {base,parseGLB} from './assets';
interface Contract {schemaVersion:1;units:'m';parts:{id:string;label:string}[];pickable:Record<string,string>;caps:Record<string,string>;pressTravelMeters:number;ledEmissive:{color:string;maxIntensity:number};ledGrid:{columns:number;rows:number;maxBrightness:number}}
const contract=contractJson as Contract;
const LED_PART=/^led_([0-4])_([0-4])$/;
// Logo touch feedback: a fraction of the button travel plus a warm emissive tint when its material is private.
const LOGO_TRAVEL=.4,LOGO_TINT=0xffb000,LOGO_TINT_INTENSITY=.6;
type Std=THREE.Material&{emissive:THREE.Color;emissiveIntensity:number};
const hasEmissive=(m:unknown):m is Std=>m instanceof THREE.Material&&(m as Partial<Std>).emissive instanceof THREE.Color&&typeof (m as Partial<Std>).emissiveIntensity==='number';
// Depress along the node's local Y (expressed in its parent's space) from a stored rest position; never accumulates.
class Plunger{
 private rest:THREE.Vector3;private axis:THREE.Vector3;
 constructor(private node:THREE.Object3D,private travel:number){this.rest=node.position.clone();this.axis=new THREE.Vector3(0,1,0).applyQuaternion(node.quaternion)}
 set(v:number){if(v<=0)this.node.position.copy(this.rest);else this.node.position.copy(this.rest).addScaledVector(this.axis,-this.travel*Math.min(v,1))}
}
export function createMicrobit(source:THREE.Object3D):Asset{
 const nodes=new Map<string,THREE.Object3D>(),known=new Set(contract.parts.map(p=>p.id));
 source.traverse(o=>{
  const id=o.userData.part_id;if(typeof id!=='string'||!known.has(id))return;
  if(nodes.has(id))throw new Error('Invalid micro:bit model: duplicate part_id '+id);nodes.set(id,o);
 });
 for(const p of contract.parts)if(!nodes.has(p.id))throw new Error('Invalid micro:bit model: missing part_id '+p.id);
 // Every LED needs its own material, otherwise lighting one LED would light the others (or other parts).
 const owners=new Map<THREE.Material,string>(),ledMaterials=new Map<string,Std>();
 for(const p of contract.parts){
  const node=nodes.get(p.id)!,isLed=LED_PART.test(p.id);
  if(isLed&&!(node instanceof THREE.Mesh&&!Array.isArray(node.material)&&hasEmissive(node.material)))throw new Error('Invalid micro:bit model: '+p.id+' must be a mesh with a single emissive material');
  if(node instanceof THREE.Mesh&&!Array.isArray(node.material)){
   const prior=owners.get(node.material);
   if(prior!==undefined&&(isLed||LED_PART.test(prior)))throw new Error('Invalid micro:bit model: '+p.id+' and '+prior+' must use a distinct material each');
   owners.set(node.material,p.id);if(isLed)ledMaterials.set(p.id,node.material as Std);
  }
 }
 const ledColor=new THREE.Color(contract.ledEmissive.color),maxIntensity=contract.ledEmissive.maxIntensity,maxBrightness=contract.ledGrid.maxBrightness;
 for(const m of ledMaterials.values()){m.emissive.copy(ledColor);m.emissiveIntensity=0}
 const root=new THREE.Group();root.add(source);root.updateMatrixWorld(true);
 const scope=new ResourceScope();
 // Drive tables are built before the anchors are measured so the rest pose is what gets measured.
 const plungers=new Map<Channel,Plunger[]>(),press=(channel:Channel,plunger:Plunger)=>plungers.set(channel,[...(plungers.get(channel)??[]),plunger]);
 for(const [id,channel] of Object.entries(contract.caps))press(channel as Channel,new Plunger(nodes.get(id)!,contract.pressTravelMeters));
 const logoNode=nodes.get('logo_touch')!,logoPlunger=new Plunger(logoNode,contract.pressTravelMeters*LOGO_TRAVEL);
 const logoMaterial=logoNode instanceof THREE.Mesh&&!Array.isArray(logoNode.material)&&hasEmissive(logoNode.material)&&owners.get(logoNode.material)==='logo_touch'?logoNode.material:undefined;
 const logoRest=logoMaterial&&{color:logoMaterial.emissive.clone(),intensity:logoMaterial.emissiveIntensity};
 const channels:Channel[]=['a','b','logo'];
 for(let y=0;y<5;y++)for(let x=0;x<5;x++)channels.push(`led.${x}.${y}` as Channel);
 const topAnchor=(object:THREE.Object3D)=>{
  const box=new THREE.Box3().setFromObject(object),top=new THREE.Vector3((box.min.x+box.max.x)/2,box.max.y,(box.min.z+box.max.z)/2);
  return root.worldToLocal(top);
 };
 const parts:PartInfo[]=contract.parts.map(p=>{
  const info:PartInfo={id:p.id,label:p.label,anchor:topAnchor(nodes.get(p.id)!)},channel=contract.pickable[p.id];
  if(channel)info.channel=channel as Channel;return info;
 });
 const pickable=contract.pickable as Record<string,Channel>;
 const set=(channel:Channel,value:number)=>{
  const v=Number.isFinite(value)?value:0,led=/^led\.([0-4])\.([0-4])$/.exec(channel);
  if(led){ledMaterials.get(`led_${led[1]}_${led[2]}`)!.emissiveIntensity=THREE.MathUtils.clamp(v,0,maxBrightness)/maxBrightness*maxIntensity;return}
  const level=THREE.MathUtils.clamp(v,0,1);
  if(channel==='a'||channel==='b')for(const p of plungers.get(channel)??[])p.set(level);
  else if(channel==='logo'){
   logoPlunger.set(level);
   if(logoMaterial&&logoRest){if(level>0){logoMaterial.emissive.set(LOGO_TINT);logoMaterial.emissiveIntensity=LOGO_TINT_INTENSITY*level}else{logoMaterial.emissive.copy(logoRest.color);logoMaterial.emissiveIntensity=logoRest.intensity}}
  }
 };
 const asset=base(root,scope,channels,{control:topAnchor(root)},set);
 asset.parts=parts;
 asset.pick=object=>{for(let o:THREE.Object3D|null=object;o;o=o.parent){const id=o.userData.part_id;if(typeof id==='string'&&Object.prototype.hasOwnProperty.call(pickable,id))return pickable[id]}return undefined};
 return asset;
}
export async function loadMicrobit(url:string,signal:AbortSignal):Promise<Asset>{
 const gltf=await parseGLB(url,signal);let asset:Asset;
 try{asset=createMicrobit(gltf.scene)}
 catch(error){const scope=new ResourceScope();scope.track(gltf.scene);scope.dispose();throw error}
 if(signal.aborted){asset.dispose();throw new DOMException('Scene replaced','AbortError')}
 return asset;
}
