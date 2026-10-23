"""Promote a reviewed, deduplicated external selection. Existing model folders are immutable.
This command is deliberately offline; acquisition URLs and archive hashes come from staged evidence.
"""
import json,hashlib,shutil,zipfile,sys
from pathlib import Path
from PIL import Image
from catalog import inspect,license_info
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def promote(selection):
    selection=selection.resolve();run=selection.parent;items=read(selection)['items'];dedup=read(run/'deduplication.json')
    if dedup['baselineFingerprintCount']!=dedup['baselineModels'] or dedup['unsupported']:raise ValueError('Incomplete duplicate check')
    if any(c['exactMatches'] or c['geometryMatches'] for c in dedup['comparisons']):raise ValueError('Duplicate candidates need review')
    for name,digest in read(run/'original-inventory.json').items():
        if sha(ROOT/name)!=digest:raise ValueError('Original catalog asset changed: '+name)
    visual=read(run/'visual-review.json')
    if visual['result']!='PASS':raise ValueError('Visual review incomplete')
    plan=read(ROOT/'selection.json');dependencies=read(ROOT/'gallery/dependencies.json')
    sources=ROOT/'sources/external';sources.mkdir(exist_ok=True)
    reviewed=[]
    for name,digest in visual['images'].items():
        src=run/name
        if sha(src)!=digest:raise ValueError('Reviewed image changed')
        dest=sources/'review'/name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(src,dest)
        reviewed.append({'file':dest.relative_to(ROOT).as_posix(),'sha256':digest})
    for item in items:
        mid=item['id'];folder=ROOT/'models'/mid
        if folder.exists():raise ValueError('Refusing to replace existing model '+mid)
        result=Path(item['output']);review=read(result/'review.json');glb=result/'model.glb'
        if review['technical']!='PASS' or sha(glb)!=review['glbSha256']:raise ValueError('Conversion evidence mismatch')
        data=glb.read_bytes();gltf=inspect(data)
        if not gltf['selfContained'] or len(data)>25*1024**2:raise ValueError('Web asset limit/dependency')
        comparison=next(c for c in dedup['comparisons'] if c['id']==mid)
        if comparison['sha256']!=sha(glb):raise ValueError('Dedup evidence mismatch')
        pack=item['pack'];acquisition=read(run/pack/'acquisition.json');kenney=pack.startswith('kenney')
        providerId='kenney' if kenney else 'opengameart';provider='Kenney' if kenney else 'OpenGameArt';author='Kenney' if kenney else 'Elegant Crow'
        raw='CC0 1.0' if kenney else 'CC-BY-SA 4.0';lic=license_info(raw)
        sourceFolder=sources/pack;sourceFolder.mkdir(exist_ok=True)
        original=Path(item['input']);rawFiles=[original]
        doc=None
        if original.suffix=='.glb':
            from geometry_fingerprint import document
            doc,_=document(original.read_bytes())
            for image in doc.get('images',[]):
                if image.get('uri') and not image['uri'].startswith('data:'):rawFiles.append(original.parent/image['uri'])
        else:rawFiles.append(original.parents[1]/'textures_512x512'/(original.stem+'_tex_512.png'))
        if any(not p.is_file() for p in rawFiles):raise ValueError('Missing original component')
        version={'kenney-nature':'Nature Kit 2.1','kenney-food':'Food Kit 2.0','kenney-buildings':'Modular Buildings 2.1','oga-gears':'Gear Pack (2020-09-01)'}[pack]
        changes='Ninguna: GLB original sin conversión' if pack=='kenney-nature' else 'GLB exportado con Blender '+review['blenderVersion']+'; '
        if pack in ['kenney-food','kenney-buildings']:changes+='textura original incrustada, sin cambio de escala; geometría y dimensiones comprobadas al reimportar.'
        elif pack=='oga-gears':changes+='OBJ convertido, textura original de 512 px asignada e incrustada; sin cambio de escala; material PBR configurado para el visor.'
        credit='"'+item['title']+'" ('+Path(item['member']).stem+'), por '+author+', '+acquisition['pageUrl']+'. '+raw+', '+lic['url']+'.'
        if not kenney:credit+=' Textura: CC0Textures.com, según el crédito del autor. Adaptación GLB y miniatura: GuateGeeks; conserva CC BY-SA 4.0.'
        evidence={'schemaVersion':1,'providerId':providerId,'pack':version,'author':author,'pageUrl':acquisition['pageUrl'],'downloadUrl':acquisition['downloadUrl'],'archiveSha256':acquisition['sha256'],'archiveBytes':acquisition['bytes'],'pageSnapshotSha256':acquisition['pageSha256'],'retrievedAt':acquisition['retrievedAt'],'license':lic,'licenseRaw':raw}
        if not kenney:evidence.update(attributionNotice='Credit is not required if you are not sharing it on other asset hosting sites, but it is always appreciated.',textureCredit='CC0Textures.com (author statement on the source page)')
        save(sourceFolder/'source.json',evidence)
        if kenney:shutil.copyfile(run/pack/'extracted/License.txt',sourceFolder/'License.txt')
        else:(sourceFolder/'License.txt').write_text('Gear Pack — Elegant Crow\nCC BY-SA 4.0\nhttps://creativecommons.org/licenses/by-sa/4.0/\nFuente: '+acquisition['pageUrl']+'\nTexturas: CC0Textures.com, según el autor.\n',encoding='utf-8')
        folder.mkdir();shutil.copyfile(glb,folder/'model.glb');originalRecords=[]
        for file in rawFiles:
            relative=file.relative_to(original.parent).as_posix() if file.is_relative_to(original.parent) else 'textures/'+file.name
            target=folder/'original'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
            originalRecords.append({'file':target.relative_to(ROOT).as_posix(),'sha256':sha(target),'bytes':target.stat().st_size})
        licenseText=raw+'\n'+lic['url']+'\n\n'+credit+'\n\nOrigen: '+acquisition['pageUrl']+'\nPaquete: '+version+'\nCambios: '+changes+'\n'
        if not kenney:licenseText+='Las adaptaciones se distribuyen bajo CC BY-SA 4.0. Se conserva el OBJ y la textura fuente.\n'
        (folder/'LICENSE.txt').write_text(licenseText,encoding='utf-8')
        with zipfile.ZipFile(folder/'originals.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
            for file in originalRecords:archive.write(ROOT/file['file'],(ROOT/file['file']).relative_to(folder).as_posix())
            archive.write(folder/'LICENSE.txt','LICENSE.txt')
        source={'Licence':raw,'Attribution':credit,'Creator':{'Username':author},'Title':item['title'],'source':evidence,'member':item['member'],'originalFiles':originalRecords}
        save(folder/'source.json',source)
        record={'id':mid,'assetId':providerId+':'+version.split(' ')[0].lower()+'/'+Path(item['member']).stem,'providerId':providerId,'provider':provider,'title':item['title'],'titleOriginal':Path(item['member']).stem,'author':author,'authorUrl':'https://kenney.nl' if kenney else 'https://opengameart.org/users/elegant-crow','sourceUrl':acquisition['pageUrl'],'metadataUrl':None,'downloadUrl':acquisition['downloadUrl'],'thumbnailUrl':None,'description':'Recurso estilizado de '+version+'. '+('Sirve para ilustración; el perfil y el paso requieren validación antes de simular un mecanismo.' if not kenney else 'Escala y precisión educativa por revisar para cada actividad.'),'category':'Agriculture' if 'nature' in pack or 'food' in pack else 'Architecture' if 'buildings' in pack else 'Mechanics','tags':item['tags'],'areas':item['areas'],'queries':[],'subjects':sorted({s for a in plan['areas'] if a['id'] in item['areas'] for s in a['subjects']}),'products':['code-studio','socrates'],'licenseRaw':raw,'license':lic,'attribution':credit,'modifications':changes,'file':folder.relative_to(ROOT).as_posix()+'/model.glb','sourceMetadataFile':folder.relative_to(ROOT).as_posix()+'/source.json','originalDownload':folder.relative_to(ROOT).as_posix()+'/originals.zip','bytes':len(data),'sha256':sha(glb),'apiTriangleCount':None,'apiAnimated':None,'gltf':gltf,'retrievedAt':acquisition['retrievedAt'],'reviewStatus':'pending','educationalReview':'Recurso visual revisado; asignación curricular y exactitud científica o mecánica requieren revisión docente.','reviewFlags':['stylized-educational-model']+([] if kenney else ['gear-mechanics-review']),'unfulfilledQueries':[],'provenance':{'pack':version,'sourceMember':item['member'],'originalFiles':originalRecords,'originalDownloadSha256':sha(folder/'originals.zip'),'archiveSha256':acquisition['sha256'],'licenseEvidence':(sourceFolder/'License.txt').relative_to(ROOT).as_posix(),'conversionTool':'Blender '+review['blenderVersion'],'dimensionsBlender':review['dimensionsBlender'],'reimportDimensionsBlender':review['reimport']['dimensionsBlender'],'scaleChange':False,'geometryFingerprint':comparison['fingerprint']},'qa':{'rights':'PASS','technical':'PASS','visual':'PASS','educational':'NOT_RUN','reviewImages':reviewed}}
        save(folder/'metadata.json',record)
        save(sources/'review'/(mid+'.json'),review)
        target=ROOT/'gallery/thumbnails'/(mid+'.webp');Image.open(result/'reimport-three-quarter.png').convert('RGB').save(target,'WEBP',quality=90)
        dependencies['thumbnails'].append({'id':mid,'file':target.relative_to(ROOT).as_posix(),'url':None,'generatedFrom':record['sha256'],'sha256':sha(target),'modelLicense':raw,'method':'Blender CPU render; clean GLB reimport','attribution':credit})
    save(ROOT/'gallery/dependencies.json',dependencies)
    report={'schemaVersion':1,'batch':'kenney-oga-20261022','added':len(items),'modelIds':[i['id'] for i in items],'duplicateCheck':dedup,'visualReview':visual,'held':[{'id':'oga-ant-ant','result':'FAIL','reason':'Three conversion attempts did not pass dimension checks; no catalog promotion.'}],'unchangedOriginalFiles':len(read(run/'original-inventory.json'))}
    save(ROOT/'enrichment/reports/kenney-oga-20261022.json',report)
    print(json.dumps({'added':len(items),'held':1}))
if __name__=='__main__':promote(Path(sys.argv[1]))
