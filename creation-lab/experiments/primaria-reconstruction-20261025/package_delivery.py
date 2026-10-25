"""Assemble a standalone local handoff without replacing prior evidence."""
from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
review=json.loads((root/'completion-review.json').read_text(encoding='utf-8-sig'))
tech=json.loads((root/'completion-run/reproduction.json').read_text(encoding='utf-8-sig'))
contact=json.loads((root/'completion-contacts-v2.json').read_text(encoding='utf-8-sig'))
if not (tech['technical']==contact['status']==review['visual']['status']==review['content']['status']=='PASS'):
    raise SystemExit('Final gates are not PASS')
manifest={'schemaVersion':1,'id':'GuateGeeks_Primaria_R4','technical':'PASS','visual':'PASS','content':'PASS','contactSamples':'PASS',
 'triangles':1738,'materials':8,'meshes':30,'heightConventionMeters':1,
 'sourceRun':'completion-run','historicalAttemptsPreserved':4,'additionalCompletionPass':1,
 'limitations':['Simplified hair and face planes','No paper-fibre microtexture','Small skin intersection at rear hair','Static model; rig/deformation NOT_RUN'],
 'files':{str(p.relative_to(root)).replace('\\','/'):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted((root/'delivery').glob('*')) if p.is_file()},
 'reviews':{p:sha(root/p) for p in ['completion-review.json','completion-contacts-v2.json','completion-run/reproduction.json']}}
(root/'final-delivery-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
protocol=json.loads((root/'completion-protocol.json').read_text())
protocol['status']='COMPLETE';protocol['finalManifest']='final-delivery-manifest.json';protocol['technical']='PASS';protocol['visual']='PASS';protocol['content']='PASS'
(root/'completion-protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
files={}
for folder in ['delivery','inspector','completion-recipe','presentation-v2','support']:
    for p in (root/folder).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':
            files[p]=p.relative_to(root).as_posix()
for name in ['DELIVERY.md','WORKFLOW.md','PROMPTS.md','reference-review.md','landmarks.json','reproduce.py','verify_contacts.py','render-presentation.py','completion-review.json','completion-contacts-v2.json','completion-protocol.json','final-delivery-manifest.json','runtime-evidence.json']:
    files[root/name]=name
files[root/'DELIVERY.md']='README.md'
for p in (root/'completion-run/renders').glob('*.png'):files[p]='qa-renders/'+p.name
for name in ['reproduction.json','build-checks.json','source-quality.json','reopen-result.json','reimport-result.json']:
    files[root/'completion-run'/name]='qa/'+name
ref=root/'references/GuateGeeks_Primaria_Piezas_R2/GuateGeeks_Primaria_Piezas_R2/imagenes/00-personaje-completo.png'
files[ref]=ref.relative_to(root).as_posix()
for name in ['review-blockout-v1.json','review-blockout-v2.json','review-blockout-v3.json','review-detail-v1.json','supplemental-contact-failure.json','delivery-manifest.json','completion-contacts.json']:
    p=root/name
    if p.exists():files[p]='history/'+name
files[root/'README.md']='history/WORKSPACE-HISTORY.md'
archive=root/'GuateGeeks_Primaria_R4.zip'
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p,arc in sorted(files.items(),key=lambda pair:pair[1]):z.write(p,arc)
with zipfile.ZipFile(archive) as z:
    error=z.testzip()
    if error:raise RuntimeError(error)
receipt={'archive':archive.name,'bytes':archive.stat().st_size,'files':len(files),'sha256':sha(archive),'integrity':'PASS'}
(root/'package-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
