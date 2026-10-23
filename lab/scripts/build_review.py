"""Bake diagnostic still poses (no animation clips), with equivalent original/UniRig joints."""
import argparse, hashlib, json, math, os, shutil, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector
ROOT=Path(__file__).resolve().parents[2]
LAB=ROOT/'lab';REVIEW=LAB/'.local/review'
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
 temporary=path.with_name(path.name+'.partial');temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');os.replace(temporary,path)
def load(path):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path))
 rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
 rig.animation_data_clear()
 for bone in rig.pose.bones: bone.matrix_basis.identity()
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.find_armature()==rig]
 if not meshes: raise ValueError('No deformable meshes')
 return rig,meshes
def bone_inventory(rig):
 return [{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(rig.matrix_world@b.head_local),'tail':list(rig.matrix_world@b.tail_local)} for b in rig.data.bones]
def baked(meshes):
 deps=bpy.context.evaluated_depsgraph_get();objects=[]
 for mesh in meshes:
  data=bpy.data.meshes.new_from_object(mesh.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps);data.transform(mesh.matrix_world)
  if any(not math.isfinite(c) for v in data.vertices for c in v.co): raise ValueError('Non-finite posed vertex')
  obj=bpy.data.objects.new('diagnostic-'+mesh.name,data);bpy.context.collection.objects.link(obj);objects.append(obj)
 return objects
def export(objects,path):
 bpy.ops.object.select_all(action='DESELECT')
 for obj in objects: obj.select_set(True)
 bpy.context.view_layer.objects.active=objects[0]
 bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_animations=False)
 # Verify the binary glTF header and absence of clips on disk, independent of bpy state.
 import struct
 data=path.read_bytes();length,kind=struct.unpack_from('<II',data,12);doc=json.loads(data[20:20+length])
 if kind!=0x4E4F534A or doc.get('animations'): raise ValueError('Diagnostic still unexpectedly contains animation')
def skeleton_objects(rig, meshes):
 material=bpy.data.materials.new('Diagnostic skeleton');material.diffuse_color=(0.72,0.12,0.035,1);material.use_nodes=True
 bsdf=material.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=material.diffuse_color;bsdf.inputs['Emission Color'].default_value=material.diffuse_color;bsdf.inputs['Emission Strength'].default_value=0.4
 weighted_names={mesh.vertex_groups[g.group].name for mesh in meshes for vertex in mesh.data.vertices for g in vertex.groups if g.weight>1e-5}
 objects=[]
 for bone in rig.pose.bones:
  # Draw actual joint-to-joint segments; inferred glTF terminal tails are not actual joints.
  if bone.parent is None or bone.name not in weighted_names: continue
  start=rig.matrix_world@bone.parent.head;end=rig.matrix_world@bone.head;delta=end-start
  if delta.length<0.001:continue
  bpy.ops.mesh.primitive_cylinder_add(vertices=6,radius=0.008,depth=delta.length,location=(start+end)/2)
  obj=bpy.context.object;obj.rotation_mode='QUATERNION';obj.rotation_quaternion=delta.to_track_quat('Z','Y');obj.data.materials.append(material);objects.append(obj)
 return objects
def metrics(rest,posed):
 moves=[];ratios=[]
 for before,after in zip(rest,posed):
  for a,b in zip(before.data.vertices,after.data.vertices):moves.append((b.co-a.co).length)
  for edge in before.data.edges:
   i,j=edge.vertices;l0=(before.data.vertices[i].co-before.data.vertices[j].co).length;l1=(after.data.vertices[i].co-after.data.vertices[j].co).length
   if l0>0.002:ratios.append(l1/l0)
 ratios.sort()
 return {'movedVertices':sum(x>1e-5 for x in moves),'maximumDisplacementMeters':max(moves,default=0),'edgeStretchP95':ratios[int((len(ratios)-1)*.95)] if ratios else None,'maximumEdgeStretch':max(ratios,default=1),'minimumEdgeRatio':min(ratios,default=1)}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--asset',choices=['human','quadruped','all'],default='all');p.add_argument('--run-dir',type=Path,required=True);args=p.parse_args()
 args.run_dir=args.run_dir.resolve()
 if not args.run_dir.is_relative_to((LAB/'.local/runs').resolve()) or not args.run_dir.is_dir():p.error('Review run must exist inside lab/.local/runs')
 REVIEW.mkdir(parents=True,exist_ok=True);(REVIEW/'assets').mkdir(exist_ok=True)
 mapping_snapshot=args.run_dir/'review-poses.json';shutil.copy2(LAB/'review-poses.json',mapping_snapshot)
 mappings=json.loads(mapping_snapshot.read_text())['assets']
 previous=json.loads((REVIEW/'manifest.json').read_text()) if (REVIEW/'manifest.json').exists() else {'schemaVersion':1,'assets':[],'files':{}}
 selected=['human','quadruped'] if args.asset=='all' else [args.asset]
 for asset_id in selected:
  run=json.loads((LAB/'reports'/('rig-'+asset_id+'.json')).read_text())
  if run['status']!='success':raise ValueError('Inference has not succeeded')
  prep=run['provenance'];candidate=ROOT/next(a['file'] for a in run['artifacts'] if a['file'].endswith('model_rigged.glb'))
  spec=mappings[asset_id]
  if digest(candidate)!=spec['candidateSha256']:raise ValueError('Pose mapping belongs to a different candidate. Inspect bones and update review-poses.json.')
  for entry in [prep['prepared'],prep['control']]:
   if digest(ROOT/entry['file'])!=entry['sha256']:raise ValueError('Prepared/control input changed')
  out=REVIEW/'assets'/asset_id/args.run_dir.name;out.mkdir(parents=True,exist_ok=False)
  new_files={}
  def register(path):
   relative=path.relative_to(REVIEW/'assets').as_posix();token=hashlib.sha256(relative.encode()).hexdigest()[:24]
   new_files[token]={'file':relative,'sha256':digest(path)};return '_lab/assets/'+token
  copied_candidate=out/'candidate.glb';shutil.copy2(candidate,copied_candidate)
  prepared=out/'prepared.glb';shutil.copy2(ROOT/prep['prepared']['file'],prepared)
  views={};pose_metrics={};inventories={};counts={}
  for variant,path in [('control',ROOT/prep['control']['file']),('candidate',candidate)]:
   rig,meshes=load(path);inventories[variant]=bone_inventory(rig);counts[variant]=len(rig.data.bones)
   # Global axis rotations are converted to the armature's coordinates (control keeps its source transform).
   bpy.context.view_layer.update();rest=baked(meshes)
   for pose in spec['poses']:
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    for instruction in pose[variant]:
     name,axis,degrees=instruction[:3]
     bone=rig.pose.bones.get(name)
     if bone is None:raise ValueError('Mapped bone missing: '+name)
     world_axis=Vector(tuple(1 if c==axis else 0 for c in 'XYZ'))
     local_axis=rig.matrix_world.to_3x3().inverted()@world_axis;local_axis.normalize()
     pivot=rig.pose.bones[instruction[3]].head.copy() if len(instruction)>3 else bone.head.copy();bone.matrix=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(degrees),4,local_axis)@Matrix.Translation(-pivot)@bone.matrix
     bpy.context.view_layer.update()
    objects=baked(meshes);m=metrics(rest,objects)
    if pose[variant] and m['movedVertices']==0:raise ValueError('Pose does not deform mesh')
    mesh_path=out/(variant+'-'+pose['id']+'.glb');export(objects,mesh_path)
    skeleton=skeleton_objects(rig,meshes)
    for obj in objects:
     for slot in obj.material_slots:
      if slot.material:
       slot.material=slot.material.copy();slot.material.diffuse_color=(*slot.material.diffuse_color[:3],.18);slot.material.blend_method='BLEND'
       if slot.material.use_nodes:
        node=slot.material.node_tree.nodes.get('Principled BSDF')
        if node:node.inputs['Alpha'].default_value=.18
    skeleton_path=out/(variant+'-'+pose['id']+'-skeleton.glb');export(objects+skeleton,skeleton_path)
    views.setdefault(pose['id'],{})[variant]={'mesh':register(mesh_path),'skeleton':register(skeleton_path)}
    pose_metrics.setdefault(pose['id'],{})[variant]=m
    for obj in objects+skeleton:bpy.data.objects.remove(obj,do_unlink=True)
   for obj in rest:bpy.data.objects.remove(obj,do_unlink=True)
  inspection=json.loads((ROOT/'lab/.local/runs'/run['runId']/'glb-inspection.json').read_text())
  gpu_peak=max((s.get('sampledDeviceMemoryMiB',{}).get('peakUsed',0) for s in run['stages']),default=0)
  item={'id':asset_id,'label':prep['label'],'runId':run['runId'],'reviewRunId':args.run_dir.name,'mappingSha256':digest(mapping_snapshot),'seconds':run['seconds'],'seed':run['seed'],'cameraOrbit':spec['cameraOrbit'],'cameraTarget':spec['cameraTarget'],'bones':counts['candidate'],'controlBones':counts['control'],'weightedVertices':inspection['weightedVertices'],'unweightedVertices':inspection['unweightedDeformableVertices'],'badWeights':inspection['nonNormalizedVertices'],'sourceSha256':prep['sourceSha256'],'candidateSha256':digest(candidate),'candidateUrl':register(copied_candidate),'preparedUrl':register(prepared),'attribution':prep['attribution'],'sourceUrl':prep['sourceUrl'],'modifications':prep['modifications']+['UniRig: generated skeleton and skinning, seed 42','diagnostic poses baked to static GLB; no animation clips'],'reviewStatus':'Pendiente de dictamen visual','observations':['Pesos finitos y normalizados; la calidad de las deformaciones requiere revisión.','Las poses usan FK directa; los controles independientes de pie del original acompañan el giro de rodilla/codo. No se resuelve IK. El esqueleto visible omite controles sin influencia.'],'poses':[{**{k:v for k,v in pose.items() if k not in ['control','candidate']},**views[pose['id']], 'metrics':pose_metrics[pose['id']]} for pose in spec['poses']]}
  findings_path=LAB/'review-findings.json'
  findings=json.loads(findings_path.read_text()).get('assets',{}).get(asset_id) if findings_path.exists() else None
  if findings and findings['candidateSha256']==digest(candidate) and findings.get('mappingSha256')==digest(mapping_snapshot):
   item['reviewStatus']=findings['status'];item['observations']=findings['observations']+item['observations']
  report={'schemaVersion':1,'asset':asset_id,'runId':run['runId'],'reviewRunId':args.run_dir.name,'source':prep,'candidateSha256':digest(candidate),'mappingSha256':digest(mapping_snapshot),'inferenceSeconds':run['seconds'],'sampledWholeDevicePeakMiB':gpu_peak,'bones':inventories,'poseMetrics':pose_metrics,'clipsCreated':0,'visualReview':'pending','gallery':item}
  write(out/'diagnostics.json',report);write(args.run_dir/('review-'+asset_id+'.json'),report);write(LAB/'reports'/('review-'+asset_id+'.json'),report)
  previous['assets']=[x for x in previous['assets'] if x['id']!=asset_id]+[item]
  # Retain only files referenced by the current public asset entries.
  previous['files'].update(new_files)
  needed=set()
  def collect(value):
   if isinstance(value,str) and value.startswith('_lab/assets/'):needed.add(value.rsplit('/',1)[1])
   elif isinstance(value,dict):
    for v in value.values():collect(v)
   elif isinstance(value,list):
    for v in value:collect(v)
  collect(previous['assets']);previous['files']={k:v for k,v in previous['files'].items() if k in needed}
  print(asset_id+': '+str(len(spec['poses']))+' static diagnostic poses per rig; no clips',flush=True)
 write(args.run_dir/'review-manifest.json',previous)
 write(REVIEW/'manifest.json',previous)
 return 0
if __name__=='__main__':
 try:code=main()
 except Exception:
  import traceback;traceback.print_exc();code=1
 sys.stdout.flush();sys.stderr.flush();os._exit(code)
