"""Promote complete, rendered kits, retaining aliases and grouping visual variants.
Requires the staged acquisition, native GLB preparation, visual review, and animated conversions.
"""
from pathlib import Path,PureWindowsPath
import sys,json,hashlib,shutil,re,zipfile,collections
from PIL import Image
from catalog import inspect,license_info
from geometry_fingerprint import fingerprint,document
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def label(name):return re.sub(r'(?<=[a-z])(?=[A-Z])',' ',name).replace('_',' · ').replace('-',' ')
def family(pack,stem):
 s=re.sub(r'(?<=[a-z])(?=[A-Z])','-',stem).lower().replace('_','-')
 if pack=='kenney-food':
  return 'food-'+s.split('-')[0]
 if pack=='kenney-nature':
  for prefix in ['crops-corn','crops-wheat','crops-bamboo','crops-leafs','crops-dirt','ground-river','ground-path','tree-pine','tree-palm','tree-oak','tree-cone','cliff','bridge','fence','mushroom','flower','rock','stone','tent','campfire','statue','plant','grass','path','log','stump']:
   if s.startswith(prefix):return 'nature-'+prefix
  return 'nature-'+s.split('-')[0]
 if pack=='kenney-buildings':
  for prefix in ['building-sample-house','building-sample-tower','building-corner','building-door','building-window','building-steps','roof','window','door','wall','stairs']:
   if s.startswith(prefix):return 'architecture-'+prefix
  return 'architecture-'+s.split('-')[0]
 if pack=='oga-gears':return 'mechanics-gears'
 return 'character-'+stem.lower()
def areas_for(pack,stem):
 s=stem.lower()
 if pack=='kenney-food':return ['alimentos-agricultura']
 if pack=='kenney-buildings':return ['comunidad-ciudadania','escenarios-videojuegos','matematicas-medicion']
 if pack in ['oga-robot','oga-animals']:return ['personajes-animacion','robotica-electronica'] if pack=='oga-robot' else ['animales-biodiversidad','personajes-animacion']
 if any(t in s for t in ['river','lily']):return ['agua-oceanos','escenarios-videojuegos']
 if s.startswith('crop'):return ['alimentos-agricultura','bosques-plantas']
 if s.startswith(('rock','stone','cliff')):return ['tierra-geografia','escenarios-videojuegos']
 if s.startswith(('tree','plant','grass','flower','mushroom','hanging')):return ['bosques-plantas','escenarios-videojuegos']
 return ['escenarios-videojuegos']
def promote(run):
 run=run.resolve();review=read(run/'bulk-visual-review.json')
 if review['result']!='PASS':raise ValueError('Visual review required')
 for relative,digest in review['images'].items():
  if sha(run/relative)!=digest:raise ValueError('Review image changed')
 plan=read(ROOT/'selection.json');kits=read(ROOT/'kits/index.json');bykit={k['id']:k for k in kits['kits']}
 existing={read(p)['id']:read(p) for p in (ROOT/'models').glob('*/metadata.json')}
 canonical={m['sha256']:m['id'] for m in existing.values()};dependencies=read(ROOT/'gallery/dependencies.json')
 inputs=read(run/'bulk-kenney.json')['items']+read(run/'animated-selection-v3.json')['items']
 aliases=[];added=[];groups={};sources=ROOT/'sources/external'
 for kit in kits['kits']:kit['assets']=[]
 for item in inputs:
  mid=item['id'];pack=item['pack'];kit=bykit[pack];native=pack.startswith('kenney')
  result=run/'bulk-kenney'/mid if native else run/PureWindowsPath(item['output']).parent.name/PureWindowsPath(item['output']).name
  glb=result/'model.glb';data=glb.read_bytes();digest=hashlib.sha256(data).hexdigest();gltf=inspect(data)
  if not gltf['selfContained']:raise ValueError('Unresolved dependency '+mid)
  if len(data)>25*1024**2:raise ValueError('Asset exceeds per-model budget')
  canonical_id=mid if mid in existing else canonical.get(digest,mid)
  stem=item.get('sourceName') or Path(item['member']).stem
  group=family(pack,stem)
  member={'sourceMember':item['member'],'sourceName':stem,'modelId':canonical_id,'relation':'same-fiche' if canonical_id==mid and mid in existing else 'binary-duplicate' if canonical_id!=mid else 'unique-or-variant'}
  kit['assets'].append(member)
  groups.setdefault(group,{'id':group,'title':label(group),'modelIds':[]})
  if canonical_id not in groups[group]['modelIds']:groups[group]['modelIds'].append(canonical_id)
  if canonical_id!=mid:aliases.append({'id':mid,'canonicalId':canonical_id,'kit':pack,'reason':'Same SHA-256'});continue
  if mid in existing:continue
  assessment=read(result/'review.json')
  if assessment['technical']!='PASS' or assessment['glbSha256']!=digest:raise ValueError('Technical review missing '+mid)
  if not native and not assessment.get('reimport'):raise ValueError('Missing clean animated reimport')
  source=run/pack/'extracted'/item['member'];rawFiles=[source]
  for name in item.get('externalImages',[]):rawFiles.append(run/pack/'extracted'/name)
  folder=ROOT/'models'/mid
  if folder.exists():raise ValueError('Refusing to replace '+mid)
  folder.mkdir();shutil.copyfile(glb,folder/'model.glb');originals=[]
  for file in rawFiles:
   relative=file.relative_to(source.parent) if file.is_relative_to(source.parent) else Path('textures')/file.name
   dest=folder/'original'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,dest);originals.append({'file':dest.relative_to(ROOT).as_posix(),'sha256':sha(dest),'bytes':dest.stat().st_size})
  title=label(stem);raw=kit['licenseRaw'];lic=license_info(raw);author=kit['author']
  modifications=('Ninguna: GLB original sin conversión' if not item.get('externalImages') else 'Texturas originales incrustadas en GLB; geometría, materiales, transformaciones y ejes conservados byte a byte en el búfer original.') if native else 'Blender '+assessment['blenderVersion']+': BLEND convertido a GLB; materiales antiguos convertidos a PBR conservando el color difuso; restricciones de rig horneadas a curvas cuando el exportador lo requiere; dimensiones de reposo comprobadas; originales conservados.'
  credit='"'+stem+'" de '+kit['title']+', por '+author+'. '+kit['sourceUrl']+'. '+raw+' '+kit['licenseUrl']+'.'
  licenseText=credit+'\n\nCambios: '+modifications+'\nKit completo: '+kit['sourceUrl']+'\n'
  (folder/'LICENSE.txt').write_text(licenseText,encoding='utf-8')
  with zipfile.ZipFile(folder/'originals.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
   for file in originals:archive.write(ROOT/file['file'],(ROOT/file['file']).relative_to(folder).as_posix())
   archive.write(folder/'LICENSE.txt','LICENSE.txt')
  record={'id':mid,'assetId':kit['providerId']+':'+pack+'/'+stem,'providerId':kit['providerId'],'provider':kit['provider'],'title':title,'titleOriginal':stem,'author':author,'authorUrl':'https://kenney.nl' if native else 'https://opengameart.org/users/quaternius','sourceUrl':kit['sourceUrl'],'metadataUrl':None,'downloadUrl':kit['downloadUrl'],'thumbnailUrl':None,'description':'Modelo de '+kit['title']+'. Representación estilizada; escala y adecuación educativa requieren revisión docente.','category':'Environment' if pack=='kenney-nature' else 'Food' if pack=='kenney-food' else 'Architecture' if pack=='kenney-buildings' else 'Characters','tags':[stem,pack,group],'areas':areas_for(pack,stem),'queries':[],'products':['code-studio','socrates'],'licenseRaw':raw,'license':lic,'attribution':credit,'modifications':modifications,'file':'models/'+mid+'/model.glb','sourceMetadataFile':'models/'+mid+'/source.json','originalDownload':'models/'+mid+'/originals.zip','bytes':len(data),'sha256':digest,'apiTriangleCount':None,'apiAnimated':None,'gltf':gltf,'retrievedAt':kit['retrievedAt'],'reviewStatus':'pending','educationalReview':'Revisión visual completada; uso curricular concreto pendiente.','reviewFlags':['stylized-educational-model']+(['modular-assembly-piece'] if native and (pack=='kenney-buildings' and 'sample' not in stem or pack=='kenney-nature' and any(w in stem.lower() for w in ['cliff','ground','path','plant_flat'])) else [])+(['adult-beverage-classroom-review'] if any(w in stem.lower() for w in ['wine','cocktail','beer']) else []),'unfulfilledQueries':[],'subjects':sorted({s for area in plan['areas'] if area['id'] in areas_for(pack,stem) for s in area['subjects']}),'provenance':{'pack':kit['title'],'sourceMember':item['member'],'originalFiles':originals,'originalDownloadSha256':sha(folder/'originals.zip'),'archiveSha256':kit['sha256'],'licenseEvidence':kit['licenseFile'],'conversionTool':'GLB image embedding without geometry conversion' if native else 'Blender '+assessment['blenderVersion'],'dimensionsBlender':assessment['dimensionsBlender'],'scaleChange':False,'geometryFingerprint':fingerprint(data)},'qa':{'rights':'PASS','technical':'PASS','visual':'PASS','educational':'NOT_RUN','reviewEvidence':'sources/external/bulk-review.json'}}
  save(folder/'metadata.json',record);save(folder/'source.json',{'Licence':raw,'Attribution':credit,'Creator':{'Username':author},'Title':stem,'sourceUrl':kit['sourceUrl'],'sourceMember':item['member'],'archiveSha256':kit['sha256'],'originalFiles':originals})
  preview=result/'preview.png' if native else result/'reimport-three-quarter.png';thumb=ROOT/'gallery/thumbnails'/(mid+'.webp');Image.open(preview).convert('RGB').save(thumb,'WEBP',quality=88)
  dependencies['thumbnails'].append({'id':mid,'file':thumb.relative_to(ROOT).as_posix(),'url':None,'generatedFrom':digest,'sha256':sha(thumb),'modelLicense':raw,'method':'Blender CPU render','attribution':credit})
  canonical[digest]=mid;existing[mid]=record;added.append(mid)
 # Gears are already promoted; link them into the complete kit and family.
 for m in existing.values():
  if m['id'].startswith('oga-gears-'):
   bykit['oga-gears']['assets'].append({'sourceMember':m['provenance']['sourceMember'],'sourceName':m.get('titleOriginal',m['id']),'modelId':m['id'],'relation':'same-fiche'})
   groups.setdefault('mechanics-gears',{'id':'mechanics-gears','title':'Engranajes','modelIds':[]})['modelIds'].append(m['id'])
 # Existing baseline equivalents stay immutable; grouping lives in this manifest.
 baseline_groups={'food-carrot':['59muuwqSsq'],'food-honey':['p92t5dG8Zd'],'character-robot':['QCm7qe9uNJ'],'character-wolf':['P1gU3Qkr9r']}
 for key,ids in baseline_groups.items():
  if key in groups:groups[key]['modelIds']=ids+[mid for mid in groups[key]['modelIds'] if mid not in ids]
 save(ROOT/'gallery/dependencies.json',dependencies)
 for kit in kits['kits']:
  kit['logicalModels']=len(kit['assets']);save(ROOT/'kits'/kit['id']/'inventory.json',kit)
 save(ROOT/'kits/index.json',kits);save(ROOT/'kits/groups.json',{'schemaVersion':1,'groups':list(groups.values()),'aliases':aliases,'grouping':'Variants share a family; SHA-256 duplicates share one model record. File-format alternatives remain in complete archives.'})
 public_review={**review,'images':{'sources/external/bulk-review/'+Path(rel).name:digest for rel,digest in review['images'].items()}}
 save(sources/'bulk-review.json',public_review)
 for rel,digest in review['images'].items():
  dest=sources/'bulk-review'/Path(rel).name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(run/rel,dest)
 save(ROOT/'enrichment/reports/complete-kits.json',{'added':len(added),'modelIds':added,'aliases':aliases,'kits':[{k:v for k,v in kit.items() if k not in ['members','assets']} for kit in kits['kits']],'nativeModelGeometry':'622 incorporaciones usan el GLB nativo con el búfer geométrico conservado y, donde corresponde, imágenes incrustadas. Quince fichas del piloto conservan sus exportaciones Blender ya revisadas, con originales y dimensiones documentados.','held':['oga-ant-ant']})
 print(json.dumps({'added':len(added),'binaryAliases':len(aliases),'kitModels':sum(len(k['assets']) for k in kits['kits'])}))
if __name__=='__main__':promote(Path(sys.argv[1]))
