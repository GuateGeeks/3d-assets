import {describe,it,expect} from 'vitest';
import {stageForBounds,type Stage} from '../src/stage';
const DEFAULT:Stage={near:.05,minDistance:2,maxDistance:22,shadowExtent:8,fogNear:12,fogFar:35,gridSize:30,frameFloor:1.4};
describe('scale-aware stage',()=>{
 it('keeps the workbench constants exactly for scenes of 2 m or larger',()=>{
  expect(stageForBounds(6)).toEqual(DEFAULT);expect(stageForBounds(2)).toEqual(DEFAULT);expect(stageForBounds(40)).toEqual(DEFAULT);
 });
 it('scales every value proportionally by longest/2 for small scenes',()=>{
  const s=stageForBounds(.0525),f=.0525/2;
  for(const k of Object.keys(DEFAULT) as (keyof Stage)[])expect(s[k]).toBeCloseTo(DEFAULT[k]*f,12);
  for(const k of Object.keys(DEFAULT) as (keyof Stage)[])expect(Math.abs(s[k]/(DEFAULT[k]*f)-1)).toBeLessThan(1e-9);
 });
 it('falls back to the default for zero, negative and non-finite sizes',()=>{
  for(const v of [0,-1,NaN,Infinity,-Infinity])expect(stageForBounds(v)).toEqual(DEFAULT);
 });
});
