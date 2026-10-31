// Stage constants tuned for scenes about 2 m wide or larger. Smaller scenes scale them down
// proportionally so centimetre-size objects are not clipped, unzoomable or shadowless.
export interface Stage{near:number;minDistance:number;maxDistance:number;shadowExtent:number;fogNear:number;fogFar:number;gridSize:number;frameFloor:number}
const BASE:Stage={near:.05,minDistance:2,maxDistance:22,shadowExtent:8,fogNear:12,fogFar:35,gridSize:30,frameFloor:1.4};
export const STAGE_REFERENCE_SIZE=2;
/** Scale factor applied to the base stage for a scene whose longest world-bounds side is `longest` metres. */
export function stageScale(longest:number):number{return Number.isFinite(longest)&&longest>0?Math.min(1,longest/STAGE_REFERENCE_SIZE):1}
export function stageForBounds(longest:number):Stage{
 const f=stageScale(longest);
 return {near:BASE.near*f,minDistance:BASE.minDistance*f,maxDistance:BASE.maxDistance*f,shadowExtent:BASE.shadowExtent*f,fogNear:BASE.fogNear*f,fogFar:BASE.fogFar*f,gridSize:BASE.gridSize*f,frameFloor:BASE.frameFloor*f};
}
