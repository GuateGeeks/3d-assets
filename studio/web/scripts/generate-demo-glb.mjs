import {chromium} from '@playwright/test';
import {writeFile} from 'node:fs/promises';
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-angle=swiftshader']});
try{
 const page=await browser.newPage();
 await page.goto(process.env.PREVIEW_URL||'http://127.0.0.1:5287/');
 const bytes=await page.evaluate(async()=>{
  const {createBuiltin}=await import('/src/assets.ts');
  const {GLTFExporter}=await import('/node_modules/three/examples/jsm/exporters/GLTFExporter.js');
  const asset=createBuiltin('character');asset.seek(0);
  const data=await new GLTFExporter().parseAsync(asset.root,{binary:true,animations:asset.clips});
  asset.dispose();return Array.from(new Uint8Array(data));
 });
 await writeFile(new URL('../public/original-character.glb',import.meta.url),new Uint8Array(bytes));
 await writeFile(new URL('../../examples/original-character.glb',import.meta.url),new Uint8Array(bytes));
 console.log('Original skinned character GLB:',bytes.length,'bytes');
}finally{await browser.close()}
