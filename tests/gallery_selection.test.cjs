const {test} = require('node:test');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const path = require('node:path');
const moduleUrl = pathToFileURL(path.join(__dirname, '../gallery/selection.mjs')).href;
const models = [{id:'poly-character'}, {id:'sketchfab-panel'}, {id:'sketchfab-turbine'}];
for(const [name,options,want] of [
 ['display order', {preferredId:'poly-character',eligibleIds:['sketchfab-turbine','sketchfab-panel']}, 'sketchfab-turbine'],
 ['source filter', {preferredId:'poly-character',eligibleIds:['sketchfab-panel','sketchfab-turbine']}, 'sketchfab-panel'],
 ['explicit model', {requestedId:'sketchfab-turbine',preferredId:'poly-character',eligibleIds:['sketchfab-panel']}, 'sketchfab-turbine'],
 ['invalid model', {requestedId:'missing',preferredId:'poly-character',eligibleIds:['sketchfab-panel']}, 'sketchfab-panel'],
 ['empty filter', {preferredId:'poly-character',eligibleIds:[]}, null],
 ['unfiltered preferred', {preferredId:'poly-character',eligibleIds:['sketchfab-panel','poly-character']}, 'poly-character']
]) test(name, async () => {
 const {chooseInitialModel} = await import(moduleUrl);
 assert.equal(chooseInitialModel(models,options)?.id ?? null,want);
});

test('compatible display is bound to the unchanged original and passing QA',async()=>{
 const {chooseDisplayVariant}=await import(moduleUrl);
 const model={id:'model-a',file:'models/model-a/model.glb',sha256:'native-hash'};
 const good={id:'model-a',sourceFile:model.file,sourceSha256:model.sha256,file:'gallery/compat/models/model-a.glb',qa:{technical:'PASS',visual:'PASS'}};
 assert.equal(chooseDisplayVariant(model,[good]),good);
 for(const change of [{sourceSha256:'other'},{sourceFile:'other.glb'},{file:'https://outside.test/model.glb'},{file:'gallery/compat/models/../model.glb'},{qa:{technical:'PASS',visual:'NOT_RUN'}}])assert.equal(chooseDisplayVariant(model,[{...good,...change}]),null);
 assert.equal(chooseDisplayVariant(model,[]),null);
});
