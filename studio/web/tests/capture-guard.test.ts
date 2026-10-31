import {describe,it,expect} from 'vitest';
// There are no Node typings in this project, so the Node built-ins are loaded through an untyped dynamic import (as in microbit-asset.test.ts).
const builtin=async(name:string)=>(await import(/* @vite-ignore */ name)) as any;
const {spawnSync}=await builtin('node:child_process'),fs=await builtin('node:fs'),{tmpdir}=await builtin('node:os'),{join}=await builtin('node:path'),{fileURLToPath}=await builtin('node:url');
const {mkdtempSync,mkdirSync,writeFileSync,readdirSync,readFileSync,existsSync,rmSync}=fs;
// The capture script must never write into an existing evidence folder. Both guards run before the browser is launched, so these runs are fast and need no server.
const script=fileURLToPath(new URL('../scripts/capture-microbit-evidence.mjs',import.meta.url));
const run=(...args:string[])=>spawnSync((globalThis as any).process.execPath,[script,...args],{encoding:'utf8',timeout:20000,env:{...(globalThis as any).process.env,PREVIEW_URL:'http://127.0.0.1:1/'}});
describe('capture-microbit-evidence output guard',()=>{
 it('requires an output directory argument',()=>{
  const r=run();expect(r.status).not.toBe(0);expect(r.stderr).toMatch(/usage:/);
 });
 it('refuses a non-empty directory and leaves it untouched',()=>{
  const dir=mkdtempSync(join(tmpdir(),'capture-guard-'));try{
   writeFileSync(join(dir,'capture-summary.json'),'reviewed\n');mkdirSync(join(dir,'closeup-a-held'));
   const r=run(dir);expect(r.status).not.toBe(0);expect(r.stderr).toMatch(/already exists and is not empty/);
   expect(readdirSync(dir).sort()).toEqual(['capture-summary.json','closeup-a-held']);expect(readFileSync(join(dir,'capture-summary.json'),'utf8')).toBe('reviewed\n');expect(readdirSync(join(dir,'closeup-a-held'))).toEqual([]);
  }finally{rmSync(dir,{recursive:true,force:true})}
 });
 it('accepts a missing or empty directory past the guard (fails later, at the unreachable preview, without writing the summary)',()=>{
  const dir=mkdtempSync(join(tmpdir(),'capture-guard-'));try{
   const r=run(dir);expect(r.stderr).not.toMatch(/already exists and is not empty|usage:/);expect(existsSync(join(dir,'capture-summary.json'))).toBe(false);
  }finally{rmSync(dir,{recursive:true,force:true})}
 });
});
