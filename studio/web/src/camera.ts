import * as THREE from 'three';
// Authored scene view: the camera looks at the bounds centre from `elevation` degrees above the ground plane and `azimuth` degrees around it.
// Azimuth 0 puts the camera on the +Z side looking toward -Z; positive azimuth turns it counter-clockwise seen from above (towards +X).
// The distance is the smallest one at which every corner of the bounds projects inside +-fill of the canvas on both axes, so the limiting dimension fills `fill`.
export function fitCamera(box:THREE.Box3,aspect:number,fovDegrees:number,elevationDegrees:number,azimuthDegrees:number,fill=.8){
 const target=box.getCenter(new THREE.Vector3()),el=THREE.MathUtils.degToRad(elevationDegrees),az=THREE.MathUtils.degToRad(azimuthDegrees);
 const direction=new THREE.Vector3(Math.sin(az)*Math.cos(el),Math.sin(el),Math.cos(az)*Math.cos(el));// from the target towards the camera
 const forward=direction.clone().negate(),right=new THREE.Vector3().crossVectors(forward,new THREE.Vector3(0,1,0)).normalize(),up=new THREE.Vector3().crossVectors(right,forward).normalize();
 const tanY=Math.tan(THREE.MathUtils.degToRad(fovDegrees/2)),tanX=tanY*Math.max(aspect,1e-6);
 // A corner at offset (x,y,z) from the target in view axes projects to x/((d+z)tanX), y/((d+z)tanY): each must stay within `fill`.
 let distance=0;
 for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z]){
  const r=new THREE.Vector3(x,y,z).sub(target),vx=r.dot(right),vy=r.dot(up),vz=r.dot(forward);
  distance=Math.max(distance,Math.abs(vx)/(fill*tanX)-vz,Math.abs(vy)/(fill*tanY)-vz);
 }
 return {target,position:target.clone().addScaledVector(direction,distance),distance};
}
