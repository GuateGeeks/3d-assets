// Functional captures of the micro:bit project through the production preview served by `studio.py preview --project`.
// The opening view is the scene's authored camera. Set CAPTURE_TOPDOWN=1 for the extra top-down views. Run from studio/web: PREVIEW_URL=http://127.0.0.1:4395/ node scripts/capture-microbit-evidence.mjs <output-directory>
// The output directory is REQUIRED and must not exist yet or must be empty: the script refuses to write into a folder that already holds files, so reviewed evidence is never overwritten or extended. Use a new folder name for every run.
// Software rendering (SwiftShader): functional evidence only. It proves what the app reports and draws, not GPU performance and not a visual approval.
import {chromium} from '@playwright/test';
import {createHash} from 'node:crypto';
import {mkdir,readdir,readFile,rm,writeFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
if(!process.argv[2]){console.error('usage: node scripts/capture-microbit-evidence.mjs <new-output-directory>  (required; the directory must not exist or must be empty)');process.exit(2)}
const out=resolve(process.argv[2]);
// Guard before anything else (the browser is launched further down): never write into a folder that already holds files.
const existing=await readdir(out).catch(e=>{if(e.code==='ENOENT')return [];throw e});
if(existing.length){console.error('refusing to run: '+out+' already exists and is not empty ('+existing.length+' entries). Reviewed evidence is never overwritten; choose a new output directory.');process.exit(3)}
const base=process.env.PREVIEW_URL||'http://127.0.0.1:4395/';
const url=new URL('?scene=project/scene.json',base).href;
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const key=cells=>cells.map(([x,y])=>x+','+y).sort();
const EXPECT={
 a:key([[1,0],[3,0],[0,1],[1,1],[2,1],[3,1],[4,1],[0,2],[1,2],[2,2],[3,2],[4,2],[1,3],[2,3],[3,3],[2,4]]),
 b:key([[1,1],[3,1],[0,3],[4,3],[1,4],[2,4],[3,4]]),
 logo:key([[4,1],[3,2],[0,3],[2,3],[1,4]])
};
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-webgl']});
const summary={schemaVersion:1,kind:'microbit-evidence-summary',url,viewport:{width:1440,height:1000},rendering:'SwiftShader software WebGL via headless Chromium; GPU performance NOT_RUN',checks:[],captures:[],console:[],glbRequests:[]};
try{
 const page=await browser.newPage({viewport:summary.viewport});
 page.on('pageerror',e=>summary.console.push('pageerror: '+e.message));
 page.on('console',m=>{if(['error','warning'].includes(m.type()))summary.console.push(m.type()+': '+m.text())});
 page.on('response',async r=>{if(r.url().endsWith('.glb'))summary.glbRequests.push({url:r.url(),status:r.status(),contentType:r.headers()['content-type'],sha256:sha(await r.body()),bytes:(await r.body()).length})});
 await page.goto(url);
 await page.getByRole('heading',{name:'micro:bit V2 interactive'}).waitFor();await page.getByRole('button',{name:'Hold A'}).waitFor();
 await page.waitForFunction(()=>document.querySelectorAll('.part-label').length===46);
 const readout=()=>page.getByTestId('channel-value').textContent();
 async function labelPoint(part){
  const label=page.locator('.part-label[data-part="'+part+'"]');
  await page.waitForFunction(p=>!!document.querySelector('.part-label[data-part="'+p+'"]')?.style.transform,part);
  return label.evaluate(el=>{const r=el.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}});
 }
 // Capture is triggered programmatically so a held pointer or key is not released by the click.
 async function capture(name){
  const dir=join(out,name);await mkdir(dir,{recursive:true});const saved=[],tasks=[];
  const collect=d=>tasks.push(d.saveAs(join(dir,d.suggestedFilename())).then(()=>saved.push(d.suggestedFilename())));page.on('download',collect);
  await page.evaluate(()=>document.querySelector('#capture').click());
  const deadline=Date.now()+15000;while(tasks.length<2&&Date.now()<deadline)await page.waitForTimeout(50);
  await Promise.all(tasks);page.off('download',collect);
  const png=saved.find(f=>f.endsWith('.png')),json=saved.find(f=>f.endsWith('.json'));
  const receipt=JSON.parse(await readFile(join(dir,json),'utf8')),pngBytes=await readFile(join(dir,png));
  const channels=receipt.scene.instances.find(i=>i.id==='Board').channels,lit=Object.keys(channels).filter(k=>k.startsWith('led.')&&channels[k]>0).map(k=>k.split('.').slice(1).join(',')).sort();
  const entry={name,png:name+'/'+png,receipt:name+'/'+json,sha256:sha(pngBytes),bytes:pngBytes.length,receiptMatchesPng:receipt.image.sha256===sha(pngBytes)&&receipt.image.bytes===pngBytes.length,
   channels:{a:channels.a,b:channels.b,logo:channels.logo},litLeds:lit,cameraDistanceM:+Math.hypot(...receipt.camera.position.map((v,i)=>v-receipt.camera.target[i])).toFixed(5),anchorsOverlay:receipt.overlays,viewport:receipt.viewport};
  summary.captures.push(entry);return entry;
 }
 const check=(name,pass,detail)=>summary.checks.push({name,status:pass?'PASS':'FAIL',detail});
 const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
 check('project scene loaded from the project inventory',summary.glbRequests.some(r=>r.url.includes('/project/microbit.glb')&&r.status===200),summary.glbRequests);
 const rest=await capture('rest');check('rest: no LED lit',rest.litLeds.length===0&&rest.channels.a===0&&rest.channels.b===0&&rest.channels.logo===0,rest.litLeds);
 for(const [name,part,source] of [['a-held','btn_a','a'],['b-held','btn_b','b'],['logo-held','logo_touch','logo']]){
  const p=await labelPoint(part);await page.mouse.move(p.x,p.y);await page.mouse.down();
  await page.waitForFunction(()=>!/ 0 LEDs lit/.test(document.querySelector('#value').textContent));
  const entry=await capture(name);await page.mouse.up();
  check(name+': pointer hold lights the '+source+' pattern',same(entry.litLeds,EXPECT[source])&&entry.channels[source]===1,{readout:await readout(),lit:entry.litLeds});
  await page.waitForFunction(()=>/ 0 LEDs lit/.test(document.querySelector('#value').textContent));
 }
if(process.env.CAPTURE_TOPDOWN){
 // Optional (CAPTURE_TOPDOWN=1) extra evidence view (not a product default): orbit by mouse drags in empty canvas until the camera looks almost straight down at the LED face,
 // then hold each of A, B and logo from the keyboard. OrbitControls stops short of the zenith, so the final elevation is recorded.
 const canvasBox=await page.locator('canvas').boundingBox();
 const elevation=r=>{const [px,py,pz]=r.camera.position,[tx,ty,tz]=r.camera.target;return Math.asin((py-ty)/Math.hypot(px-tx,py-ty,pz-tz))*180/Math.PI};
 const latest=async()=>{const n=summary.captures.length;await capture('probe-camera');const c=summary.captures.pop();const r=JSON.parse(await readFile(join(out,c.receipt),'utf8'));await rm(join(out,'probe-camera'),{recursive:true,force:true});return r};
 let top=await latest();
 for(let i=0;i<8&&elevation(top)<80;i++){
  const x=canvasBox.x+canvasBox.width*.9,y=canvasBox.y+canvasBox.height*.15;
  await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(x,y+250,{steps:10});await page.mouse.up();await page.waitForTimeout(300);top=await latest();
 }
 const topElevation=+elevation(top).toFixed(1);check('top-down view reached (camera elevation above 80 degrees)',topElevation>80,{elevationDegrees:topElevation});
 for(const [name,button,source] of [['topdown-a-held','Hold A','a'],['topdown-b-held','Hold B','b'],['topdown-logo-held','Hold logo','logo']]){
  await page.getByRole('button',{name:button}).focus();await page.keyboard.down('Space');
  await page.waitForFunction(()=>!/ 0 LEDs lit/.test(document.querySelector('#value').textContent));
  const entry=await capture(name);await page.keyboard.up('Space');entry.cameraElevationDegrees=topElevation;
  check(name+': keyboard hold lights the '+source+' pattern in the top-down view',same(entry.litLeds,EXPECT[source])&&entry.channels[source]===1,{lit:entry.litLeds});
  await page.waitForFunction(()=>/ 0 LEDs lit/.test(document.querySelector('#value').textContent));
 }
 // Close-up from the default orientation again: reload.
 await page.goto(url);await page.getByRole('button',{name:'Hold A'}).waitFor();await page.waitForFunction(()=>document.querySelectorAll('.part-label').length===46);
 }
 // Close-up: wheel-zoom towards the board centre and hold A from the keyboard (the pressed cap and the lit LEDs stay in view). Anchors stay on.
 await page.waitForTimeout(500);const box=await page.locator('canvas').boundingBox();await page.mouse.move(box.x+box.width/2,box.y+box.height/2);
 for(let i=0;i<9;i++){await page.mouse.wheel(0,-300);await page.waitForTimeout(60)}
 await page.waitForTimeout(400);
 await page.getByRole('button',{name:'Hold A'}).focus();await page.keyboard.down('Space');
 await page.waitForFunction(()=>!/ 0 LEDs lit/.test(document.querySelector('#value').textContent));
 const close=await capture('closeup-a-held');
 await page.screenshot({path:join(out,'closeup-a-held','page-with-labels.png')});
 await page.keyboard.up('Space');
 check('closeup: keyboard hold of A lights the heart with Anchors on',same(close.litLeds,EXPECT.a)&&close.anchorsOverlay?.anchors===true,{overlays:close.anchorsOverlay,distance:close.cameraDistanceM});
 check('closeup is closer than the default framing',close.cameraDistanceM<rest.cameraDistanceM*.6,{closeup:close.cameraDistanceM,rest:rest.cameraDistanceM});
 check('every receipt records the SHA-256 and size of its PNG',summary.captures.every(c=>c.receiptMatchesPng),summary.captures.map(c=>c.name));
 const noise=summary.console.filter(m=>!/Automatic fallback to software WebGL/.test(m));
 check('no console errors or warnings other than Chromium\'s software-WebGL notice',noise.length===0,summary.console);
 summary.pagePng={path:'closeup-a-held/page-with-labels.png',sha256:sha(await readFile(join(out,'closeup-a-held','page-with-labels.png')))};
}finally{await browser.close()}
summary.status=summary.checks.every(c=>c.status==='PASS')?'PASS':'FAIL';
await writeFile(join(out,'capture-summary.json'),JSON.stringify(summary,null,2)+'\n');
console.log(summary.status,summary.checks.map(c=>c.status+' '+c.name).join('\n'));
process.exit(summary.status==='PASS'?0:1);
