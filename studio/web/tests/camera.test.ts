import {describe,it,expect} from 'vitest';
import * as THREE from 'three';
import {fitCamera} from '../src/camera';
const board=()=>new THREE.Box3(new THREE.Vector3(-.0258,0,-.021),new THREE.Vector3(.0258,.0115,.02225));
const deg=(r:number)=>r*180/Math.PI;
function project(box:THREE.Box3,aspect:number,fov:number,fit:{position:THREE.Vector3;target:THREE.Vector3}){
 const camera=new THREE.PerspectiveCamera(fov,aspect,.001,10);camera.position.copy(fit.position);camera.up.set(0,1,0);camera.lookAt(fit.target);camera.updateMatrixWorld(true);camera.updateProjectionMatrix();
 const xs:number[]=[],ys:number[]=[];
 for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z]){const p=new THREE.Vector3(x,y,z).project(camera);xs.push(p.x);ys.push(p.y)}
 return {minX:Math.min(...xs),maxX:Math.max(...xs),minY:Math.min(...ys),maxY:Math.max(...ys)};
}
describe('fitCamera (authored scene view)',()=>{
 it('looks at the bounds centre from the authored elevation',()=>{
  const box=board(),fit=fitCamera(box,1152/820,38,62,0);
  expect(fit.target.distanceTo(box.getCenter(new THREE.Vector3()))).toBeLessThan(1e-12);
  const d=fit.position.clone().sub(fit.target);expect(deg(Math.asin(d.y/d.length()))).toBeCloseTo(62,6);expect(d.length()).toBeCloseTo(fit.distance,9);
 });
 it('azimuth 0 puts the camera on the +Z side, positive azimuth turns it counter-clockwise seen from above (towards +X)',()=>{
  const c=(az:number)=>{const f=fitCamera(board(),1.4,38,60,az);return f.position.clone().sub(f.target)};
  const a=c(0);expect(a.z).toBeGreaterThan(0);expect(Math.abs(a.x)).toBeLessThan(1e-12);
  const r=c(90);expect(r.x).toBeGreaterThan(0);expect(Math.abs(r.z)).toBeLessThan(1e-9);
  const l=c(-90);expect(l.x).toBeLessThan(0);expect(c(180).z).toBeLessThan(0);
  // Same elevation whatever the azimuth.
  for(const az of [-135,-45,30,120])expect(deg(Math.asin(c(az).y/c(az).length()))).toBeCloseTo(60,6);
 });
 it('with azimuth 0 the +X axis is to the right and -Z (USB end) is towards the top of the screen',()=>{
  const f=fitCamera(board(),1.4,38,62,0),camera=new THREE.PerspectiveCamera(38,1.4);camera.position.copy(f.position);camera.lookAt(f.target);camera.updateMatrixWorld(true);
  const c=f.target.clone();
  const a=new THREE.Vector3(f.target.x+.01,f.target.y,f.target.z).project(camera),b=new THREE.Vector3(f.target.x,f.target.y,f.target.z-.01).project(camera),o=c.clone().project(camera);
  expect(a.x).toBeGreaterThan(o.x);expect(Math.abs(a.y-o.y)).toBeLessThan(1e-9);expect(b.y).toBeGreaterThan(o.y);expect(Math.abs(b.x-o.x)).toBeLessThan(1e-9);
 });
 for(const [aspect,name] of [[1152/820,'1152x820'],[390/440,'phone portrait'],[2.4,'wide']] as const)
  it(`fits the whole bounds inside the frustum and fills the limiting dimension (${name})`,()=>{
   for(const [el,az] of [[62,0],[30,35],[89,0],[5,-120]]){
    const box=board(),fit=fitCamera(box,aspect,38,el,az,.8),p=project(box,aspect,38,fit);
    for(const v of [p.minX,p.maxX,p.minY,p.maxY])expect(Math.abs(v)).toBeLessThanOrEqual(.8+1e-6);
    // Tight: the limiting side reaches the fill fraction.
    expect(Math.max(Math.abs(p.minX),Math.abs(p.maxX),Math.abs(p.minY),Math.abs(p.maxY))).toBeGreaterThan(.8-1e-6);
   }
  });
 it('the board spans 70-80 % of the canvas width at 1152x820, azimuth 0, elevation 62',()=>{
  const box=board(),fit=fitCamera(box,1152/820,38,62,0),p=project(box,1152/820,38,fit),fraction=(p.maxX-p.minX)/2;
  expect(fraction).toBeGreaterThan(.7);expect(fraction).toBeLessThan(.85);
 });
 it('scale-aware: a 10x board keeps the same framing at 10x the distance',()=>{
  const small=fitCamera(board(),1.4,38,62,0),big=board();big.min.multiplyScalar(10);big.max.multiplyScalar(10);
  expect(fitCamera(big,1.4,38,62,0).distance/small.distance).toBeCloseTo(10,6);
 });
});
