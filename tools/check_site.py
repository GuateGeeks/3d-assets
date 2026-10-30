"""Check the publication inventory, assets, licenses, paths and credentials."""
from pathlib import Path
from urllib.parse import urlsplit
import hashlib,json,os,re,sys
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'_site'
from reindex import records
canonical_records={m['id']:m for m in records()}  # Original integrity and current group manifests.
models=json.loads((ROOT/'index.json').read_text(encoding='utf-8'))['models']
if len({m['id'] for m in models})!=len(models): raise SystemExit('Duplicate IDs')
if set(canonical_records)!={m['id'] for m in models}: raise SystemExit('Stale catalog model IDs')
for m in models:
    if any(m.get(k)!=canonical_records[m['id']].get(k) for k in ['kitIds','variantGroupId','variantGroupTitle']): raise SystemExit('Stale catalog grouping')
    if m.get('providerId')=='polyhaven':
        review=json.loads((ROOT/m['provenance']['technicalReviewEvidence']).read_text(encoding='utf-8'))
        if review['technical']!='PASS' or review['glbSha256']!=m['sha256']: raise SystemExit('Poly Haven technical review mismatch')
        for name,digest in review['images'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest: raise SystemExit('Poly Haven review image changed')
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
for entry in manifest.get('decoders',{}).get('files',[]):
    decoder=ROOT/entry['file']
    if hashlib.sha256(decoder.read_bytes()).hexdigest()!=entry['sha256']: raise SystemExit('Decoder integrity mismatch')
    if SITE.exists() and (SITE/entry['file']).read_bytes()!=decoder.read_bytes(): raise SystemExit('Stale decoder in site')
for m in manifest['thumbnails']:
    if m.get('error') or hashlib.sha256((ROOT/m['file']).read_bytes()).hexdigest()!=m['sha256']: raise SystemExit('Thumbnail integrity mismatch')
for p in [ROOT/'gallery.html',*(ROOT/'gallery').glob('*.css')]:
    text=p.read_text(encoding='utf-8-sig')
    refs=re.findall(r'(?:src|href)="([^"]+)"',text) if p.suffix=='.html' else re.findall(r'url\([\"\x27]?([^\)\"\x27]+)',text)
    for ref in refs:
        if ref.startswith(('#','http:','https:','data:')): continue
        if not (p.parent/urlsplit(ref).path).is_file(): raise SystemExit('Missing local resource: '+ref)
for item in json.loads((ROOT/'sources/documents.json').read_text(encoding='utf-8'))['sources']:
    if hashlib.sha256((ROOT/'sources'/item['file']).read_bytes()).hexdigest()!=item['sha256']: raise SystemExit('Source evidence integrity mismatch: '+item['file'])
secret=re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})')
for directory,dirs,files in os.walk(ROOT,followlinks=False):
    base=Path(directory)
    included=[]
    for name in dirs:
        p=base/name
        if p.relative_to(ROOT).as_posix() in {'.git','_site','lab/.local'}: continue
        if p.is_symlink(): raise SystemExit('Unlisted symlink in source tree: '+str(p.relative_to(ROOT)))
        included.append(name)
    dirs[:]=included
    for name in files:
        p=base/name
        if p.is_symlink(): raise SystemExit('Unlisted symlink in source tree: '+str(p.relative_to(ROOT)))
        if not p.is_file() or p.suffix not in {'.md','.txt','.json','.js','.html','.py','.yml','.yaml','.css'}: continue
        text=p.read_text(encoding='utf-8-sig')
        if secret.search(text) or ('chatgpt'+'-conversation:') in text: raise SystemExit('Private material found: '+str(p.relative_to(ROOT)))
if SITE.exists():
    for path in ['gallery/app.js','gallery/lab.js','gallery/style.css','gallery/vendor/model-viewer.min.js']:
        if (ROOT/path).read_bytes()!=(SITE/path).read_bytes(): raise SystemExit('Stale site asset: '+path)
    if not (SITE/'index.html').is_file() or not (SITE/'.nojekyll').exists(): raise SystemExit('Missing Pages entry point')
    if (SITE/'sources/context.json').exists() or (SITE/'.git').exists(): raise SystemExit('Private files in site')
    for name in ['lab','creation-lab','procedural-web','.agents','derived','packs']:
        if (SITE/name).exists(): raise SystemExit('Unlisted laboratory files in site: '+name)
from compatibility import verify_display_variants
display_variants=verify_display_variants(ROOT,SITE if SITE.exists() else None,models)
print(json.dumps({'models':len(models),'licenses':sorted({m['licenseRaw'] for m in models}),'thumbnails':len(manifest['thumbnails']),'displayVariants':display_variants,'integrity':'passed','paths':'passed','credentialScan':'passed','siteChecked':SITE.exists()}))
