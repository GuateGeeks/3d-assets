"""Check the publication inventory, assets, licenses, paths and credentials."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'_site'
from reindex import records
records()  # Includes integrity of source files and QA gates for external resources.
models=json.loads((ROOT/'index.json').read_text(encoding='utf-8'))['models']
if len({m['id'] for m in models})!=len(models): raise SystemExit('Duplicate IDs')
for m in models:
    p=(ROOT/m['file']).resolve()
    if not p.is_relative_to((ROOT/'models').resolve()): raise SystemExit('Unsafe model path')
    data=p.read_bytes()
    if hashlib.sha256(data).hexdigest()!=m['sha256'] or len(data)!=m['bytes']: raise SystemExit('Model integrity mismatch: '+m['id'])
    if len(data)>=100*1024**2: raise SystemExit('Model exceeds GitHub regular-file limit')
    if not m.get('licenseRaw') or not m.get('attribution') or not m['license'].get('url'): raise SystemExit('Missing license or credit')
    for suffix in ['metadata.json','source.json','LICENSE.txt']:
        if not (p.parent/suffix).is_file(): raise SystemExit('Missing model evidence: '+suffix)
    thumb=ROOT/'gallery/thumbnails'/(m['id']+'.webp')
    if thumb.read_bytes()[:4]!=b'RIFF': raise SystemExit('Missing thumbnail')
    if SITE.exists() and (SITE/m['file']).read_bytes()!=data: raise SystemExit('Build model mismatch')
kit_path=ROOT/'kits/index.json'
if kit_path.exists():
    import zipfile
    model_ids={m['id'] for m in models}
    for kit in json.loads(kit_path.read_text(encoding='utf-8'))['kits']:
        archive=(ROOT/kit['file']).resolve()
        if not archive.is_relative_to((ROOT/'kits').resolve()) or hashlib.sha256(archive.read_bytes()).hexdigest()!=kit['sha256']: raise SystemExit('Kit integrity mismatch')
        if not (ROOT/kit['licenseFile']).is_file() or not kit['attribution']: raise SystemExit('Missing kit license/credit')
        if hashlib.sha256((ROOT/kit['pageSnapshotFile']).read_bytes()).hexdigest()!=kit['pageSnapshotSha256']: raise SystemExit('Kit source page changed')
        with zipfile.ZipFile(archive) as z:
            for member in kit['members']:
                raw=z.read(member['file'])
                if len(raw)!=member['bytes'] or hashlib.sha256(raw).hexdigest()!=member['sha256']: raise SystemExit('Kit member integrity mismatch')
        if any(a['modelId'] not in model_ids for a in kit.get('assets',[])): raise SystemExit('Kit model link mismatch')
        if SITE.exists() and (SITE/kit['file']).read_bytes()!=archive.read_bytes(): raise SystemExit('Built kit mismatch')
    if (ROOT/'kits/groups.json').exists():
        groups=json.loads((ROOT/'kits/groups.json').read_text(encoding='utf-8'))
        if any(not set(g['modelIds'])<=model_ids for g in groups['groups']): raise SystemExit('Unknown variant ID')
external=ROOT/'sources/external'
if external.exists() and SITE.exists():
    for p in external.rglob('*'):
        if p.is_file() and (SITE/p.relative_to(ROOT)).read_bytes()!=p.read_bytes(): raise SystemExit('External evidence build mismatch')
manifest=json.loads((ROOT/'gallery/dependencies.json').read_text(encoding='utf-8'))
for m in manifest['thumbnails']:
    if m.get('error') or hashlib.sha256((ROOT/m['file']).read_bytes()).hexdigest()!=m['sha256']: raise SystemExit('Thumbnail integrity mismatch')
for p in [ROOT/'gallery.html',*(ROOT/'gallery').glob('*.css')]:
    text=p.read_text(encoding='utf-8-sig')
    refs=re.findall(r'(?:src|href)="([^"]+)"',text) if p.suffix=='.html' else re.findall(r'url\([\"\x27]?([^\)\"\x27]+)',text)
    for ref in refs:
        if ref.startswith(('#','http:','https:','data:')): continue
        if not (p.parent/ref).is_file(): raise SystemExit('Missing local resource: '+ref)
for item in json.loads((ROOT/'sources/documents.json').read_text(encoding='utf-8'))['sources']:
    if hashlib.sha256((ROOT/'sources'/item['file']).read_bytes()).hexdigest()!=item['sha256']: raise SystemExit('Source evidence integrity mismatch: '+item['file'])
secret=re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})')
for p in ROOT.rglob('*'):
    if '.git' in p.parts or '_site' in p.parts or not p.is_file() or p.suffix not in {'.md','.txt','.json','.js','.html','.py','.yml','.yaml','.css'}: continue
    text=p.read_text(encoding='utf-8-sig')
    if secret.search(text) or ('chatgpt'+'-conversation:') in text: raise SystemExit('Private material found: '+str(p.relative_to(ROOT)))
if SITE.exists():
    for path in ['gallery/app.js','gallery/style.css','gallery/vendor/model-viewer.min.js']:
        if (ROOT/path).read_bytes()!=(SITE/path).read_bytes(): raise SystemExit('Stale site asset: '+path)
    if not (SITE/'index.html').is_file() or not (SITE/'.nojekyll').exists(): raise SystemExit('Missing Pages entry point')
    if (SITE/'sources/context.json').exists() or (SITE/'.git').exists(): raise SystemExit('Private files in site')
print(json.dumps({'models':len(models),'licenses':sorted({m['licenseRaw'] for m in models}),'thumbnails':len(manifest['thumbnails']),'integrity':'passed','paths':'passed','credentialScan':'passed','siteChecked':SITE.exists()}))
