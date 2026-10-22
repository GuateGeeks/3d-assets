"""Convert selected external assets and render CPU review evidence in an isolated process.
Run Blender with --factory-startup --disable-autoexec --background --python this.py -- selection.json.
No supplied scripts are executed. The source assets are never saved over.
"""
import bpy,sys,json,math,os,hashlib,shutil
from pathlib import Path
from mathutils import Vector
plan=Path(sys.argv[sys.argv.index('--')+1])
items=json.loads(plan.read_text(encoding='utf-8'))['items']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def geometry():
    bpy.context.view_layer.update()
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render]
    dg=bpy.context.evaluated_depsgraph_get()
    points=[o.matrix_world@v.co for o in meshes for v in o.evaluated_get(dg).data.vertices]
    lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    triangles=sum(len(o.data.polygons) for o in meshes)
    return meshes,lo,hi,{'dimensionsBlender':list(hi-lo),'meshObjects':len(meshes),'polygons':triangles,'materials':len({m.name for o in meshes for m in o.data.materials if m}),'blenderVersion':bpy.app.version_string}
def render(path,azimuth=35,elevation=25,wire=False):
    meshes,lo,hi,stats=geometry();center=(lo+hi)/2;extent=max(hi-lo)
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
    scene.render.resolution_x=320;scene.render.resolution_y=286;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    scene.view_settings.view_transform='Standard'
    world=bpy.data.worlds.new('ReviewWorld');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.94,.93,.91,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
    created=[]
    for name,offset,power in [('Key',(2,-3,4),450),('Fill',(-3,-1,2),250)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power*extent*extent;data.shape='DISK';data.size=extent*3
        ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=center+Vector(offset)*extent
        ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler();created.append(ob)
    data=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',data);scene.collection.objects.link(cam)
    a=math.radians(azimuth);e=math.radians(elevation)
    cam.location=center+Vector((math.sin(a)*math.cos(e),-math.cos(a)*math.cos(e),math.sin(e)))*extent*4
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=extent*1.5
    cam.data.clip_start=max(extent/10000,.00001);cam.data.clip_end=max(extent*100,100);scene.camera=cam
    overrides=[]
    if wire:
        for ob in meshes:
            mod=ob.modifiers.new('ReviewWireframe','WIREFRAME');mod.thickness=extent*.002;mod.use_replace=False;overrides.append((ob,mod))
    scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    for ob,mod in overrides:ob.modifiers.remove(mod)
    for ob in created+[cam]:bpy.data.objects.remove(ob,do_unlink=True)
    return stats
for item in items:
    dest=Path(item['output']);dest.mkdir(parents=True,exist_ok=True)
    if (dest/'review.json').exists():continue
    source=Path(item['input']);bpy.ops.wm.read_factory_settings(use_empty=True)
    if source.suffix=='.blend':
        bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
        for ob in list(bpy.context.scene.objects):
            if ob.type not in {'MESH','ARMATURE','EMPTY'}:bpy.data.objects.remove(ob,do_unlink=True)
        # Bone control shapes and unused source datablocks are editor helpers, not scene geometry.
        scene_objects=set(bpy.context.scene.objects)
        for ob in list(bpy.data.objects):
            if ob not in scene_objects:bpy.data.objects.remove(ob,do_unlink=True)
        # Rebuild legacy renderer-specific flat materials as explicit glTF-compatible PBR.
        for material in bpy.data.materials:
            color=tuple(material.diffuse_color)
            if material.use_nodes:
                outputs=[n for n in material.node_tree.nodes if n.type=='OUTPUT_MATERIAL']
                output=next((n for n in outputs if n.target=='CYCLES'),None) or next((n for n in outputs if n.is_active_output),None)
                if output and output.inputs['Surface'].links:
                    original_shader=output.inputs['Surface'].links[0].from_node
                    socket=original_shader.inputs.get('Color') or original_shader.inputs.get('Base Color')
                    if socket:
                        if socket.is_linked:raise ValueError('Linked legacy color requires explicit texture conversion')
                        color=tuple(socket.default_value)
            material.use_nodes=True;material.node_tree.nodes.clear()
            shader=material.node_tree.nodes.new('ShaderNodeBsdfPrincipled');shader.inputs['Base Color'].default_value=color;shader.inputs['Roughness'].default_value=.65
            output=material.node_tree.nodes.new('ShaderNodeOutputMaterial');material.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface'])
        bpy.context.scene.frame_set(1)
    elif source.suffix=='.obj':
        bpy.ops.wm.obj_import(filepath=str(source))
        tex=source.parents[1]/'textures_512x512'/(source.stem+'_tex_512.png')
        mat=bpy.data.materials.new('Gear material');mat.use_nodes=True
        shader=mat.node_tree.nodes.get('Principled BSDF');image=mat.node_tree.nodes.new('ShaderNodeTexImage');image.image=bpy.data.images.load(str(tex));image.image.pack()
        mat.node_tree.links.new(image.outputs['Color'],shader.inputs['Base Color'])
        for ob in bpy.context.scene.objects:
            if ob.type=='MESH':ob.data.materials.clear();ob.data.materials.append(mat)
    else:bpy.ops.import_scene.gltf(filepath=str(source))
    if item.get('restReview'):
        for ob in bpy.context.scene.objects:
            if ob.type=='ARMATURE':ob.data.pose_position='REST'
    meshes,lo,hi,stats=geometry()
    stats['sourceSha256']=digest(source);stats['sourceFile']=item['member'];stats['id']=item['id']
    stats['actions']=[a.name for a in bpy.data.actions]
    # Keep the editable conversion scene independently of the unchanged source.
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/'conversion.blend'))
    views=[('source-three-quarter',35,25,False)]
    if source.suffix!='.glb' or item.get('forceConvert'):views += [('source-front',0,0,False),('source-side',90,0,False),('source-back',180,0,False),('source-wireframe',35,25,True)]
    for name,a,e,wire in views:render(dest/(name+'.png'),a,e,wire)
    glb=dest/'model.glb'
    if source.suffix=='.glb' and not item.get('forceConvert'):shutil.copyfile(source,glb)
    else:
        bpy.ops.object.select_all(action='DESELECT')
        for ob in list(bpy.context.scene.objects):
            if ob.type in {'MESH','ARMATURE','EMPTY'}:ob.select_set(True)
        props=bpy.ops.export_scene.gltf.get_rna_type().properties
        options={'filepath':str(glb),'export_format':'GLB','use_selection':True,'export_animations':True,'export_skins':True,'export_yup':True}
        if 'export_animation_mode' in props:options['export_animation_mode']='ACTIONS'
        if 'export_all_influences' in props:options['export_all_influences']=True
        for ob in bpy.context.scene.objects:
            if ob.type=='ARMATURE':ob.data.pose_position='POSE'
        bpy.ops.export_scene.gltf(**options)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(glb))
    if item.get('restReview'):
        for ob in bpy.context.scene.objects:
            if ob.type=='ARMATURE':ob.data.pose_position='REST'
    import struct
    raw=glb.read_bytes();length=struct.unpack_from('<I',raw,12)[0];gdoc=json.loads(raw[20:20+length]);allowed={n.get('name') for n in gdoc['nodes'] if 'mesh' in n}
    for ob in list(bpy.context.scene.objects):
        if ob.type=='MESH' and ob.name not in allowed:bpy.data.objects.remove(ob,do_unlink=True)
    _,rlo,rhi,reimport=geometry()
    stats['reimport']=reimport
    dims=stats['dimensionsBlender'];rdims=reimport['dimensionsBlender']
    stats['dimensionTolerance']=max(max(dims)*.0001,1e-5)
    if any(abs(a-b)>stats['dimensionTolerance'] for a,b in zip(dims,rdims)):raise ValueError('Dimensions changed '+item['id'])
    render(dest/'reimport-three-quarter.png')
    import struct
    glbdata=glb.read_bytes();n=struct.unpack_from('<I',glbdata,12)[0];doc=json.loads(glbdata[20:20+n])
    external=[v['uri'] for group in ['images','buffers'] for v in doc.get(group,[]) if v.get('uri') and not v['uri'].startswith('data:')]
    if external:raise ValueError('External GLB dependencies: '+str(external))
    stats['selfContained']=True
    stats['glbSha256']=digest(glb)
    stats['images']={p.name:digest(p) for p in dest.glob('*.png')}
    stats['technical']='PASS';stats['visual']='NOT_RUN'
    (dest/'review.json').write_text(json.dumps(stats,indent=2)+'\n',encoding='utf-8')
    print('ASSET_REVIEW '+item['id'],flush=True)
print('EXTERNAL_CONVERSION_COMPLETE',flush=True)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
