/* Independent Khronos format validation; leaves immutable Blender runs untouched. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '../../..');
const validator = require(path.join(root, 'lab/.local/tools/gltf-validator/package'));
const output = path.join(root, 'creation-lab/.local/benchmarks/animal-cell-20261022');
async function main() {
  const entries = [];
  for (const id of 'ABCDEF') {
    const folder = path.join(output, id);
    if (!fs.existsSync(folder)) continue;
    for (const runId of fs.readdirSync(folder).sort()) {
      const run = path.join(folder, runId), asset = path.join(run, 'asset.glb');
      if (!fs.existsSync(asset) || !fs.existsSync(path.join(run, 'COMPLETE'))) continue;
      const bytes = fs.readFileSync(asset);
      const report = await validator.validateBytes(new Uint8Array(bytes), {uri:'asset.glb', maxIssues:1000});
      entries.push({id, runId, sha256:crypto.createHash('sha256').update(bytes).digest('hex'), validator:validator.version(),
        status:report.issues.numErrors === 0 ? 'PASS' : 'FAIL', report});
      console.log(`${id}/${runId}: ${report.issues.numErrors} errors, ${report.issues.numWarnings} warnings`);
    }
  }
  fs.writeFileSync(path.join(__dirname, 'format-validation.json'), JSON.stringify({schemaVersion:1,entries},null,2)+'\n');
  if (entries.some(x=>x.status==='FAIL')) process.exitCode=1;
}
main().catch(error=>{console.error(error);process.exitCode=1;});
