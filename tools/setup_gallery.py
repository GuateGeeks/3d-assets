"""Fetch pinned, licensed gallery dependencies and source thumbnails."""
import base64, concurrent.futures, hashlib, io, json, tarfile, time
from pathlib import Path
from urllib.request import Request, urlopen
ROOT=Path(__file__).resolve().parents[1]
def get(url):
    for n in range(4):
        try:
            with urlopen(Request(url,headers={'User-Agent':'GuateGeeks-Local-Gallery/1.0'}),timeout=60) as r: return r.read()
        except Exception:
            if n==3: raise
            time.sleep(2**n)
def save(p,b): p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b)
def package(name,version,files):
    meta=json.loads(get('https://registry.npmjs.org/'+name+'/'+version))
    data=get(meta['dist']['tarball']); algo,expected=meta['dist']['integrity'].split('-',1)
    if base64.b64encode(hashlib.new(algo,data).digest()).decode()!=expected: raise ValueError('NPM integrity mismatch')
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as t:
        for source,dest in files:
            f=t.extractfile('package/'+source)
            if f is None: raise ValueError('Missing package member '+source)
            save(ROOT/'gallery/vendor'/dest,f.read())
    return dict(name=name,version=version,license=meta.get('license'),url=meta['dist']['tarball'],integrity=meta['dist']['integrity'])
deps=[package('@google/model-viewer','4.4.0',[('dist/model-viewer.min.js','model-viewer.min.js'),('LICENSE','model-viewer.LICENSE')]),package('@fontsource/inter','5.3.0',[(f'files/inter-latin-{w}-normal.woff2',f'inter-{w}.woff2') for w in (400,500,600,700)]+[('LICENSE','inter.LICENSE')])]
models=json.loads((ROOT/'index.json').read_text(encoding='utf-8'))['models']
def thumbnail(m):
    try:
        path=ROOT/'gallery/thumbnails'/(m['id']+'.webp')
        if not path.exists(): save(path,get(m['thumbnailUrl']))
        data=path.read_bytes()
        if data[:4]!=b'RIFF' or data[8:12]!=b'WEBP': raise ValueError('Not WebP')
        return dict(id=m['id'],file='gallery/thumbnails/'+path.name,url=m['thumbnailUrl'],sha256=hashlib.sha256(data).hexdigest(),modelLicense=m['licenseRaw'])
    except Exception as e: return dict(id=m['id'],error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: thumbs=list(pool.map(thumbnail,models))
manifest=dict(dependencies=deps,thumbnails=thumbs,note='Original catalog previews; per-model license and credits remain in index.json. No API key is used.')
save(ROOT/'gallery/dependencies.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(dependencies=deps,thumbnails=len(thumbs),errors=[x for x in thumbs if 'error' in x]),indent=2))
