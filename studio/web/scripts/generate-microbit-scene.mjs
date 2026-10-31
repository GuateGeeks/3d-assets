// Deterministic generator for the micro:bit demo scene. Run from studio/web: node scripts/generate-microbit-scene.mjs
// It writes the owned copies (studio/examples/microbit and studio/web/public/microbit); the output depends only on this file.
// The three 5x5 patterns and the LED timeline are authored stand-ins for a future simulator feed, not simulator output.
import {writeFile,mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const LEVEL={'.':0,'+':80,'#':255};// off, dim, full brightness (0..255)
const PATTERNS={
 // Rows are LED rows (y, top to bottom) and columns are x, matching led.X.Y.
 heart:['.#.#.','#####','#####','.###.','..#..'],
 smile:['.....','.#.#.','.....','#...#','.+++.'],
 check:['.....','....#','...#.','#.#..','.#...']
};
const grid=name=>PATTERNS[name].map(row=>[...row].map(c=>LEVEL[c]));
const SEQUENCE=['heart','smile','check'];
const DURATION=6,SLOT=DURATION/SEQUENCE.length;
// Each LED fades in, holds and cross-fades into the next pattern, then fades out at the end.
function ledTracks(){
 const tracks=[];
 for(let x=0;x<5;x++)for(let y=0;y<5;y++){
  const keyframes=[{time:0,value:0}];
  SEQUENCE.forEach((name,k)=>{const value=grid(name)[y][x],start=k*SLOT;keyframes.push({time:+(start+.4).toFixed(3),value},{time:+(start+SLOT-.4).toFixed(3),value})});
  keyframes.push({time:DURATION,value:0});
  tracks.push({target:'Board',channel:`led.${x}.${y}`,keyframes});
 }
 return tracks;
}
export function buildScene(){
 return {
  schemaVersion:1,kind:'scene',id:'microbit-v2-demo',title:'micro:bit V2 interactive',duration:DURATION,mode:'interactive',
  // The board is 51.6 mm wide and is never rescaled; the underside parts reach 6.3 mm below the origin, so it rests just above the stage ground.
  instances:[{id:'Board',asset:'microbit.glb',behavior:'microbit',position:[0,.0066,0],rotation:[0,0,0],scale:[1,1,1]}],
  patternBindings:[
   {source:'a',target:'Board',released:grid('heart').map(r=>r.map(()=>0)),pressed:grid('heart')},
   {source:'b',target:'Board',released:grid('smile').map(r=>r.map(()=>0)),pressed:grid('smile')},
   {source:'logo',target:'Board',released:grid('check').map(r=>r.map(()=>0)),pressed:grid('check')}
  ],
  tracks:ledTracks()
 };
}
// One top-level key per line and one track or binding per line keeps diffs reviewable.
export function format(scene){
 const line=(key,value)=>Array.isArray(value)&&value.length>1&&key!=='instances'?` "${key}": [\n${value.map(v=>'  '+JSON.stringify(v)).join(',\n')}\n ]`:` "${key}": ${JSON.stringify(value)}`;
 return '{\n'+Object.entries(scene).map(([k,v])=>line(k,v)).join(',\n')+'\n}\n';
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const text=format(buildScene());
 for(const folder of ['../../examples/microbit/','../public/microbit/']){
  await mkdir(new URL(folder,import.meta.url),{recursive:true});
  await writeFile(new URL(folder+'microbit.scene.json',import.meta.url),text);
 }
 console.log('micro:bit scene:',text.length,'bytes');
}
