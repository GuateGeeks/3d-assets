import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
test('capture downloads paired image and metadata of the actual scene, camera and renderer',async({page})=>{
 await page.goto('/');await expect(page.getByText('Ready · 3 objects')).toBeVisible();
 await page.getByLabel('Mode').selectOption('timeline');await page.getByLabel('Timeline position').fill('1.25');
 await page.getByRole('button',{name:'Character / 03'}).click();await page.getByLabel('Animation clip').selectOption('1');
 await page.getByText('View options',{exact:true}).click();await page.getByLabel('Bounds',{exact:true}).check();
 const downloads:import('@playwright/test').Download[]=[];page.on('download',d=>downloads.push(d));
 await page.getByRole('button',{name:'Capture PNG'}).click();await expect.poll(()=>downloads.length).toBe(2);
 const png=downloads.find(d=>d.suggestedFilename().endsWith('.png'))!,receipt=downloads.find(d=>d.suggestedFilename().endsWith('.json'))!;
 const pixels=await readFile((await png.path())!),metadata=JSON.parse(await readFile((await receipt.path())!,'utf8'));
 expect(metadata.image.name).toBe(png.suggestedFilename());expect(metadata.image.sha256).toBe(createHash('sha256').update(pixels).digest('hex'));
 expect(metadata.scene.spec.id).toBe('interactive-workbench');expect(metadata.scene.time).toBe(1.25);expect(metadata.scene.mode).toBe('timeline');
 expect(metadata.scene.instances.find((i:any)=>i.id==='Character').clipIndex).toBe(1);expect(metadata.scene.instances.find((i:any)=>i.id==='Servo').channels.angle).toBeCloseTo(56.25);
 const canvas=page.locator('canvas'),size=await canvas.boundingBox();expect(metadata.viewport.cssWidth).toBe(size!.width);expect(metadata.viewport.cssHeight).toBe(size!.height);
 expect(metadata.viewport.pixelWidth).toBeGreaterThan(0);expect(metadata.viewport.devicePixelRatio).toBeGreaterThan(0);expect(metadata.viewport.rendererPixelRatio).toBeGreaterThan(0);
 expect(metadata.camera.position).toHaveLength(3);expect(metadata.camera.target).toHaveLength(3);expect(metadata.camera.projectionMatrix).toHaveLength(16);
 expect(metadata.renderer.webglVersion).toContain('WebGL');expect(metadata.renderer.renderer).toBeTruthy();expect(metadata.runtime.three).toBe('180');expect(metadata.runtime.userAgent).toBeTruthy();expect(metadata.overlays.bounds).toBe(true);
});
test('original workbench button drives servo horn and disables its bound live control',async({page})=>{
 await page.goto('/');await expect(page.getByText('Ready · 3 objects')).toBeVisible();
 await page.getByRole('button',{name:'Hold button'}).focus();const initial=await page.locator('canvas').screenshot();await page.keyboard.down('Space');
 const pressed=await page.locator('canvas').screenshot();expect(pressed.equals(initial)).toBe(false);await page.keyboard.up('Space');
 await page.getByRole('button',{name:'Servo / 02'}).click();await expect(page.getByLabel('Servo angle')).toBeDisabled();
 await expect(page.getByText('Button controls this channel.')).toBeVisible();
});
