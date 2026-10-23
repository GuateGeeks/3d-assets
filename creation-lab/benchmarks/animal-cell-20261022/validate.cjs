/* Independent Khronos validation; historical reports and Blender runs stay intact. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '../../..');
const defaultRuns = path.join(root, 'creation-lab/.local/benchmarks/animal-cell-20261022');
function options(argv) {
  const result = {runs:defaultRuns, output:null, validatorModule:null};
  for (let i=0; i<argv.length; i++) {
    if (argv[i] === '--help') {
      console.log('node validate.cjs [--runs PATH] [--output NEW_JSON] [--validator-module PATH]\nInstall the pinned optional validator with npm ci --ignore-scripts in this folder.');
      return null;
    }
    const key = {'--runs':'runs','--output':'output','--validator-module':'validatorModule'}[argv[i]];
    if (!key || !argv[i+1] || argv[i+1].startsWith('--')) throw Error(`Invalid option: ${argv[i]}`);
    result[key] = path.resolve(argv[++i]);
  }
  result.output ||= path.join(defaultRuns, 'reports', `${Date.now()}-${crypto.randomUUID()}`, 'format-validation.json');
  return result;
}
async function main() {
  const opts = options(process.argv.slice(2));
  if (!opts) return;
  if (fs.existsSync(opts.output)) throw Error('Output exists; choose a new --output path.');
  let validator;
  try { validator = require(opts.validatorModule || 'gltf-validator'); }
  catch { throw Error('Khronos validator unavailable. Run npm ci --ignore-scripts in the benchmark folder, or provide --validator-module /absolute/path/to/package.'); }
  const entries = [];
  for (const id of 'ABCDEF') {
    const folder = path.join(opts.runs, id);
    if (!fs.existsSync(folder)) continue;
    for (const runId of fs.readdirSync(folder).sort()) {
      if (!/^[A-Za-z0-9_-]+$/.test(runId)) continue;
      const run = path.join(folder, runId), asset = path.join(run, 'asset.glb');
      if (!fs.existsSync(asset) || !fs.existsSync(path.join(run, 'COMPLETE'))) continue;
      const manifest = fs.readFileSync(path.join(run, 'manifest.json'));
      if (fs.readFileSync(path.join(run, 'COMPLETE'),'utf8').trim() !== crypto.createHash('sha256').update(manifest).digest('hex')) throw Error(`Changed completion manifest: ${id}/${runId}`);
      const bytes = fs.readFileSync(asset);
      const sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
      if (JSON.parse(manifest).artifacts['asset.glb'] !== sha256) throw Error(`Changed GLB: ${id}/${runId}`);
      const report = await validator.validateBytes(new Uint8Array(bytes), {uri:'asset.glb', maxIssues:1000});
      entries.push({id, runId, sha256, validator:validator.version(),
        status:report.issues.numErrors === 0 ? 'PASS' : 'FAIL', report});
      console.log(`${id}/${runId}: ${report.issues.numErrors} errors, ${report.issues.numWarnings} warnings`);
    }
  }
  if (!entries.length) throw Error('No completed GLBs found. Restore fixtures or generate a run before validation.');
  fs.mkdirSync(path.dirname(opts.output), {recursive:true});
  fs.writeFileSync(opts.output, JSON.stringify({schemaVersion:1,entries},null,2)+'\n', {flag:'wx'});
  console.log(`Report: ${opts.output}`);
  if (entries.some(x=>x.status==='FAIL')) process.exitCode=1;
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
