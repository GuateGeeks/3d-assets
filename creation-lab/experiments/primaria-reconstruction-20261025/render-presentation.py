"""Render verified geometry for visual comparison; never overwrite source or previous evidence.
Blender --background --python render-presentation.py -- --source path/source.blend --output new-folder
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    source=Path(args.source).resolve()
    out=Path(args.output).resolve()
    out.mkdir(parents=True,exist_ok=False)
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    scene=bpy.context.scene
    meshes=[o for o in scene.objects if o.type=='MESH']
    points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
    lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center=(lo+hi)/2
    height=hi.z-lo.z
    for obj in list(scene.objects):
        if obj.type in {'LIGHT','CAMERA'}:
            bpy.data.objects.remove(obj,do_unlink=True)
    world=bpy.data.worlds.new('Neutral paper studio');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.86,.86,.86,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.40
    scene.world=world
    for name,position,energy,size in [('Key',(-1.4,-2.3,2.6),115,2.0),('Fill',(1.9,-1.0,1.3),38,2.3),('Rim',(.2,1.6,2.1),65,1.8)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=energy*height*height;data.size=size*height
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
        obj.location=center+Vector(position)*height;aim(obj,center)
    floor_mat=bpy.data.materials.new('Presentation floor');floor_mat.use_nodes=True
    floor_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.83,.815,.86,1)
    floor_mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=1
    bpy.ops.mesh.primitive_plane_add(size=200*height,location=(0,0,lo.z-.001*height))
    floor=bpy.context.object;floor.name='PRESENTATION ONLY ground';floor.data.materials.append(floor_mat)
    camera_data=bpy.data.cameras.new('Comparison camera');camera=bpy.data.objects.new('Comparison camera',camera_data)
    scene.collection.objects.link(camera);scene.camera=camera
    camera_data.type='ORTHO';camera_data.ortho_scale=height*1.18
    camera_data.clip_start=height*.001;camera_data.clip_end=height*500
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
    scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.render.resolution_x=960;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=-.3
    scene.view_settings.gamma=1
    views={'front':(0,-4,0),'side':(4,0,0),'back':(0,4,0),'three-quarter':(2.8,-4,.4)}
    evidence=[]
    for name,direction in views.items():
        camera.location=center+Vector(direction)*height;aim(camera,center)
        path=out/(name+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        evidence.append({'view':name,'sha256':sha(path),'file':path.name,'cameraBlender':list(camera.location)})
    # Clay changes only temporary presentation materials, not saved source or GLB.
    clay=bpy.data.materials.new('Neutral silhouette clay');clay.use_nodes=True
    clay.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.50,.50,.50,1)
    clay.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=1
    for obj in meshes:
        obj.data.materials.clear();obj.data.materials.append(clay)
        for polygon in obj.data.polygons:polygon.material_index=0
    for name in ['front','three-quarter']:
        camera.location=center+Vector(views[name])*height;aim(camera,center)
        path=out/('clay-'+name+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        evidence.append({'view':'clay-'+name,'sha256':sha(path),'file':path.name})
    receipt={'source':str(source),'sourceSha256':sha(source),'blender':bpy.app.version_string,
        'geometryModification':'NONE','sourceWritten':False,'assetBounds':[list(lo),list(hi)],
        'viewTransform':'Standard','exposure':-.3,'engine':'Cycles CPU','samples':24,
        'referenceComparison':'True orthographic front/back/side. Three-quarter has a slight elevation. Supplemental presentation, does not replace workflow QA.',
        'images':evidence}
    (out/'presentation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','output':str(out),'images':len(evidence)}))
main()
