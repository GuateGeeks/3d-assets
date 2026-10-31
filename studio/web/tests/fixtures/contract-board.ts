import * as THREE from 'three';
import contract from '../../../examples/microbit/node-contract.json';
// Contract fixture: a plausible 0.052 x 0.042 m board in glTF convention (Y up, LED face +Y,
// edge connector toward +Z). One mesh per contract part, found only through userData.part_id.
// Node names are deliberately opaque so nothing can resolve parts by name. No Node-only APIs:
// the browser also builds a GLB from this through GLTFExporter.
const PCB_TOP=.0008;
// [width, height, depth, x, z, lift] ; the box rests on lift above the PCB top surface.
const LAYOUT:Record<string,[number,number,number,number,number,number]>={
 pcb:[.052,.0016,.042,0,0,0],edge_connector:[.05,.0016,.002,0,.02,0],
 pin_0:[.005,.0008,.003,-.02,.0165,0],pin_1:[.005,.0008,.003,-.01,.0165,0],pin_2:[.005,.0008,.003,0,.0165,0],pin_3v:[.005,.0008,.003,.01,.0165,0],pin_gnd:[.005,.0008,.003,.02,.0165,0],
 btn_a:[.006,.0035,.006,-.0195,0,0],btn_b:[.006,.0035,.006,.0195,0,0],btn_a_cap:[.0035,.002,.0035,-.0195,0,.0035],btn_b_cap:[.0035,.002,.0035,.0195,0,.0035],
 logo_touch:[.004,.0008,.003,0,-.016,0],usb:[.008,.0028,.004,0,-.019,0],reset_btn:[.003,.0015,.003,.0075,.0108,0],battery_socket:[.005,.003,.006,-.0225,-.015,0],
 speaker:[.006,.002,.006,.02,-.0125,0],mic:[.002,.001,.002,.01,-.016,0],mic_led:[.0012,.0006,.0012,.01,-.0125,0],processor:[.006,.001,.006,-.02,.01,0],
 antenna:[.006,.0005,.004,.02,.01,0],accel_compass:[.003,.001,.003,.015,.0095,0]
};
for(let y=0;y<5;y++)for(let x=0;x<5;x++)LAYOUT[`led_${x}_${y}`]=[.0035,.0008,.0018,(x-2)*.0072,(y-2)*.0064,0];
export function makeContractBoard():THREE.Group{
 const board=new THREE.Group();let n=0;
 for(const part of contract.parts){
  const [w,h,d,x,z,lift]=LAYOUT[part.id];
  const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),new THREE.MeshStandardMaterial({color:part.id.startsWith('led_')?0x331111:part.id==='pcb'?0x1a6b3a:0xb0b0b0}));
  mesh.name='node_'+(n++);mesh.userData.part_id=part.id;mesh.position.set(x,part.id==='pcb'||part.id==='edge_connector'?0:PCB_TOP+lift+h/2,z);
  board.add(mesh);
 }
 return board;
}
