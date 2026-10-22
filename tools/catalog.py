"""Poly Pizza downloader and offline indexer. Python standard library only."""
import csv, hashlib, json, os, re, struct, time, sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import quote, urlparse
from urllib.error import HTTPError
ROOT = Path(__file__).resolve().parents[1]
API = 'https://api.poly.pizza/v1/'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def get(url,key=None):
    host=urlparse(url).hostname
    if urlparse(url).scheme!='https' or host not in {'api.poly.pizza','static.poly.pizza','poly.pizza','raw.githubusercontent.com','creativecommons.org'}: raise ValueError('Unapproved URL')
    headers={'User-Agent':'GuateGeeks-Educational-Asset-Catalog/1.0'}
    if key and host=='api.poly.pizza': headers['X-Auth-Token']=key
    for attempt in range(5):
        try:
            with urlopen(Request(url,headers=headers),timeout=90) as r:
                data=r.read(80*1024*1024+1)
                if len(data)>80*1024*1024: raise ValueError('Resource exceeds 80 MiB')
                return data
        except HTTPError as e:
            if e.code not in {429,500,502,503,504} or attempt==4: raise
            time.sleep(max(1,min(60,int(e.headers.get('Retry-After',2**attempt)))))
        except (OSError,TimeoutError):
            if attempt==4: raise
            time.sleep(2**attempt)
def inspect(data):
    if len(data)<20 or data[:4]!=b'glTF': raise ValueError('Not GLB')
    version,size=struct.unpack_from('<II',data,4)
    if version!=2 or size!=len(data): raise ValueError('Invalid version/length')
    pos=12; doc=None
    while pos<size:
        length,kind=struct.unpack_from('<II',data,pos); end=pos+8+length
        if end>size or length%4: raise ValueError('Invalid chunk')
        if kind==0x4e4f534a: doc=json.loads(data[pos+8:end].decode('utf-8'))
        pos=end
    if not doc or not doc.get('meshes'): raise ValueError('No geometry')
    external=[x['uri'] for g in ('buffers','images') for x in doc.get(g,[]) if x.get('uri') and not x['uri'].startswith('data:')]
    skins=doc.get('skins',[]); animations=doc.get('animations',[])
    return dict(version=version,meshes=len(doc['meshes']),nodes=len(doc.get('nodes',[])),materials=len(doc.get('materials',[])),skins=len(skins),joints=sum(len(s.get('joints',[])) for s in skins),rigged=bool(skins),animated=bool(animations),animations=len(animations),animationNames=[a.get('name',f'animation_{i}') for i,a in enumerate(animations)],externalDependencies=external,selfContained=not external,extensionsRequired=doc.get('extensionsRequired',[]))
def license_info(raw):
    if raw in {'CC0','CC0 1.0'}: return dict(id='CC0-1.0',url='https://creativecommons.org/publicdomain/zero/1.0/',attributionRequired=False,commercialUse=True,derivatives=True,shareAlike=False)
    m=re.fullmatch(r'CC-(BY(?:-NC)?(?:-SA|-ND)?)\s+(\d\.\d)',raw or '')
    if m:
        code,v=m.groups()
        return dict(id=f'CC-{code}-{v}',url=f'https://creativecommons.org/licenses/{code.lower()}/{v}/',attributionRequired=True,commercialUse='-NC' not in code,derivatives='-ND' not in code,shareAlike='-SA' in code)
    return dict(id='UNKNOWN',url=None,attributionRequired=None,commercialUse=None,derivatives=None,shareAlike=None)
def download():
    key=os.environ.get('POLY_PIZZA_KEY')
    if not key: raise SystemExit('Set POLY_PIZZA_KEY in this process; never saved')
    plan=read(ROOT/'selection.json'); issues=[]; chosen={}
    for area in plan['areas']:
        for q in area['queries']:
            try:
                cache=ROOT/'sources/search'/(quote(q,safe='')+'.json')
                if not cache.exists():
                    save(cache,json.loads(get(API+'search/'+quote(q,safe='')+'?limit=12&format=glb',key))); time.sleep(.2)
                results=read(cache).get('results',[])
                terms=re.findall('[a-z0-9]+',q.lower())
                matches=[m for m in results if any(t in m.get('Title','').lower() for t in terms)]
                selected=(matches or results[:1])[:plan['modelsPerQuery']]
                if not selected: issues.append(dict(area=area['id'],query=q,reason='No results'))
                for m in selected:
                    mid=m['ID']
                    if not re.fullmatch('[A-Za-z0-9_-]+',mid): raise ValueError('Unsafe ID')
                    item=chosen.setdefault(mid,dict(model=m,areas=[],queries=[]))
                    if area['id'] not in item['areas']: item['areas'].append(area['id'])
                    if q not in item['queries']: item['queries'].append(q)
                print(f"SEARCH {area['id']}: {q}: {len(selected)}",flush=True)
            except Exception as e: issues.append(dict(area=area['id'],query=q,reason=str(e)))
    save(ROOT/'sources/selection-results.json',chosen)
    for n,(mid,item) in enumerate(chosen.items(),1):
        folder=ROOT/'models'/mid; folder.mkdir(parents=True,exist_ok=True)
        try:
            raw=folder/'source.json'
            if not raw.exists(): save(raw,json.loads(get(API+'model/'+mid,key))); time.sleep(.15)
            m=read(raw); p=folder/'model.glb'
            data=p.read_bytes() if p.exists() else get(m['Download'])
            gltf=inspect(data)
            if not gltf['selfContained']: raise ValueError('Unresolved external dependencies')
            if not p.exists(): p.write_bytes(data)
            lic=license_info(m.get('Licence')); author=m.get('Creator',{}).get('Username','Unknown')
            attribution=m.get('Attribution') or f'"{m["Title"]}" by {author}, https://poly.pizza/m/{mid}. {m.get("Licence")}'
            subjects=sorted({s for a in plan['areas'] if a['id'] in item['areas'] for s in a['subjects']})
            r=dict(id=mid,title=m['Title'],author=author,authorUrl='https://poly.pizza/u/'+quote(author,safe=''),sourceUrl='https://poly.pizza/m/'+mid,metadataUrl=API+'model/'+mid,downloadUrl=m['Download'],thumbnailUrl=m.get('Thumbnail'),description=m.get('Description'),category=m.get('Category'),tags=m.get('Tags',[]),areas=item['areas'],queries=item['queries'],subjects=subjects,products=['code-studio','socrates'],licenseRaw=m.get('Licence'),license=lic,attribution=attribution,modifications='Ninguna: GLB original sin conversión',file=f'models/{mid}/model.glb',sourceMetadataFile=f'models/{mid}/source.json',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),apiTriangleCount=m.get('Tri Count',m.get('TriangleCount')),apiAnimated=m.get('Animated'),gltf=gltf,retrievedAt=datetime.now(timezone.utc).isoformat(),reviewStatus='pending',educationalReview='Revisar adecuación visual, cultural y científica; asociación por búsqueda, sin acreditación curricular')
            save(folder/'metadata.json',r)
            (folder/'LICENSE.txt').write_text(f"{r['licenseRaw']}\n{lic['url']}\n\n{attribution}\n\nOrigen: {r['sourceUrl']}\nCambios: {r['modifications']}\nEvaluación de uso: pendiente.\n",encoding='utf-8')
            print(f"MODEL {n}/{len(chosen)} {mid} {m['Title']}: {len(data)} bytes",flush=True)
        except Exception as e: issues.append(dict(id=mid,reason=str(e)))
    save(ROOT/'download-issues.json',issues); build()
def build():
    plan=read(ROOT/'selection.json'); records=[]; errors=[]
    for p in sorted((ROOT/'models').glob('*/metadata.json')):
        r=read(p)
        flags=[]
        title=r['title'].lower()
        description=(r.get('description') or '').lower()
        substitutions=[('quetzal','parrot','guatemala-contexto','animales-biodiversidad'),('tapir','collared peccary','guatemala-contexto','animales-biodiversidad'),('ceiba','bamboo','guatemala-contexto','bosques-plantas'),('marimba','xylophone','guatemala-contexto','arte-musica'),('pottery','honey','historia-patrimonio','alimentos-agricultura'),('lungs','chest','cuerpo-salud','escenarios-videojuegos')]
        unmet=set(r.get('unfulfilledQueries',[]))
        for query,other,old_area,new_area in substitutions:
            if query in r['queries'] and other in title:
                unmet.add(query)
                if old_area in r['areas']:
                    r['areas']=sorted(set(a for a in r['areas'] if a!=old_area)|{new_area})
                r['classificationNote']=f'Recurso reclasificado por título original: {r["title"]}; no satisface la búsqueda {query}.'
        if 'cacao' in r['queries'] and 'coffee' in title: unmet.add('cacao')
        if 'tikal' in r['queries']: unmet.add('tikal')
        if 'pulley' in r['queries'] and 'hose wheel' in title: unmet.add('pulley')
        if 'motor' in r['queries'] and 'motorcycle' in title: unmet.add('motor')
        if 'electric motor' in r['queries'] and 'generator' in title: unmet.add('electric motor')
        r['unfulfilledQueries']=sorted(unmet)
        if unmet: flags.append('requested-object-not-confirmed')

        if 'motorcycle' in title and 'robotica-electronica' in r['areas']:
            r['areas']=[a for a in r['areas'] if a!='robotica-electronica']+['transporte-movilidad']
            r['classificationNote']='Reclasificado: búsqueda motor devolvió motocicleta; conservar consulta original como evidencia.'
        if 'race circuit' in title and 'robotica-electronica' in r['areas']:
            r['areas']=[a for a in r['areas'] if a!='robotica-electronica']+['escenarios-videojuegos']
            r['classificationNote']='Reclasificado: circuito de carreras, no placa electrónica.'
        if 'mixamo' in description: flags.append('third-party-animation-mentioned')
        if re.search(r'\b(gun|weapon|zombie|enemy)\b',title): flags.append('fantasy-or-combat-classroom-review')
        if re.search(r'\b(macbook|nintendo|pokemon|lego|rubik)\b',title): flags.append('brand-or-third-party-character-review')
        if 'cuerpo-salud' in r['areas']: flags.append('anatomy-accuracy-review')
        if {'historia-patrimonio','guatemala-contexto'} & set(r['areas']): flags.append('cultural-or-species-identification-review')
        if bool(r.get('apiAnimated'))!=r['gltf']['animated']: flags.append('api-animation-metadata-disagrees-with-glb')
        if r['license']['id']=='UNKNOWN': flags.append('unrecognized-license')
        r['reviewFlags']=flags
        r['subjects']=sorted({sub for a in plan['areas'] if a['id'] in r['areas'] for sub in a['subjects']})
        save(p,r)
        try:
            data=(ROOT/r['file']).read_bytes()
            if hashlib.sha256(data).hexdigest()!=r['sha256']: raise ValueError('SHA mismatch')
            if len(data)!=r['bytes']: raise ValueError('Length mismatch')
            if inspect(data)!=r['gltf']: raise ValueError('GLB mismatch')
            if not (p.parent/'LICENSE.txt').exists(): raise ValueError('Missing license file')
            source=read(p.parent/'source.json')
            if source.get('Licence')!=r['licenseRaw']: raise ValueError('Source license mismatch')
            if source.get('Attribution') and source['Attribution']!=r['attribution']: raise ValueError('Source attribution mismatch')
            records.append(r)
        except Exception as e: errors.append(dict(id=r['id'],error=str(e)))
    summary=dict(schemaVersion=1,generatedAt=datetime.now(timezone.utc).isoformat(),models=len(records),bytes=sum(r['bytes'] for r in records),rigged=sum(r['gltf']['rigged'] for r in records),animated=sum(r['gltf']['animated'] for r in records),licenses={},areas={},errors=errors,validationScope='SHA-256, bytes, GLB v2 chunks/JSON/geometry and embedded dependencies; rendering pending')
    summary['animationMetadataMismatches']=sum(bool(r.get('apiAnimated'))!=r['gltf']['animated'] for r in records)
    summary['flaggedForReview']=sum(bool(r.get('reviewFlags')) for r in records)
    save(ROOT/'index.json',dict(schemaVersion=1,source='Poly Pizza API v1.1',licensePolicy='Todas las licencias devueltas; evaluación de uso pendiente',models=records))
    def subset(name,rs,details=None):
        save(ROOT/'indices'/(name+'.json'),dict(schemaVersion=1,details=details,count=len(rs),modelIds=[r['id'] for r in rs]))
        if name.startswith(('areas/','animation/','licenses/')):
            title=details.get('title',name) if isinstance(details,dict) else name
            lines=[f'# {title}','',f'{len(rs)} modelos. Evaluación de uso pendiente. Créditos completos: [ATTRIBUTIONS.md](../../ATTRIBUTIONS.md).','','| Modelo | Licencia | Autor | GLB | Esqueleto / Clips |','| --- | --- | --- | --- | --- |']
            for r in rs:
                label=r['title'].replace('|','\\|'); author=r['author'].replace('|','\\|')
                lines.append(f"| [{label}]({r['sourceUrl']}) | [{r['licenseRaw']}]({r['license']['url']}) | {author} | [Archivo](../../{r['file']}) | {r['gltf']['skins']} / {r['gltf']['animations']} |")
            (ROOT/'indices'/(name+'.md')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    for a in plan['areas']:
        rs=[r for r in records if a['id'] in r['areas']]; summary['areas'][a['id']]=len(rs); subset('areas/'+a['id'],rs,a)
    for raw in sorted({r['licenseRaw'] for r in records}):
        rs=[r for r in records if r['licenseRaw']==raw]; summary['licenses'][raw]=len(rs); subset('licenses/'+re.sub('[^a-z0-9]+','-',raw.lower()).strip('-'),rs,license_info(raw))
    for c in sorted({r['category'] or 'Unknown' for r in records}): subset('categories/'+re.sub('[^a-z0-9]+','-',c.lower()).strip('-'),[r for r in records if (r['category'] or 'Unknown')==c],c)
    for s in sorted({s for r in records for s in r['subjects']}): subset('subjects/'+re.sub('[^a-z0-9]+','-',s.lower()).strip('-'),[r for r in records if s in r['subjects']],s)
    subset('products/code-studio',records,'Mundos y escenas programables; integración en aplicación pendiente')
    subset('products/socrates',records,'Biblioteca candidata para lecciones CNB y STEAM; asignación docente pendiente')
    subset('animation/rigged',[r for r in records if r['gltf']['rigged']])
    subset('animation/animated',[r for r in records if r['gltf']['animated']])
    subset('animation/static',[r for r in records if not r['gltf']['animated']])
    subset('review/flagged',[r for r in records if r.get('reviewFlags')])
    subset('review/unfulfilled-queries',[r for r in records if r.get('unfulfilledQueries')])
    subset('review/api-animation-mismatch',[r for r in records if bool(r.get('apiAnimated'))!=r['gltf']['animated']])
    fields=['id','title','author','licenseRaw','licenseUrl','attributionRequired','commercialUse','derivatives','shareAlike','areas','subjects','file','bytes','sha256','sourceUrl','rigged','animated','animationNames','reviewStatus','reviewFlags','attribution']
    with (ROOT/'index.csv').open('w',newline='',encoding='utf-8-sig') as out:
        w=csv.DictWriter(out,fieldnames=fields); w.writeheader()
        for r in records:
            row={f:r.get(f) for f in fields}
            row['reviewFlags']='; '.join(r.get('reviewFlags',[]))
            row.update(licenseUrl=r['license']['url'],attributionRequired=r['license']['attributionRequired'],commercialUse=r['license']['commercialUse'],derivatives=r['license']['derivatives'],shareAlike=r['license']['shareAlike'],areas='; '.join(r['areas']),subjects='; '.join(r['subjects']),rigged=r['gltf']['rigged'],animated=r['gltf']['animated'],animationNames='; '.join(r['gltf']['animationNames']))
            w.writerow(row)
    credits=['# Créditos de modelos Poly Pizza','','GLB originales sin modificaciones. Cada modelo conserva su licencia individual.','']
    for r in records: credits.append(f"- **{r['title']}** (`{r['id']}`): {r['attribution']} · {r['licenseRaw']} · {r['license']['url']}")
    (ROOT/'ATTRIBUTIONS.md').write_text('\n'.join(credits)+'\n',encoding='utf-8')
    lines=['# Índice de modelos','',f"{len(records)} modelos · {summary['bytes']/1024**2:.1f} MiB · {summary['rigged']} con esqueleto · {summary['animated']} animados.",'','| Área | Modelos |','| --- | ---: |']
    for a in plan['areas']: lines.append(f"| [{a['title']}](indices/areas/{a['id']}.md) | {summary['areas'][a['id']]} |")
    lines+=['','| Modelo | Autor | Licencia | Archivo | Rig / Animaciones |','| --- | --- | --- | --- | --- |']
    for r in records:
        title=r['title'].replace('|','\\|'); author=r['author'].replace('|','\\|')
        lines.append(f"| [{title}]({r['sourceUrl']}) | {author} | {r['licenseRaw']} | [GLB]({r['file']}) | {r['gltf']['skins']} / {r['gltf']['animations']} |")
    (ROOT/'INDEX.md').write_text('\n'.join(lines)+'\n',encoding='utf-8'); save(ROOT/'validation.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    if errors: raise SystemExit(1)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('action',choices=['download','verify']); a=p.parse_args()
    download() if a.action=='download' else build()
