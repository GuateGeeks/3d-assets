"""Audit index consistency and document search coverage without network access."""
import csv, hashlib, json, os, re
from pathlib import Path
from collections import Counter
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
plan=read(ROOT/'selection.json'); catalog=read(ROOT/'index.json')['models']; selection=read(ROOT/'sources/selection-results.json'); ids={r['id'] for r in catalog}
if len(ids)!=len(catalog) or ids!=set(selection): raise ValueError('Selection/catalog IDs mismatch')
files=list((ROOT/'models').glob('*/model.glb'))
if len(files)!=len(catalog): raise ValueError('Model file count mismatch')
rows=list(csv.DictReader((ROOT/'index.csv').open(encoding='utf-8-sig',newline='')))
if {r['id'] for r in rows}!=ids or len(rows)!=len(catalog): raise ValueError('CSV mismatch')
for row in rows:
    r=next(m for m in catalog if m['id']==row['id'])
    if row['licenseRaw']!=r['licenseRaw'] or row['sha256']!=r['sha256'] or row['file']!=r['file']: raise ValueError('CSV field mismatch')
credits=(ROOT/'ATTRIBUTIONS.md').read_text(encoding='utf-8')
for mid in ids:
    if credits.count('`'+mid+'`')!=1: raise ValueError('Missing/duplicate attribution ID')
index_count=0
for p in (ROOT/'indices').rglob('*.json'):
    d=read(p); sub=d['modelIds']
    if len(sub)!=len(set(sub)) or len(sub)!=d['count'] or not set(sub)<=ids: raise ValueError('Invalid subset '+str(p))
    index_count+=1
for source in read(ROOT/'sources/documents.json')['sources']:
    if hashlib.sha256((ROOT/'sources'/source['file']).read_bytes()).hexdigest()!=source['sha256']: raise ValueError('Source snapshot hash mismatch')
key=os.environ.get('POLY_PIZZA_KEY'); scanned=0
if key:
    for p in ROOT.rglob('*'):
        if p.is_file() and p.suffix.lower() in {'.json','.md','.py','.txt','.csv','.html','.log'}:
            scanned+=1
            if key.encode() in p.read_bytes(): raise ValueError('Credential found in '+str(p))
coverage=[]
def title_match(query,title):
    terms=re.findall('[a-z0-9]+',query.lower())
    return all(re.search(r'\b'+re.escape(term)+r'(?:s|es)?\b',title.lower()) for term in terms)
for a in plan['areas']:
    for q in a['queries']:
        d=read(ROOT/'sources/search'/(quote(q,safe='')+'.json'))
        candidates=d.get('results',[]); selected=[r for r in catalog if q in r['queries']]
        literals=[m['Title'] for m in candidates if title_match(q,m['Title'])]
        coverage.append(dict(area=a['id'],query=q,totalApiResults=d.get('total'),inspectedResults=len(candidates),literalTitleMatches=literals,downloaded=[dict(id=r['id'],title=r['title'],license=r['licenseRaw'],unfulfilledQueries=r.get('unfulfilledQueries',[]),classificationNote=r.get('classificationNote')) for r in selected],review='Revisar pertinencia semántica y visual' if not literals else 'Revisar modelo antes de publicar'))
save(ROOT/'coverage.json',dict(scope='Primera página de hasta 12 candidatos por consulta; coincidencia nominal no acredita exactitud educativa, científica ni cultural.',queries=coverage))
ambiguous=[q for q in coverage if not q['literalTitleMatches']]
lines=['# Cobertura y coincidencias pendientes','',f"{len(catalog)} modelos originales en {len(plan['areas'])} áreas; {len(coverage)} consultas inspeccionadas.",'','La biblioteca es una selección inicial para revisión y autoría. La API puede devolver aproximaciones semánticas. Las consultas siguientes no tienen una coincidencia literal completa en el título dentro de la primera página inspeccionada. Esto no prueba que el modelo no exista en todo el catálogo. No renombrar un recurso para presentarlo como una especie, instrumento o sitio que no ha sido verificado.','','| Consulta | Recursos descargados |','| --- | --- |']
for q in ambiguous:
    models='; '.join(m['title'].replace('|','\\|') for m in q['downloaded']) or 'Ninguno'
    lines.append(f"| {q['query']} | {models} |")
lines+=['','## Contexto guatemalteco','','Un loro no se acredita como quetzal, un xilófono no se acredita como marimba y un templo genérico no se acredita como una reconstrucción de Tikal. Los modelos similares se conservan con su título original y se reclasifican cuando la asociación es incorrecta; `unfulfilledQueries` identifica los objetos solicitados que esos recursos no acreditan. No se consideran necesidades resueltas. Para revisar la respuesta completa, consultar `sources/search/<consulta>.json`.','','## Animaciones','','`gltf` conserva lo encontrado en cada archivo. `apiAnimated` registra lo declarado por el catálogo. Ver [animados](indices/animation/animated.md), [con esqueleto](indices/animation/rigged.md) e [inconsistencias](indices/review/api-animation-mismatch.json).','','## Licencias','','La cobertura de licencias de todos los candidatos inspeccionados, incluyendo los no seleccionados, está en [sources/license-coverage.json](sources/license-coverage.json). Cada licencia encontrada está representada en la descarga; no se inventan licencias que no aparecieron en las consultas.']
(ROOT/'COVERAGE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
report=dict(models=len(catalog),glbFiles=len(files),csvRows=len(rows),uniqueIds=len(ids),subsetIndices=index_count,licenseCounts=dict(Counter(r['licenseRaw'] for r in catalog)),queries=len(coverage),queriesWithoutLiteralTitleMatch=len(ambiguous),sourceSnapshotHashes='passed',credentialScan=dict(textFilesScanned=scanned,matches=0,performed=bool(key)),result='passed')
save(ROOT/'audit.json',report)
print(json.dumps(report,ensure_ascii=True,indent=2))
