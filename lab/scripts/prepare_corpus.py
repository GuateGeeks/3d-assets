"""Freeze a corpus mesh in bind/rest pose, preserving materials and provenance."""
import argparse, hashlib, json, os, sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix
ROOT = Path(__file__).resolve().parents[2]
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--asset',choices=['human','quadruped'],required=True);p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args()
 a.run_dir=a.run_dir.resolve()
 if not a.run_dir.is_relative_to((ROOT/'lab/.local/runs').resolve()) or not a.run_dir.is_dir():p.error('Preparation run must exist inside lab/.local/runs')
 spec=next(x for x in json.loads((ROOT/'lab/corpus.json').read_text())['assets'] if x['id']==a.asset)
 meta=json.loads((ROOT/'models'/spec['sourceId']/'metadata.json').read_text());source=ROOT/meta['file']
 if digest(source)!=meta['sha256']: raise ValueError('Original hash changed')
 base=ROOT/'lab/.local/corpus'/a.asset;base.mkdir(parents=True,exist_ok=True)
 out=base/a.run_dir.name;out.mkdir(exist_ok=False)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source))
 mesh=bpy.data.objects[spec['mesh']];rig=next(m.object for m in mesh.modifiers if m.type=='ARMATURE')
 rig.animation_data_clear()
 for bone in rig.pose.bones: bone.matrix_basis.identity()
 rig.data.pose_position='REST';bpy.context.view_layer.update()
 # Restrict to the actual source mesh: glTF importer helper Icosphere is not source content.
 points=[mesh.matrix_world@v.co for v in mesh.data.vertices]
 lo=Vector(tuple(min(v[i] for v in points) for i in range(3)));hi=Vector(tuple(max(v[i] for v in points) for i in range(3)))
 factor=2.0/max(hi-lo);center=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
 normalization=Matrix.Scale(factor,4)@Matrix.Translation(-center)
 # Normalize the entire control hierarchy once, before exporting either variant.
 for obj in list(bpy.context.scene.objects):
  if obj.parent is None: obj.matrix_world=normalization@obj.matrix_world
 bpy.context.view_layer.update()
 rig.data.pose_position='POSE'
 bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);rig.select_set(True)
 bpy.ops.export_scene.gltf(filepath=str(out/'control.glb'),export_format='GLB',use_selection=True,export_animations=False,export_extras=False)
 # Bake world-space bind geometry; remove all skinning and source actions from prepared input.
 deps=bpy.context.evaluated_depsgraph_get();evaluated=mesh.evaluated_get(deps)
 data=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=deps);data.transform(mesh.matrix_world)
 prepared=bpy.data.objects.new('prepared-'+a.asset,data);bpy.context.collection.objects.link(prepared)
 bpy.ops.object.select_all(action='DESELECT');prepared.select_set(True);bpy.context.view_layer.objects.active=prepared
 bpy.ops.export_scene.gltf(filepath=str(out/'prepared.glb'),export_format='GLB',use_selection=True,export_animations=False)
 data.calc_loop_triangles()
 if not data.vertices or any(not __import__('math').isfinite(c) for v in data.vertices for c in v.co): raise ValueError('Invalid geometry')
 report={'schemaVersion':1,'asset':a.asset,'label':spec['label'],'sourceId':spec['sourceId'],'sourceSha256':meta['sha256'],'sourceFile':meta['file'],'sourceUrl':meta['sourceUrl'],'attribution':meta['attribution'],'license':meta['license'],'reason':spec['reason'],'modifications':['rest/bind pose, source actions removed','source rig removed from inference input; retained in control','uniform normalization: longest dimension 2 m, centered XY, ground Z=0','materials preserved; no decimation or remeshing'],'normalization':{'scale':factor,'sourceTranslation':list(-center),'matrix':[list(row) for row in normalization]},'vertices':len(data.vertices),'triangles':len(data.loop_triangles),'materials':len(data.materials),'prepared':{'file':str((out/'prepared.glb').relative_to(ROOT)),'sha256':digest(out/'prepared.glb')},'control':{'file':str((out/'control.glb').relative_to(ROOT)),'sha256':digest(out/'control.glb')},'reviewStatus':'pending'}
 payload=json.dumps(report,indent=2,ensure_ascii=False)+'\n'
 (out/'prepared.json').write_text(payload);(a.run_dir/('prepared-'+a.asset+'.json')).write_text(payload)
 temporary=base/'prepared.json.partial';temporary.write_text(payload);os.replace(temporary,base/'prepared.json')
 (out/'LICENSE.txt').write_text(meta['attribution']+'\nModificaciones: '+'; '.join(report['modifications'])+'\n')
 print(json.dumps(report,ensure_ascii=False),flush=True);return 0
if __name__=='__main__':
 try: code=main()
 except Exception:
  import traceback;traceback.print_exc();code=1
 sys.stdout.flush();sys.stderr.flush();os._exit(code)
