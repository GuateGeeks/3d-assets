"""Render and inspect complete native-GLB kits on CPU without resaving source assets."""
import bpy,sys,json,math,os,hashlib
from pathlib import Path
from mathutils import Vector
run=Path(sys.argv[sys.argv.index('--')+1]);plan=json.loads((run/'bulk-kenney.json').read_text())
for number,item in enumerate(plan['items'],1):
 folder=run/'bulk-kenney'/item['id']
 if item['reuse'] or (folder/'review.json').exists():continue
 try:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(folder/'model.glb'))
  bpy.context.view_layer.update();meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render]
  points=[o.matrix_world@Vector(v) for o in meshes for v in o.bound_box]
  lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
  center=(lo+hi)/2;extent=max(hi-lo)
  if not extent or not all(math.isfinite(v) for p in points for v in p):raise ValueError('Invalid geometry')
  scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=4
  scene.render.resolution_x=256;scene.render.resolution_y=228;scene.render.resolution_percentage=100
  scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False;scene.view_settings.view_transform='Standard'
  world=bpy.data.worlds.new('ReviewWorld');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.9,.89,.87,1);world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
  for name,offset,power in [('Key',(2,-3,4),450),('Fill',(-3,-1,2),250)]:
   data=bpy.data.lights.new(name,'AREA');data.energy=power*extent*extent;data.size=extent*3
   ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=center+Vector(offset)*extent;ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
  data=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',data);scene.collection.objects.link(cam)
  cam.location=center+Vector((.52,-.74,.42))*extent*4;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=extent*1.5;cam.data.clip_start=max(extent/10000,.00001);cam.data.clip_end=max(extent*100,100);scene.camera=cam
  scene.render.filepath=str(folder/'preview.png');bpy.ops.render.render(write_still=True)
  report={'technical':'PASS','visual':'NOT_RUN','id':item['id'],'dimensionsBlender':list(hi-lo),'blenderVersion':bpy.app.version_string,'meshObjects':len(meshes),'glbSha256':hashlib.sha256((folder/'model.glb').read_bytes()).hexdigest(),'previewSha256':hashlib.sha256((folder/'preview.png').read_bytes()).hexdigest(),'scope':'Native GLB geometry preserved; clean Blender import and CPU render. Educational use remains pending.'}
  (folder/'review.json').write_text(json.dumps(report,indent=2)+'\n');print('BULK_PROGRESS '+str(number)+'/'+str(len(plan['items']))+' '+item['id'],flush=True)
 except Exception as e:
  (folder/'failed.json').write_text(json.dumps({'id':item['id'],'technical':'FAIL','reason':str(e)})+'\n');print('BULK_FAILED '+item['id']+' '+str(e),flush=True)
print('BULK_COMPLETE',flush=True);sys.stdout.flush();sys.stderr.flush();os._exit(0)
