import {test,expect} from '@playwright/test';
test('controls, ownership, scene swap, failed load and lifecycle',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await expect(page.getByText('Ready · 3 objects')).toBeVisible();
 await page.getByRole('button',{name:'Button / 01'}).click();
 await page.screenshot({path:'test-results/desktop.png',fullPage:true});
 const hold=page.getByRole('button',{name:'Hold button'});await hold.focus();await page.keyboard.down('Space');
 await expect(page.getByTestId('channel-value')).toHaveText('Pressed');await page.keyboard.up('Space');
 await expect(page.getByTestId('channel-value')).toHaveText('Released');
 await page.getByRole('button',{name:'Servo / 02'}).click();
 await expect(page.getByLabel('Servo angle')).toBeDisabled();await expect(page.getByText('Button controls this channel.')).toBeVisible();
 await page.getByLabel('Mode').selectOption('timeline');await expect(page.getByLabel('Servo angle')).toBeDisabled();
 await page.getByLabel('Timeline position').fill('2');await expect(page.getByTestId('channel-value')).toHaveText('90°');
 await page.getByRole('button',{name:'Reset scene'}).click();await expect(page.getByLabel('Timeline position')).toHaveValue('0');
 await page.getByRole('button',{name:'Load scene'}).click();await page.getByLabel('Scene URL').fill('single.json');await page.getByRole('button',{name:'Open scene'}).click();
 await expect(page.getByText('Ready · 1 object')).toBeVisible();await expect(page.getByRole('button',{name:'Solo / 01'})).toBeVisible();
 await page.getByRole('button',{name:'Load scene'}).click();await page.getByLabel('Scene URL').fill('missing.json');await page.getByRole('button',{name:'Open scene'}).click();
 await expect(page.getByRole('alert')).toContainText('Scene request failed');await expect(page.getByText('Ready · 1 object')).toBeVisible();
 await page.screenshot({path:'test-results/workspace.png',fullPage:true});expect(errors).toEqual([]);
});
test('query scene and reduced motion stay paused until explicit seek',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'});await page.goto('/?scene=single.json');
 await expect(page.getByText('Ready · 1 object')).toBeVisible();await page.getByLabel('Mode').selectOption('timeline');
 await page.getByRole('button',{name:'Play timeline'}).click();await page.waitForTimeout(150);await expect(page.getByLabel('Timeline position')).toHaveValue('0');
 await page.getByLabel('Timeline position').fill('2');await expect(page.getByLabel('Timeline position')).toHaveValue('2');
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:'test-results/mobile.png',fullPage:true});
});
test('mount, unmount and remount cleanly release the canvas and callbacks',async({page})=>{
 await page.goto('/');await expect(page.getByText('Ready · 3 objects')).toBeVisible();
 const result=await page.evaluate(async()=>{
  const {mountPreview}=await import('/src/preview.ts');
  const host=document.createElement('div');host.style.cssText='position:fixed;inset:0';document.body.append(host);
  const stop=mountPreview(host);await new Promise(r=>setTimeout(r,100));const first=host.querySelectorAll('canvas').length;
  stop();stop();const after=host.childElementCount;const stopAgain=mountPreview(host);await new Promise(r=>setTimeout(r,100));const second=host.querySelectorAll('canvas').length;
  stopAgain();host.remove();return {first,after,second};
 });expect(result).toEqual({first:1,after:0,second:1});
});
test('original skinned character exports and loads as a self-contained GLB with clips',async({page})=>{
 await page.goto('/');await expect(page.getByText('Ready · 3 objects')).toBeVisible();
 const result=await page.evaluate(async()=>{
  const {createBuiltin,loadGLB}=await import('/src/assets.ts');
  const {GLTFExporter}=await import('/node_modules/three/examples/jsm/exporters/GLTFExporter.js');
  const original=createBuiltin('character');original.seek(0);
  const data=await new GLTFExporter().parseAsync(original.root,{binary:true,animations:original.clips});
  const url=URL.createObjectURL(new Blob([data as ArrayBuffer],{type:'model/gltf-binary'}));
  const asset=await loadGLB(url,new AbortController().signal);let skinned=0,bones=0;asset.root.traverse((o:any)=>{if(o.isSkinnedMesh)skinned++;if(o.isBone)bones++});
  const arm=asset.root.getObjectByName('LeftArm')!;asset.seek(1);const q=arm.quaternion.clone();asset.seek(2);asset.seek(1);
  const result={skinned,bones,clips:asset.clips.map((c:any)=>c.name),backwardsError:q.angleTo(arm.quaternion),rotation:q.z};
  asset.dispose();original.dispose();URL.revokeObjectURL(url);return result;
 });
 expect(result.skinned).toBe(1);expect(result.bones).toBe(7);expect(result.clips).toEqual(['Wave','Idle']);expect(result.backwardsError).toBeCloseTo(0);expect(Math.abs(result.rotation)).toBeGreaterThan(.1);
});
test('a slower scene response cannot replace a newer scene choice',async({page})=>{
 await page.route('**/slow.json',async route=>{await new Promise(r=>setTimeout(r,1500));await route.fulfill({json:{schemaVersion:1,kind:'scene',id:'slow',title:'Stale scene',duration:4,mode:'interactive',instances:[{id:'Stale',asset:'button',position:[0,0,0],rotation:[0,0,0],scale:[1,1,1]}],tracks:[]}})});
 await page.goto('/');await expect(page.getByText('Ready · 3 objects')).toBeVisible();
 for(const url of ['slow.json','single.json']){
  await page.getByRole('button',{name:'Load scene'}).click();await page.getByLabel('Scene URL').fill(url);await page.getByRole('button',{name:'Open scene'}).click();
 }
 await expect(page.getByText('Ready · 1 object')).toBeVisible();await page.waitForTimeout(1650);await expect(page.getByRole('heading',{name:'Single object'})).toBeVisible();
});
test('inspection overlays, speed, loop, motion override and capture are usable',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'});await page.goto('/');await expect(page.getByText('Ready · 3 objects')).toBeVisible();
 await page.getByRole('button',{name:'Character / 03'}).click();await expect(page.getByLabel('Animation clip')).toHaveValue('0');
 await page.getByText('View options',{exact:true}).click();
 await page.getByLabel('Bounds').check();await page.getByLabel('Rig').check();await page.getByLabel('Anchors').uncheck();
 await page.getByLabel('Playback speed').selectOption('2');await page.getByLabel('Loop').uncheck();
 await page.getByLabel('Allow motion').check();await page.getByRole('button',{name:'Play timeline'}).click();
 await expect.poll(async()=>Number(await page.getByLabel('Timeline position').inputValue())).toBeGreaterThan(0);
 await expect(page.getByTestId('diagnostics')).toContainText('draw calls');
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Capture PNG'}).click();expect((await download).suggestedFilename()).toMatch(/^3d-lab-.*\.png$/);
});


test('GLB scene resolves its asset relative to the scene JSON URL',async({page})=>{
 await page.goto('/?scene=character.scene.json');
 await expect(page.getByRole('heading',{name:'Original character · GLB'})).toBeVisible();
 await expect(page.getByLabel('Animation clip').locator('option')).toHaveText(['Wave','Idle']);
 await page.getByLabel('Timeline position').fill('1');await page.getByLabel('Animation clip').selectOption('1');await page.getByLabel('Mode').selectOption('interactive');await expect(page.getByLabel('Animation clip')).toHaveValue('1');
 await page.getByText('View options',{exact:true}).click();await page.getByLabel('Rig').check();await page.getByLabel('Bounds').check();
 await page.screenshot({path:'test-results/rig.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
