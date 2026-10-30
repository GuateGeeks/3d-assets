import {test,expect} from '@playwright/test';
test('interactive reset restores servo channel and rendered pose',async({page})=>{
 await page.route('**/unbound.json',async route=>{const response=await route.fetch({url:new URL('/demo.scene.json',route.request().url()).href});const spec=await response.json();delete spec.bindings;await route.fulfill({json:spec})});
 await page.goto('/?scene=unbound.json');await expect(page.getByText('Ready · 3 objects')).toBeVisible();
 await page.getByRole('button',{name:'Servo / 02'}).click();
 const canvas=page.locator('canvas');const initial=await canvas.screenshot();
 await page.getByLabel('Servo angle').fill('90');await expect(page.getByTestId('channel-value')).toHaveText('90°');
 const turned=await canvas.screenshot();expect(turned.equals(initial)).toBe(false);
 await page.getByRole('button',{name:'Reset scene'}).click();
 await expect(page.getByLabel('Mode')).toHaveValue('interactive');
 await expect(page.getByLabel('Servo angle')).toHaveValue('0');await expect(page.getByTestId('channel-value')).toHaveText('0°');
 await expect(page.getByLabel('Timeline position')).toHaveValue('0');await expect(page.getByRole('button',{name:'Play timeline'})).toBeVisible();
 expect((await canvas.screenshot()).equals(initial)).toBe(true);
 await expect(page.getByLabel('Animation clip')).toBeDisabled();await expect(page.getByLabel('Animation clip').locator('option')).toHaveText(['None']);
});
test('unmount cancels an in-flight JSON scene request',async({page})=>{
 await page.goto('/');await expect(page.getByText('Ready · 3 objects')).toBeVisible();
 const result=await page.evaluate(async()=>{
  const {mountPreview}=await import('/src/preview.ts');
  const originalFetch=window.fetch;let requested=false,aborted=false;
  window.fetch=((input:RequestInfo|URL,init?:RequestInit)=>{
   if(String(input).includes('pending.json')){
    requested=true;return new Promise((_resolve,reject)=>{
     init?.signal?.addEventListener('abort',()=>{aborted=true;reject(new DOMException('Cancelled','AbortError'))},{once:true});
    });
   }return originalFetch(input,init);
  }) as typeof fetch;
  const host=document.createElement('div');document.body.append(host);const stop=mountPreview(host);
  host.querySelector<HTMLButtonElement>('#load')!.click();host.querySelector<HTMLInputElement>('#scene-url')!.value='pending.json';
  host.querySelector('form')!.dispatchEvent(new Event('submit',{cancelable:true}));stop();await new Promise(resolve=>setTimeout(resolve,0));
  const children=host.childElementCount;window.fetch=originalFetch;host.remove();return {requested,aborted,children};
 });expect(result).toEqual({requested:true,aborted:true,children:0});
});
