"""CPU source/reimport QA for explicitly selected static material display variants.

Run in Blender with --background --factory-startup --disable-autoexec --threads 2,
then -- RUN --calibrated-lighting. RUN/selection.json contains native catalog rows.
Native files are immutable; derivatives remain in staging pending visual approval.
"""
import bpy,json,sys,os,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import review_institutions as reference
run=Path(sys.argv[sys.argv.index('--')+1]);root=Path(__file__).resolve().parents[1]
scope={name:getattr(reference,name) for name in ['import_model','geometry','render']}
def world_points():
    graph=bpy.context.evaluated_depsgraph_get()
    return [o.matrix_world @ vertex.co for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render for vertex in o.evaluated_get(graph).data.vertices]

if '--geometry-only' in sys.argv:
    from mathutils.kdtree import KDTree
    for model in json.loads((run/'selection.json').read_text(encoding='utf-8')):
        folder=run/'prepared'/model['id'];native=root/model['file'];display=folder/'display.glb'
        bpy.ops.wm.read_factory_settings(use_empty=True);reference.import_model(native);_,lo,hi,source_stats=reference.geometry();original=world_points()
        bpy.ops.wm.read_factory_settings(use_empty=True);reference.import_model(display);_,rlo,rhi,display_stats=reference.geometry();converted=world_points()
        tolerance=max(max(hi-lo)*1e-5,1e-6);distances=[]
        for queries,targets in [(original,converted),(converted,original)]:
            tree=KDTree(len(targets))
            for i,point in enumerate(targets):tree.insert(point,i)
            tree.balance();distances.append(max(tree.find(point)[2] for point in queries))
        assert max(distances)<=tolerance, (model['id'],distances,tolerance)
        assert source_stats['polygons']==display_stats['polygons'] and source_stats['meshObjects']==display_stats['meshObjects']
        report={'result':'PASS','id':model['id'],'sourceSha256':hashlib.sha256(native.read_bytes()).hexdigest(),'displaySha256':hashlib.sha256(display.read_bytes()).hexdigest(),'sourceVertices':len(original),'displayVertices':len(converted),'polygons':source_stats['polygons'],'meshObjects':source_stats['meshObjects'],'maxNearestVertexDistances':distances,'absoluteTolerance':tolerance,'method':'Bidirectional nearest world-space vertex distance, preserved polygon and object counts; accounts for floating-point serialization and split vertices.'}
        (folder/'geometry-comparison.json').write_text(json.dumps(report,indent=2)+'\n');print('COMPAT_GEOMETRY',model['id'],max(distances),tolerance,flush=True)
    sys.stdout.flush();os._exit(0)

rows=json.loads((run/'selection.json').read_text(encoding='utf-8'));results=[]
for model in rows:
 assert not model['gltf']['animated'] and not model['gltf']['rigged'], 'Static-only display conversion'
 folder=run/'prepared'/model['id'];folder.mkdir(parents=True,exist_ok=True)
 if (folder/'review.json').exists():
  existing=json.loads((folder/'review.json').read_text(encoding='utf-8'))
  assert hashlib.sha256((root/model['file']).read_bytes()).hexdigest()==existing['originalSha256']
  assert hashlib.sha256((folder/'display.glb').read_bytes()).hexdigest()==existing['displaySha256']
  results.append(existing);continue
 native=root/model['file'];before=hashlib.sha256(native.read_bytes()).hexdigest();assert before==model['sha256']
 bpy.ops.wm.read_factory_settings(use_empty=True);scope['import_model'](native);_,lo,hi,stats=scope['geometry']()
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'source-review.blend'));bpy.ops.wm.open_mainfile(filepath=str(folder/'source-review.blend'))
 for name,az,el,wire in [('source-three-quarter',35,25,False),('source-front',0,0,False),('source-side',90,0,False),('source-back',180,0,False),('source-wireframe',35,25,True)]:scope['render'](folder/(name+'.png'),az,el,wire)
 # Cameras/lights generated for review have been removed; only source objects export.
 destination=folder/'display.glb';bpy.ops.export_scene.gltf(filepath=str(destination),export_format='GLB',export_yup=True,export_animations=True)
 bpy.ops.wm.read_factory_settings(use_empty=True);scope['import_model'](destination);_,rlo,rhi,reimport=scope['geometry']();scope['render'](folder/'reimport-three-quarter.png')
 tolerance=max(max(hi-lo)*.0001,.00001);assert all(abs(a-b)<=tolerance for a,b in zip(list(lo)+list(hi),list(rlo)+list(rhi)))
 assert stats['polygons']==reimport['polygons'];assert stats['meshObjects']==reimport['meshObjects'];assert stats['materials']==reimport['materials']
 raw=destination.read_bytes();import struct;doc=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]]);assert 'KHR_materials_pbrSpecularGlossiness' not in doc.get('extensionsUsed',[])
 assert all('pbrMetallicRoughness' in m for m in doc.get('materials',[]));assert hashlib.sha256(native.read_bytes()).hexdigest()==before
 report={'id':model['id'],'originalFile':model['file'],'originalSha256':before,'displaySha256':hashlib.sha256(raw).hexdigest(),'displayBytes':len(raw),'tool':'Blender '+bpy.app.version_string,'source':stats,'reimport':reimport,'dimensionTolerance':tolerance,'nativeBytesUnchanged':True,'technical':'PASS','visual':'NOT_RUN','images':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.png')}}
 (folder/'review.json').write_text(json.dumps(report,indent=2)+'\n');results.append(report);print('COMPAT_REVIEW',model['id'],flush=True)
(run/'technical-review.json').write_text(json.dumps(results,indent=2)+'\n');sys.stdout.flush();os._exit(0)
