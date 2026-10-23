"""Rebuild all catalog indices without modifying any original metadata or asset bytes."""
import csv,hashlib,json,re
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from catalog import inspect
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def records():
    output=[];seen=set()
    for path in sorted((ROOT/'models').glob('*/metadata.json')):
        m=read(path)
        if m['id'] in seen:raise ValueError('Duplicate ID')
        seen.add(m['id']);target=(ROOT/m['file']).resolve()
        if not target.is_relative_to((ROOT/'models').resolve()):raise ValueError('Unsafe asset path')
        data=target.read_bytes()
        if len(data)!=m['bytes'] or hashlib.sha256(data).hexdigest()!=m['sha256']:raise ValueError('Asset integrity '+m['id'])
        if inspect(data)!=m['gltf']:raise ValueError('GLB inspection changed '+m['id'])
        if not m['gltf']['selfContained']:raise ValueError('External dependencies '+m['id'])
        if not (path.parent/'LICENSE.txt').is_file():raise ValueError('Missing license')
        source=read(path.parent/'source.json')
        if source.get('Licence')!=m['licenseRaw'] or source.get('Attribution')!=m['attribution']:raise ValueError('Source license/credit mismatch '+m['id'])
        m.setdefault('providerId','poly-pizza');m.setdefault('provider','Poly Pizza')
        if m['providerId']!='poly-pizza':
            if hashlib.sha256((ROOT/m['originalDownload']).read_bytes()).hexdigest()!=m['provenance']['originalDownloadSha256']:raise ValueError('Original ZIP changed '+m['id'])
            for file in m['provenance']['originalFiles']:
                p=(ROOT/file['file']).resolve()
                if not p.is_relative_to(path.parent.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=file['sha256']:raise ValueError('Original evidence mismatch')
            if m['qa']['technical']!='PASS' or m['qa']['visual']!='PASS' or m['qa']['rights']!='PASS':raise ValueError('External resource has incomplete QA')
            if m['providerId']=='polyhaven':
                for field in ['licenseEvidence','metadataEvidence','fileManifestEvidence','technicalReviewEvidence']:
                    if hashlib.sha256((ROOT/m['provenance'][field]).read_bytes()).hexdigest()!=m['provenance'][field+'Sha256']:raise ValueError('Poly Haven evidence changed: '+field)
        output.append(m)
    kits_file=ROOT/'kits/index.json';membership={}
    if kits_file.exists():
        for kit in read(kits_file)['kits']:
            for entry in kit.get('assets',[]):membership.setdefault(entry['modelId'],set()).add(kit['id'])
    group_map={}
    for manifest in [ROOT/'kits/groups.json',*sorted((ROOT/'groups').glob('*.json'))]:
        if not manifest.exists():continue
        for group in read(manifest)['groups']:
            for mid in group['modelIds']:
                if mid not in seen:raise ValueError('Unknown grouped model '+mid)
                if mid in group_map and group_map[mid]['id']!=group['id']:raise ValueError('Conflicting variant families '+mid)
                group_map[mid]=group
    for m in output:
        m['kitIds']=sorted(membership.get(m['id'],[]))
        if m['id'] in group_map:
            group=group_map[m['id']];m['variantGroupId']=group['id'];m['variantGroupTitle']=group['title']
    return output

def rebuild():
    plan=read(ROOT/'selection.json');rs=records()
    summary={'schemaVersion':2,'generatedAt':datetime.now(timezone.utc).isoformat(),'models':len(rs),'bytes':sum(m['bytes'] for m in rs),'rigged':sum(m['gltf']['rigged'] for m in rs),'animated':sum(m['gltf']['animated'] for m in rs),'licenses':dict(Counter(m['licenseRaw'] for m in rs)),'providers':dict(Counter(m['provider'] for m in rs)),'areas':{a['id']:sum(a['id'] in m['areas'] for m in rs) for a in plan['areas']},'errors':[],'validationScope':'SHA-256, source evidence, GLB structure and offline dependencies; external rendering QA is recorded per model'}
    save(ROOT/'index.json',{'schemaVersion':2,'source':', '.join(sorted({m['provider'] for m in rs})),'licensePolicy':'Licencias individuales conservadas; uso educativo concreto pendiente de revisión docente','models':rs,'kits':[{k:v for k,v in kit.items() if k not in {'members','assets'}} for kit in read(ROOT/'kits/index.json')['kits']] if (ROOT/'kits/index.json').exists() else []})
    def subset(name,group,details=None):
        save(ROOT/'indices'/(name+'.json'),{'schemaVersion':2,'details':details,'count':len(group),'modelIds':[m['id'] for m in group]})
        if name.startswith(('areas/','licenses/','animation/','providers/')):
            title=details.get('title',name) if isinstance(details,dict) else details or name
            lines=['# '+str(title),'',str(len(group))+' modelos. Créditos: [ATTRIBUTIONS.md](../../ATTRIBUTIONS.md).','','| Modelo | Fuente | Licencia | Autor | GLB | Rig / clips |','| --- | --- | --- | --- | --- | --- |']
            for m in group:lines.append('| ['+m['title'].replace('|',chr(92)+'|')+']('+m['sourceUrl']+') | '+m['provider']+' | ['+m['licenseRaw']+']('+m['license']['url']+') | '+m['author'].replace('|',chr(92)+'|')+' | [GLB](../../'+m['file']+') | '+str(m['gltf']['skins'])+' / '+str(m['gltf']['animations'])+' |')
            (ROOT/'indices'/(name+'.md')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    slug=lambda s:re.sub('[^a-z0-9]+','-',s.lower()).strip('-')
    for a in plan['areas']:subset('areas/'+a['id'],[m for m in rs if a['id'] in m['areas']],a)
    for raw in summary['licenses']:subset('licenses/'+slug(raw),[m for m in rs if m['licenseRaw']==raw],next(m['license'] for m in rs if m['licenseRaw']==raw))
    for provider in sorted({m['providerId'] for m in rs}):subset('providers/'+provider,[m for m in rs if m['providerId']==provider],next(m['provider'] for m in rs if m['providerId']==provider))
    for kit in read(ROOT/'kits/index.json')['kits'] if (ROOT/'kits/index.json').exists() else []:subset('kits/'+kit['id'],[m for m in rs if kit['id'] in m.get('kitIds',[])],{k:v for k,v in kit.items() if k not in {'members','assets'}})
    for category in sorted({m['category'] or 'Unknown' for m in rs}):subset('categories/'+slug(category),[m for m in rs if (m['category'] or 'Unknown')==category],category)
    for subject in sorted({s for m in rs for s in m['subjects']}):subset('subjects/'+slug(subject),[m for m in rs if subject in m['subjects']],subject)
    for product in ['code-studio','socrates']:subset('products/'+product,[m for m in rs if product in m['products']], 'Biblioteca candidata; asignación docente pendiente')
    subset('animation/rigged',[m for m in rs if m['gltf']['rigged']]);subset('animation/animated',[m for m in rs if m['gltf']['animated']]);subset('animation/static',[m for m in rs if not m['gltf']['animated']])
    subset('review/flagged',[m for m in rs if m.get('reviewFlags')]);subset('review/unfulfilled-queries',[m for m in rs if m.get('unfulfilledQueries')]);subset('review/api-animation-mismatch',[m for m in rs if m.get('apiAnimated') is not None and bool(m['apiAnimated'])!=m['gltf']['animated']])
    fields=['id','title','providerId','provider','kitIds','variantGroupId','variantGroupTitle','author','licenseRaw','licenseUrl','attributionRequired','commercialUse','derivatives','shareAlike','areas','subjects','file','bytes','sha256','sourceUrl','rigged','animated','animationNames','reviewStatus','reviewFlags','modifications','attribution']
    with (ROOT/'index.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for m in rs:
            row={k:m.get(k) for k in fields}
            for k in ['areas','subjects','reviewFlags','kitIds']:row[k]='; '.join(m.get(k,[]))
            row.update(licenseUrl=m['license']['url'],**{k:m['license'][k] for k in ['attributionRequired','commercialUse','derivatives','shareAlike']},rigged=m['gltf']['rigged'],animated=m['gltf']['animated'],animationNames='; '.join(m['gltf']['animationNames']))
            writer.writerow(row)
    lines=['# Créditos y licencias de los modelos','','Originales y derivados web conservan sus licencias individuales. Los cambios y la procedencia se indican en cada entrada.','']
    for m in rs:lines.append('- **'+m['title']+'** (`'+m['id']+'`): '+m['attribution']+' · '+m['licenseRaw']+' · '+m['license']['url']+' · '+m['modifications'])
    (ROOT/'ATTRIBUTIONS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    lines=['# Índice de modelos','',str(len(rs))+' modelos · '+str(round(summary['bytes']/1024**2,1))+' MiB.','','| Área | Modelos |','| --- | ---: |']
    for a in plan['areas']:lines.append('| ['+a['title']+'](indices/areas/'+a['id']+'.md) | '+str(summary['areas'][a['id']])+' |')
    lines+=['','| Modelo | Fuente | Autor | Licencia | Archivo |','| --- | --- | --- | --- | --- |']
    for m in rs:lines.append('| ['+m['title'].replace('|',chr(92)+'|')+']('+m['sourceUrl']+') | '+m['provider']+' | '+m['author'].replace('|',chr(92)+'|')+' | '+m['licenseRaw']+' | [GLB]('+m['file']+') |')
    (ROOT/'INDEX.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');save(ROOT/'validation.json',summary)
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':rebuild()
