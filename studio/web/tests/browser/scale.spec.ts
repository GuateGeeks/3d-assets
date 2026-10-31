import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const tiny={schemaVersion:1,kind:'scene',id:'tiny',title:'Tiny button',duration:4,mode:'interactive',instances:[{id:'Tiny',asset:'button',position:[0,0,0],rotation:[0,0,0],scale:[.02,.02,.02]}],tracks:[]};
async function receipt(page:import('@playwright/test').Page){
 const downloads:import('@playwright/test').Download[]=[],collect=(d:import('@playwright/test').Download)=>downloads.push(d);page.on('download',collect);
 await page.getByRole('button',{name:'Capture PNG'}).click();await expect.poll(()=>downloads.length).toBe(2);page.off('download',collect);
 return JSON.parse(await readFile((await downloads.find(d=>d.suggestedFilename().endsWith('.json'))!.path())!,'utf8'));
}
const distance=(c:any)=>Math.hypot(...c.position.map((v:number,i:number)=>v-c.target[i]));
test('a centimetre-scale object is framed unclipped and zooms closer than the workbench minimum',async({page})=>{
 await page.route('**/tiny.json',route=>route.fulfill({json:tiny}));
 await page.goto('/?scene=tiny.json');await expect(page.getByRole('heading',{name:'Tiny button'})).toBeVisible();
 await page.getByText('View options',{exact:true}).click();
 await page.getByRole('button',{name:'Frame scene'}).click();
 const {camera}=await receipt(page),d=distance(camera);
 expect(camera.near).toBeLessThan(.01);expect(camera.near).toBeLessThan(d);expect(d).toBeLessThan(2);
 await page.locator('canvas').hover();for(let i=0;i<8;i++)await page.mouse.wheel(0,-300);await page.waitForTimeout(300);
 const zoomed=distance((await receipt(page)).camera);
 expect(zoomed).toBeLessThan(d);expect(zoomed).toBeGreaterThan(camera.near);
});
test('the default workbench keeps its camera constants',async({page})=>{
 await page.goto('/');await expect(page.getByText('Ready · 3 objects')).toBeVisible();
 await page.getByText('View options',{exact:true}).click();
 const {camera}=await receipt(page),d=distance(camera);
 expect(camera.near).toBe(.05);expect(d).toBeGreaterThanOrEqual(2);expect(d).toBeLessThanOrEqual(22);
 await page.locator('canvas').hover();for(let i=0;i<20;i++)await page.mouse.wheel(0,-400);await page.waitForTimeout(300);
 expect(distance((await receipt(page)).camera)).toBeCloseTo(2,5);
 await page.locator('canvas').hover();for(let i=0;i<40;i++)await page.mouse.wheel(0,600);await page.waitForTimeout(300);
 expect(distance((await receipt(page)).camera)).toBeCloseTo(22,5);
});
