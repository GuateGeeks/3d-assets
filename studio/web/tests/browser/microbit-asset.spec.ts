import {test,expect,type Page,type Download} from '@playwright/test';
import {readFile} from 'node:fs/promises';
// The REAL Blender GLB (studio/web/public/microbit/microbit.glb) with the shipped demo scene, served by the dev server's public folder.
// Nothing is intercepted: the factory meets the real export, the real part geometry and the real default camera.
const SCENE='microbit/microbit.scene.json';
type Cell=[number,number];
const HEART:Cell[]=[[1,0],[3,0],[0,1],[1,1],[2,1],[3,1],[4,1],[0,2],[1,2],[2,2],[3,2],[4,2],[1,3],[2,3],[3,3],[2,4]];
const SMILE:Cell[]=[[1,1],[3,1],[0,3],[4,3],[1,4],[2,4],[3,4]];
const CHECK:Cell[]=[[4,1],[3,2],[0,3],[2,3],[1,4]];
const key=(cells:Cell[])=>cells.map(([x,y])=>x+','+y).sort();
// Console warnings count too: the real model must load without any. Chromium's own notice that the software-WebGL fallback is deprecated
// comes from the test launch flags (swiftshader), not from the page, so it is the one message ignored.
const SOFTWARE_GL=/Automatic fallback to software WebGL has been deprecated/;
const noise=(page:Page)=>{const out:string[]=[];page.on('pageerror',e=>out.push(e.message));page.on('console',m=>{if((m.type()==='error'||m.type()==='warning')&&!SOFTWARE_GL.test(m.text()))out.push(m.type()+': '+m.text())});return out};
async function open(page:Page){
 await page.goto('/?'+new URLSearchParams({scene:SCENE}));
 await expect(page.getByRole('heading',{name:'micro:bit V2 interactive'})).toBeVisible();await expect(page.getByRole('button',{name:'Hold A'})).toBeVisible();
 await expect(page.locator('.part-label')).toHaveCount(46);
}
async function receipt(page:Page){
 const downloads:Download[]=[],collect=(d:Download)=>downloads.push(d);page.on('download',collect);
 await page.evaluate(()=>document.querySelector<HTMLButtonElement>('#capture')!.click());await expect.poll(()=>downloads.length).toBe(2);page.off('download',collect);
 return JSON.parse(await readFile((await downloads.find(d=>d.suggestedFilename().endsWith('.json'))!.path())!,'utf8'));
}
async function board(page:Page){
 const data=(await receipt(page)).scene.instances.find((i:{id:string})=>i.id==='Board').channels as Record<string,number>;
 const leds=Object.keys(data).filter(k=>k.startsWith('led.'));
 return {a:data.a,b:data.b,logo:data.logo,ledChannels:leds.length,lit:leds.filter(k=>data[k]>0).map(k=>k.split('.').slice(1).join(',')).sort(),levels:Object.fromEntries(leds.filter(k=>data[k]>0).map(k=>[k.split('.').slice(1).join(','),data[k]]))};
}
const readout=(page:Page)=>page.getByTestId('channel-value');
async function partPoint(page:Page,part:string){
 const label=page.locator('.part-label[data-part="'+part+'"]');await expect(label).toHaveCount(1);
 await expect.poll(()=>label.evaluate(el=>(el as HTMLElement).style.transform)).not.toBe('');
 return label.evaluate(el=>{const r=el.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}});
}
// The element under the pointer must be the canvas: any overlay in between would swallow the press.
const topElement=(page:Page,p:{x:number;y:number})=>page.evaluate(({x,y})=>{const e=document.elementFromPoint(x,y);return e?e.tagName+'.'+(e.className||'')+'#'+e.id:''},p);
async function mouseHold(page:Page,part:string){const p=await partPoint(page,part);await page.mouse.move(p.x,p.y);await page.mouse.down();return p}

test('real GLB loads with 46 parts, 28 channels and no console noise at rest',async({page})=>{
 const out=noise(page);await open(page);
 await expect(readout(page)).toHaveText('A released · B released · Logo released · 0 LEDs lit');
 const rest=await board(page);expect(rest).toMatchObject({a:0,b:0,logo:0,ledChannels:25,lit:[]});
 const data=(await receipt(page)).scene.instances[0];expect(Object.keys(data.channels).length).toBe(28);
 expect(data.position).toEqual([0,.0066,0]);expect(data.scale).toEqual([1,1,1]);
 expect(out).toEqual([]);
});
test('inspector Hold A, Hold B and Hold logo each light a different non-empty LED set; release clears',async({page})=>{
 const out=noise(page);await open(page);const seen:string[][]=[];
 for(const [name,expected,count] of [['A',HEART,16],['B',SMILE,7],['logo',CHECK,5]] as const){
  const hold=page.getByRole('button',{name:'Hold '+name});await hold.focus();await page.keyboard.down('Space');
  await expect(readout(page)).toContainText(count+' LEDs lit');
  const state=await board(page);expect(state.ledChannels).toBe(25);expect(state.lit.length).toBeGreaterThan(0);expect(state.lit).toEqual(key(expected));seen.push(state.lit);
  await page.keyboard.up('Space');await expect(readout(page)).toContainText('0 LEDs lit');
  expect(await board(page)).toMatchObject({a:0,b:0,logo:0,lit:[]});
 }
 expect(new Set(seen.map(s=>s.join('|'))).size).toBe(3);
 expect(out).toEqual([]);
});
test('pattern brightness levels reach the LED channels (dim and full)',async({page})=>{
 await open(page);const hold=page.getByRole('button',{name:'Hold B'});await hold.focus();await page.keyboard.down('Space');
 await expect(readout(page)).toContainText('7 LEDs lit');
 const {levels}=await board(page);expect(levels['1,1']).toBe(255);expect(levels['2,4']).toBe(80);
 await page.keyboard.up('Space');
});
test('the Board anchor label does not sit in the way of a press at the default framing',async({page})=>{
 const out=noise(page);await open(page);
 for(const part of ['btn_a','btn_b','logo_touch']){
  const p=await partPoint(page,part);
  const hit=await topElement(page,p);
  expect(hit,part+' is covered by '+hit).toMatch(/^(CANVAS|DIV#viewport)/);
 }
 expect(out).toEqual([]);
});
// The instance label sits above the board's top-centre anchor; at the default framing it overlaps the left end of the logo ring. Scanning the
// label's own rectangle must find presses that reach a part, so the label (pointer-events:auto for plain assets) does not swallow them.
// The authored camera moves the label clear of the parts, so this scans the old oblique default view (the same scene without its camera) where the overlap was proven.
for(const viewport of [{width:1280,height:800},{width:390,height:844}])
test(`the Board label does not swallow presses on the part beneath it (${viewport.width}px)`,async({page})=>{
 await page.route('**/microbit/microbit.scene.json',async route=>{const scene=await (await route.fetch()).json();delete scene.camera;await route.fulfill({json:scene})});
 await page.setViewportSize(viewport);await open(page);
 await expect.poll(()=>page.locator('.part-label[data-part="logo_touch"]').evaluate(el=>(el as HTMLElement).style.transform)).not.toBe('');
 const label=await page.locator('.anchor-label[data-id="Board"]').evaluate(el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}});
 let reached=0;
 for(let i=0;i<=8;i++)for(let j=0;j<=4;j++){
  await page.mouse.move(label.x+2+(label.w-4)*i/8,label.y+2+(label.h-4)*j/4);await page.mouse.down();
  if(!/ 0 LEDs lit/.test(await readout(page).textContent()??''))reached++;
  await page.mouse.up();
 }
 expect(reached,'presses inside the Board label that reached a part').toBeGreaterThan(0);
 await expect(page.locator('.anchor-label[data-id="Board"]')).toHaveCSS('pointer-events','none');
});
test('pointer hold on the real A, B and logo parts at the default camera lights their patterns',async({page})=>{
 const out=noise(page);await open(page);
 await mouseHold(page,'btn_a');
 await expect(readout(page)).toContainText('A pressed · B released');await expect(readout(page)).toContainText('16 LEDs lit');
 expect(await board(page)).toMatchObject({a:1,b:0,logo:0,lit:key(HEART)});
 await page.mouse.up();await expect(readout(page)).toContainText('0 LEDs lit');
 await mouseHold(page,'btn_b');await expect(readout(page)).toContainText('B pressed · Logo released · 7 LEDs lit');
 expect((await board(page)).lit).toEqual(key(SMILE));await page.mouse.up();await expect(readout(page)).toContainText('0 LEDs lit');
 await mouseHold(page,'logo_touch');await expect(readout(page)).toContainText('Logo pressed · 5 LEDs lit');
 expect((await board(page)).lit).toEqual(key(CHECK));await page.mouse.up();await expect(readout(page)).toContainText('0 LEDs lit');
 expect(await board(page)).toMatchObject({a:0,b:0,logo:0,lit:[]});
 expect(out).toEqual([]);
});
test('A and B held together combine by per-LED maximum, then releasing A leaves the smile',async({page})=>{
 await open(page);
 await mouseHold(page,'btn_a');await page.getByRole('button',{name:'Hold B'}).focus();await page.keyboard.down('Space');
 const union=[...new Set(key([...HEART,...SMILE]))];await expect(readout(page)).toContainText(union.length+' LEDs lit');
 expect((await board(page)).lit).toEqual(union);
 await page.mouse.up();await expect(readout(page)).toHaveText('A released · B pressed · Logo released · 7 LEDs lit');
 expect((await board(page)).lit).toEqual(key(SMILE));await page.keyboard.up('Space');await expect(readout(page)).toContainText('0 LEDs lit');
});
test('timeline mode replays the heart, smile and check sequence on the led channels',async({page})=>{
 const out=noise(page);await open(page);
 await page.locator('#mode').selectOption('timeline');
 for(const [time,cells] of [[1,HEART],[3,SMILE],[5,CHECK]] as const){
  await page.locator('#timeline').evaluate((el,t)=>{(el as HTMLInputElement).value=String(t);el.dispatchEvent(new Event('input',{bubbles:true}))},time);
  await expect.poll(async()=>(await board(page)).lit).toEqual(key(cells));
 }
 await page.locator('#timeline').evaluate(el=>{(el as HTMLInputElement).value='0';el.dispatchEvent(new Event('input',{bubbles:true}))});
 await expect.poll(async()=>(await board(page)).lit).toEqual([]);
 expect(out).toEqual([]);
});
test('mount and unmount three times with the real model, once while holding a part, leave no errors or warnings',async({page})=>{
 const out=noise(page);await open(page);
 for(let round=0;round<3;round++){
  await page.evaluate(async()=>{
   const {mountPreview}=await import('/src/preview.ts');
   const host=document.createElement('div');host.id='extra';host.style.cssText='position:fixed;inset:0;z-index:9999;background:#fff';document.body.append(host);
   (window as unknown as {__extra:{host:HTMLElement;stop:()=>void}}).__extra={host,stop:mountPreview(host)};
   // The extra preview reads ?scene= from the page URL, so it loads the same real board.
   while(!host.querySelector('.part-label'))await new Promise(r=>setTimeout(r,20));
  });
  if(round===1){
   const p=await page.evaluate(async()=>{
    const label=(window as unknown as {__extra:{host:HTMLElement}}).__extra.host.querySelector<HTMLElement>('.part-label[data-part="btn_a"]')!;
    while(!label.style.transform)await new Promise(r=>setTimeout(r,20));const r=label.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};
   });
   await page.mouse.move(p.x,p.y);await page.mouse.down();
   await expect.poll(()=>page.evaluate(()=>(window as unknown as {__extra:{host:HTMLElement}}).__extra.host.querySelector('#value')!.textContent)).toContain('16 LEDs lit');
  }
  const children=await page.evaluate(()=>{const e=(window as unknown as {__extra:{host:HTMLElement;stop:() => void}}).__extra;e.stop();e.stop();const n=e.host.childElementCount;e.host.remove();return n});
  expect(children).toBe(0);
  if(round===1)await page.mouse.up();
 }
 await expect(readout(page)).toContainText('0 LEDs lit');
 expect(out).toEqual([]);
});

// The scene authors its own view: the camera is placed from camera.elevation and camera.azimuth, not from the default oblique direction.
const elevationOf=(c:{position:number[];target:number[]})=>{const d=c.position.map((v,i)=>v-c.target[i]);return Math.asin(d[1]/Math.hypot(d[0],d[1],d[2]))*180/Math.PI};
const azimuthOf=(c:{position:number[];target:number[]})=>{const d=c.position.map((v,i)=>v-c.target[i]);return Math.atan2(d[0],d[2])*180/Math.PI};
const authored=async(page:Page)=>(await (await page.request.get('/'+SCENE)).json()).camera as {elevation:number;azimuth:number};
test('the authored scene camera sets the opening view: authored elevation, camera on the +Z side of the board',async({page})=>{
 await open(page);const view=await authored(page);expect(view).toBeDefined();
 const camera=(await receipt(page)).camera;
 expect(elevationOf(camera)).toBeCloseTo(view.elevation,3);expect(azimuthOf(camera)).toBeCloseTo(view.azimuth,3);
 // Azimuth 0: the camera is on the +Z side (the edge connector side) of the board and level with it left to right.
 expect(camera.position[2]-camera.target[2]).toBeGreaterThan(0);
 expect(Math.abs(camera.target[0])).toBeLessThan(.002);
});
test('the micro:bit board fills most of the canvas width in the authored view (1152 x 820 canvas)',async({page})=>{
 await page.setViewportSize({width:1440,height:1000});await open(page);
 const left=await partPoint(page,'pin_0'),right=await partPoint(page,'pin_gnd'),canvas=(await page.locator('canvas').boundingBox())!;
 // Pin 0 and GND are the outermost pin rings, about three quarters of the 51.6 mm board apart; the board itself covers 70-80 % of the canvas width.
 expect(canvas.width).toBe(1152);expect((right.x-left.x)/canvas.width).toBeGreaterThan(.5);
 expect(left.x).toBeGreaterThan(canvas.x);expect(right.x).toBeLessThan(canvas.x+canvas.width);
});
test('Frame scene returns to the authored view after an orbit drag',async({page})=>{
 await open(page);const authoredCamera=(await receipt(page)).camera,box=(await page.locator('canvas').boundingBox())!,x=box.x+box.width*.9,y=box.y+box.height*.15;
 await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(x-160,y+90,{steps:8});await page.mouse.up();
 const dragged=(await receipt(page)).camera;expect(dragged.position.some((v:number,i:number)=>Math.abs(v-authoredCamera.position[i])>1e-5)).toBe(true);
 await page.locator('#frame').click();
 const back=(await receipt(page)).camera;back.position.forEach((v:number,i:number)=>expect(v).toBeCloseTo(authoredCamera.position[i],6));back.target.forEach((v:number,i:number)=>expect(v).toBeCloseTo(authoredCamera.target[i],6));
});
test('Frame scene with a zero-size viewport keeps the previous view, and works again once the viewport is back',async({page})=>{
 await open(page);const authoredCamera=(await receipt(page)).camera,box=(await page.locator('canvas').boundingBox())!,x=box.x+box.width*.9,y=box.y+box.height*.15;
 await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(x-160,y+90,{steps:8});await page.mouse.up();
 const dragged=(await receipt(page)).camera;
 // display:none gives the host clientWidth = clientHeight = 0 (aspect 0): the fit must be skipped, not sent to an enormous distance.
 await page.locator('#viewport').evaluate(el=>{(el as HTMLElement).style.display='none'});
 expect(await page.locator('#viewport').evaluate(el=>[el.clientWidth,el.clientHeight])).toEqual([0,0]);
 await page.locator('#frame').click();
 const hidden=(await receipt(page)).camera;hidden.position.forEach((v:number,i:number)=>expect(v).toBeCloseTo(dragged.position[i],6));hidden.target.forEach((v:number,i:number)=>expect(v).toBeCloseTo(dragged.target[i],6));
 await page.locator('#viewport').evaluate(el=>{(el as HTMLElement).style.display=''});
 await page.locator('#frame').click();
 const back=(await receipt(page)).camera;back.position.forEach((v:number,i:number)=>expect(v).toBeCloseTo(authoredCamera.position[i],6));
});
test('a scene without a camera keeps the default workbench view exactly',async({page})=>{
 await page.goto('/');await expect(page.getByText('Ready · 3 objects')).toBeVisible();
 const camera=(await receipt(page)).camera;
 // Recorded from the unchanged default framing (992 x 540 canvas at 1280 x 720).
 const expected={position:[5.290185685049913,4.476487489070782,6.413318582799788],target:[0.903747027890033,1.029999972730875,0.14697764399995855]};
 camera.position.forEach((v:number,i:number)=>expect(v).toBeCloseTo(expected.position[i],6));camera.target.forEach((v:number,i:number)=>expect(v).toBeCloseTo(expected.target[i],6));
 expect(camera.near).toBe(.05);
});
