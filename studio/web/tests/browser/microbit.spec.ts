import {test,expect,type Page,type Download} from '@playwright/test';
import {readFile} from 'node:fs/promises';
// A contract-conformant board is exported to a GLB inside the page (GLTFExporter from the contract fixture) and served
// through page.route, so these tests also exercise the real glTF round trip of userData.part_id (extras).
type Cell=[number,number];
const grid=(cells:Cell[])=>Array.from({length:5},(_,y)=>Array.from({length:5},(_,x)=>cells.some(([cx,cy])=>cx===x&&cy===y)?255:0));
const A_CELLS:Cell[]=[[0,0],[0,1],[0,2],[0,3],[0,4]],B_CELLS:Cell[]=[[4,0],[4,1],[4,2],[4,3]],LOGO_CELLS:Cell[]=[[1,2],[2,2],[3,2]];
const key=(cells:Cell[])=>cells.map(([x,y])=>x+','+y).sort();
const scene=(scale=1)=>({schemaVersion:1,kind:'scene',id:'microbit-test',title:'Test micro:bit',duration:4,mode:'interactive',
 instances:[{id:'Board',asset:'board.glb',behavior:'microbit',position:[0,0,0],rotation:[0,0,0],scale:[scale,scale,scale]}],tracks:[],
 patternBindings:[{source:'a',target:'Board',released:grid([]),pressed:grid(A_CELLS)},{source:'b',target:'Board',released:grid([]),pressed:grid(B_CELLS)},{source:'logo',target:'Board',released:grid([]),pressed:grid(LOGO_CELLS)}]});
async function exportBoard(page:Page,kind:'board'|'bad'='board'){
 return Buffer.from(await page.evaluate(async kind=>{
  const {makeContractBoard}=await import('/tests/fixtures/contract-board.ts');
  const {GLTFExporter}=await import('/node_modules/three/examples/jsm/exporters/GLTFExporter.js');
  const root=makeContractBoard();if(kind==='bad')root.children.pop();// a board missing its last part
  const bytes=new Uint8Array(await new GLTFExporter().parseAsync(root,{binary:true}) as ArrayBuffer);
  let text='';for(const b of bytes)text+=String.fromCharCode(b);return btoa(text);
 },kind),'base64');
}
const errorsOf=(page:Page)=>{const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});return errors};
async function openBoard(page:Page,scale=1){
 await page.goto('/');await expect(page.getByText('Ready · 3 objects')).toBeVisible();
 const glb=await exportBoard(page);
 await page.route('**/board.glb',route=>route.fulfill({body:glb,contentType:'model/gltf-binary'}));
 await page.route('**/board.scene.json',route=>route.fulfill({json:scene(scale)}));
 await page.goto('/?scene=board.scene.json');await expect(page.getByRole('heading',{name:'Test micro:bit'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Hold A'})).toBeVisible();
}
// Capture is triggered programmatically: clicking the button with a pointer would blur (and so release) a held inspector control.
async function receipt(page:Page){
 const downloads:Download[]=[],collect=(d:Download)=>downloads.push(d);page.on('download',collect);
 await page.evaluate(()=>document.querySelector<HTMLButtonElement>('#capture')!.click());await expect.poll(()=>downloads.length).toBe(2);page.off('download',collect);
 return JSON.parse(await readFile((await downloads.find(d=>d.suggestedFilename().endsWith('.json'))!.path())!,'utf8'));
}
async function board(page:Page){
 const data=(await receipt(page)).scene.instances.find((i:{id:string})=>i.id==='Board').channels as Record<string,number>;
 return {a:data.a,b:data.b,logo:data.logo,lit:Object.keys(data).filter(k=>k.startsWith('led.')&&data[k]>0).map(k=>k.split('.').slice(1).join(',')).sort()};
}
const readout=(page:Page)=>page.getByTestId('channel-value');
// Part labels stay positioned while Anchors is off, so their rects say where a part is on screen.
async function partPoint(page:Page,part:string){
 const label=page.locator('.part-label[data-part="'+part+'"]');await expect(label).toHaveCount(1);
 await expect.poll(()=>label.evaluate(el=>(el as HTMLElement).style.transform)).not.toBe('');
 return label.evaluate(el=>{const r=el.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}});
}
async function emptyDrag(page:Page){
 const box=(await page.locator('canvas').boundingBox())!,x=box.x+box.width*.85,y=box.y+box.height*.2;
 const before=(await receipt(page)).camera.position;
 await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(x-120,y+40,{steps:6});await page.mouse.up();
 const after=(await receipt(page)).camera.position;return before.some((v:number,i:number)=>Math.abs(v-after[i])>1e-6);
}
async function mouseHold(page:Page,part:string){const p=await partPoint(page,part);await page.mouse.move(p.x,p.y);await page.mouse.down()}

test('inspector Hold A lights the A pattern and releasing clears it',async({page})=>{
 const errors=errorsOf(page);await openBoard(page);
 await expect(readout(page)).toHaveText('A released · B released · Logo released · 0 LEDs lit');
 await expect(page.getByRole('button',{name:'Hold B'})).toBeVisible();await expect(page.getByRole('button',{name:'Hold logo'})).toBeVisible();
 await page.getByRole('button',{name:'Hold A'}).focus();await page.keyboard.down('Space');
 await expect(readout(page)).toHaveText('A pressed · B released · Logo released · 5 LEDs lit');
 expect(await board(page)).toEqual({a:1,b:0,logo:0,lit:key(A_CELLS)});
 await page.keyboard.up('Space');
 await expect(readout(page)).toHaveText('A released · B released · Logo released · 0 LEDs lit');
 expect(await board(page)).toEqual({a:0,b:0,logo:0,lit:[]});
 await expect(page.getByText('Pattern bindings control the LEDs.')).toBeVisible();
 await page.getByRole('button',{name:'Hold logo'}).focus();await page.keyboard.down('Enter');
 await expect(readout(page)).toContainText('Logo pressed · 3 LEDs lit');expect((await board(page)).lit).toEqual(key(LOGO_CELLS));
 await page.keyboard.up('Enter');await expect(readout(page)).toContainText('0 LEDs lit');
 expect(errors).toEqual([]);
});
test('every contract part has a label that keeps its position when Anchors is off',async({page})=>{
 await openBoard(page);
 expect(await page.locator('.part-label').count()).toBe(46);
 await expect(page.locator('.part-label[data-part="btn_a"]')).toBeVisible();
 await page.getByText('View options',{exact:true}).click();await page.getByLabel('Anchors').uncheck();
 await expect(page.locator('.part-label[data-part="btn_a"]')).toBeHidden();
 const p=await partPoint(page,'btn_a'),box=(await page.locator('canvas').boundingBox())!;
 expect(p.x).toBeGreaterThan(box.x);expect(p.x).toBeLessThan(box.x+box.width);expect(p.y).toBeGreaterThan(box.y);expect(p.y).toBeLessThan(box.y+box.height);
});
test('pointer hold on the A part lights the pattern and disables orbit until release',async({page})=>{
 const errors=errorsOf(page);await openBoard(page);
 await page.getByText('View options',{exact:true}).click();await page.getByLabel('Anchors').uncheck();
 expect(await emptyDrag(page)).toBe(true);
 await mouseHold(page,'btn_a');
 await expect(readout(page)).toContainText('A pressed · B released');await expect(readout(page)).toContainText('5 LEDs lit');
 expect(await board(page)).toEqual({a:1,b:0,logo:0,lit:key(A_CELLS)});
 const held=(await receipt(page)).camera.position,p=await partPoint(page,'btn_a');
 await page.mouse.move(p.x-90,p.y+60,{steps:6});await page.waitForTimeout(100);
 expect((await receipt(page)).camera.position).toEqual(held);
 await page.mouse.up();
 await expect(readout(page)).toContainText('0 LEDs lit');expect(await board(page)).toEqual({a:0,b:0,logo:0,lit:[]});
 await expect(page.getByRole('button',{name:'Board / 01'})).toHaveAttribute('aria-pressed','true');
 expect(await emptyDrag(page)).toBe(true);
 expect(errors).toEqual([]);
});
test('pointer hold works on the B part and on the logo',async({page})=>{
 await openBoard(page);
 await mouseHold(page,'btn_b');await expect(readout(page)).toContainText('B pressed · Logo released · 4 LEDs lit');
 expect((await board(page)).lit).toEqual(key(B_CELLS));await page.mouse.up();await expect(readout(page)).toContainText('0 LEDs lit');
 await mouseHold(page,'logo_touch');await expect(readout(page)).toContainText('Logo pressed · 3 LEDs lit');
 expect((await board(page)).lit).toEqual(key(LOGO_CELLS));await page.mouse.up();await expect(readout(page)).toContainText('0 LEDs lit');
});
test('A and B held together, releasing A leaves the B pattern',async({page})=>{
 const errors=errorsOf(page);await openBoard(page);
 await mouseHold(page,'btn_a');await page.getByRole('button',{name:'Hold B'}).focus();await page.keyboard.down('Space');
 await expect(readout(page)).toHaveText('A pressed · B pressed · Logo released · 9 LEDs lit');
 expect((await board(page)).lit).toEqual(key([...A_CELLS,...B_CELLS]));
 await page.mouse.up();
 await expect(readout(page)).toHaveText('A released · B pressed · Logo released · 4 LEDs lit');
 expect(await board(page)).toEqual({a:0,b:1,logo:0,lit:key(B_CELLS)});
 await page.keyboard.up('Space');await expect(readout(page)).toContainText('0 LEDs lit');
// And the other way round: release the keyboard hold first, the pointer hold stays.
 await mouseHold(page,'btn_a');await page.getByRole('button',{name:'Hold B'}).focus();await page.keyboard.down('Space');
 await expect(readout(page)).toContainText('9 LEDs lit');await page.keyboard.up('Space');
 await expect(readout(page)).toHaveText('A pressed · B released · Logo released · 5 LEDs lit');
 expect((await board(page)).lit).toEqual(key(A_CELLS));await page.mouse.up();await expect(readout(page)).toContainText('0 LEDs lit');
 expect(errors).toEqual([]);
});
for(const kind of ['pointercancel','blur','visibilitychange'] as const){
 test(kind+' while holding releases the channel and re-enables orbit',async({page})=>{
  const errors=errorsOf(page);await openBoard(page);
  await mouseHold(page,'btn_a');await expect(readout(page)).toContainText('5 LEDs lit');
  await page.evaluate(kind=>{
   if(kind==='pointercancel')document.querySelector('canvas')!.dispatchEvent(new PointerEvent('pointercancel',{pointerId:1,bubbles:true}));
   else if(kind==='blur')window.dispatchEvent(new Event('blur'));
   else{Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'));Object.defineProperty(document,'hidden',{configurable:true,get:()=>false})}
  },kind);
  await expect(readout(page)).toContainText('A released');await expect(readout(page)).toContainText('0 LEDs lit');
  expect(await board(page)).toEqual({a:0,b:0,logo:0,lit:[]});
  await page.mouse.up();expect(await emptyDrag(page)).toBe(true);
  expect(errors).toEqual([]);
 });
}
// Regression: releasing the canvas capture on blur/hidden let a later mouse-up outside the canvas skip OrbitControls' own pointerup,
// leaving it rotating on plain hover.
for(const kind of ['blur','visibilitychange'] as const){
 test(kind+' while holding, then mouse up outside the canvas, does not leave orbit dragging on hover',async({page})=>{
  const errors=errorsOf(page);await openBoard(page);
  await mouseHold(page,'btn_a');await expect(readout(page)).toContainText('5 LEDs lit');
  await page.evaluate(kind=>{
   if(kind==='blur')window.dispatchEvent(new Event('blur'));
   else{Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'));Object.defineProperty(document,'hidden',{configurable:true,get:()=>false})}
  },kind);
  await expect(readout(page)).toContainText('0 LEDs lit');
  await page.mouse.move(2,2);await page.mouse.up();
  const before=(await receipt(page)).camera.position,box=(await page.locator('canvas').boundingBox())!;
  await page.mouse.move(box.x+box.width*.5,box.y+box.height*.3,{steps:8});await page.mouse.move(box.x+box.width*.8,box.y+box.height*.6,{steps:8});
  await page.evaluate(()=>new Promise<void>(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>requestAnimationFrame(()=>r())))));
  expect((await receipt(page)).camera.position).toEqual(before);
  expect(await emptyDrag(page)).toBe(true);
  expect(errors).toEqual([]);
 });
}
test('pointer leaving the canvas while holding still releases on mouse up',async({page})=>{
 await openBoard(page);await mouseHold(page,'btn_a');await expect(readout(page)).toContainText('5 LEDs lit');
 await page.mouse.move(2,2,{steps:8});await expect(readout(page)).toContainText('5 LEDs lit');
 await page.mouse.up();await expect(readout(page)).toContainText('0 LEDs lit');expect(await emptyDrag(page)).toBe(true);
});
test('scene swap while holding leaves no stuck channel or disabled orbit',async({page})=>{
 const errors=errorsOf(page);await openBoard(page);
 await mouseHold(page,'btn_a');await expect(readout(page)).toContainText('5 LEDs lit');
 await page.evaluate(()=>{document.querySelector<HTMLButtonElement>('#load')!.click();document.querySelector<HTMLInputElement>('#scene-url')!.value='single.json';document.querySelector('form')!.dispatchEvent(new Event('submit',{cancelable:true}))});
 await expect(page.getByRole('button',{name:'Solo / 01'})).toBeVisible();await expect(page.locator('.part-label')).toHaveCount(0);
 await page.mouse.up();expect(await emptyDrag(page)).toBe(true);
 await page.evaluate(()=>{document.querySelector<HTMLButtonElement>('#load')!.click();document.querySelector<HTMLInputElement>('#scene-url')!.value='board.scene.json';document.querySelector('form')!.dispatchEvent(new Event('submit',{cancelable:true}))});
 await expect(page.getByRole('button',{name:'Hold A'})).toBeVisible();await expect(readout(page)).toContainText('0 LEDs lit');
 await mouseHold(page,'btn_a');await expect(readout(page)).toContainText('5 LEDs lit');await page.mouse.up();await expect(readout(page)).toContainText('0 LEDs lit');
 expect(errors).toEqual([]);
});
test('mount and unmount three times, once while a part is held, produce no errors',async({page})=>{
 const errors=errorsOf(page);await openBoard(page);
 for(let round=0;round<3;round++){
  await page.evaluate(async()=>{
   const {mountPreview}=await import('/src/preview.ts');
   const host=document.createElement('div');host.id='extra';host.style.cssText='position:fixed;inset:0;z-index:9999;background:#fff';document.body.append(host);
   (window as unknown as {__extra:{host:HTMLElement;stop:()=>void}}).__extra={host,stop:mountPreview(host)};
   while(!host.querySelector('.part-label'))await new Promise(r=>setTimeout(r,20));
  });
  if(round===1){
   const p=await page.evaluate(async()=>{
    const label=(window as unknown as {__extra:{host:HTMLElement}}).__extra.host.querySelector<HTMLElement>('.part-label[data-part="btn_a"]')!;
    while(!label.style.transform)await new Promise(r=>setTimeout(r,20));const r=label.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};
   });
   await page.mouse.move(p.x,p.y);await page.mouse.down();
   await expect.poll(()=>page.evaluate(()=>(window as unknown as {__extra:{host:HTMLElement}}).__extra.host.querySelector('#value')!.textContent)).toContain('5 LEDs lit');
  }
  const children=await page.evaluate(()=>{const e=(window as unknown as {__extra:{host:HTMLElement;stop:() => void}}).__extra;e.stop();e.stop();const n=e.host.childElementCount;e.host.remove();return n});
  expect(children).toBe(0);
  if(round===1)await page.mouse.up();
 }
 await expect(readout(page)).toContainText('0 LEDs lit');expect(await emptyDrag(page)).toBe(true);
 expect(errors).toEqual([]);
});
test('a scene replaced during a micro:bit load never reports a contract error',async({page})=>{
 await page.goto('/');await expect(page.getByText('Ready · 3 objects')).toBeVisible();
 const bad=await exportBoard(page,'bad');
 const result=await page.evaluate(async b64=>{
  const {loadMicrobit}=await import('/src/microbit.ts');
  const bytes=Uint8Array.from(atob(b64),c=>c.charCodeAt(0)),original=window.fetch;
  // The response ignores the signal, as if the bytes had already arrived when the scene was replaced.
  window.fetch=(()=>Promise.resolve(new Response(bytes))) as typeof fetch;
  const controller=new AbortController();controller.abort();
  try{await loadMicrobit('/bad.glb',controller.signal);return 'resolved'}catch(e){return (e as Error).name+': '+(e as Error).message}finally{window.fetch=original}
 },bad.toString('base64'));
 expect(result).toMatch(/^AbortError/);
});
test('instance scale 10x keeps picking, labels and framing aligned',async({page})=>{
 const errors=errorsOf(page);await openBoard(page,10);
 const box=(await page.locator('canvas').boundingBox())!;
 for(const part of ['btn_a','btn_b','logo_touch']){
  const p=await partPoint(page,part);
  expect(p.x).toBeGreaterThan(box.x);expect(p.x).toBeLessThan(box.x+box.width);expect(p.y).toBeGreaterThan(box.y);expect(p.y).toBeLessThan(box.y+box.height);
 }
 await mouseHold(page,'btn_a');await expect(readout(page)).toContainText('A pressed · B released');expect((await board(page)).lit).toEqual(key(A_CELLS));await page.mouse.up();
 await mouseHold(page,'btn_b');await expect(readout(page)).toContainText('B pressed');expect((await board(page)).lit).toEqual(key(B_CELLS));await page.mouse.up();
 await expect(readout(page)).toContainText('0 LEDs lit');
 // A scene about 0.5 m wide is framed by the scaled stage, not clipped by the default camera near plane.
 const camera=(await receipt(page)).camera,d=Math.hypot(...camera.position.map((v:number,i:number)=>v-camera.target[i]));
 expect(camera.near).toBeLessThan(d);expect(camera.near).toBeLessThan(.5);expect(d).toBeLessThan(5);
 expect(errors).toEqual([]);
});
