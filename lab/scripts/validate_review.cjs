// Optional independent Khronos glTF validation. Pass the installed gltf-validator package directory.
const fs = require('node:fs'), path = require('node:path');
const root = path.resolve(__dirname, '../..');
const validator = require(path.resolve(process.argv[2]));
const review = path.join(root, 'lab/.local/review');
(async () => {
 const manifest = JSON.parse(fs.readFileSync(path.join(review, 'manifest.json'), 'utf8'));
 const results = [];
 for (const [token, entry] of Object.entries(manifest.files)) {
  const file = path.resolve(review, 'assets', entry.file);
  if (!file.startsWith(path.resolve(review, 'assets') + path.sep)) throw new Error('Unsafe review asset');
  const report = await validator.validateBytes(new Uint8Array(fs.readFileSync(file)), {uri:path.basename(file),externalResourceFunction:uri=>Promise.reject(new Error('External resource forbidden: '+uri))});
  results.push({token,file:entry.file,sha256:entry.sha256,errors:report.issues.numErrors,warnings:report.issues.numWarnings,messages:report.issues.messages.filter(m=>m.severity<=1)});
 }
 const errors = results.reduce((sum,r)=>sum+r.errors,0), warnings = results.reduce((sum,r)=>sum+r.warnings,0);
 const report = {schemaVersion:1,validator:validator.version(),recordedAt:new Date().toISOString(),status:errors?'failed':'passed',files:results.length,errors,warnings,results};
 fs.writeFileSync(path.join(root,'lab/reports/corpus-gltf-validation.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,files:report.files,errors,warnings}));process.exitCode=errors?1:0;
})().catch(error=>{console.error(error);process.exitCode=1;});
