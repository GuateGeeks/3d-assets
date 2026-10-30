"""CPU bpy worker. Writes only into a fresh adapter run directory."""
import argparse
import json
from pathlib import Path
import sys
import math

# Works under both Blender --python and explicitly configured bpy Python.
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from studio.adapters.retarget import validate_mapping, MIXAMO_TO_HUMANOID


def import_asset(path, append=False):
    import bpy
    suffix=path.suffix.lower()
    if suffix=='.blend':
        if append:
            with bpy.data.libraries.load(str(path),link=False) as (data,loaded): loaded.objects=list(data.objects)
            for obj in loaded.objects:
                if obj: bpy.context.scene.collection.objects.link(obj)
        else: bpy.ops.wm.open_mainfile(filepath=str(path),use_scripts=False)
    elif suffix in ('.glb','.gltf'): bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix=='.fbx': bpy.ops.import_scene.fbx(filepath=str(path))
    elif suffix=='.obj': bpy.ops.wm.obj_import(filepath=str(path))
    else: raise ValueError('Supported inputs: blend, glb, gltf, fbx, obj')


def actions(objects):
    found={}
    for obj in objects:
        data=obj.animation_data
        if not data: continue
        if data.action: found[data.action.name]=data.action
        for track in data.nla_tracks:
            for strip in track.strips:
                if strip.action: found[strip.action.name]=strip.action
    return list(found.values())


def inspect_scene():
    import bpy
    from mathutils import Vector
    objects=list(bpy.context.scene.objects)
    fps=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
    shapes={p.custom_shape for o in objects if o.type=='ARMATURE' for p in o.pose.bones if p.custom_shape}
    meshes=[o for o in objects if o.type=='MESH' and o not in shapes]
    bounds=[o.matrix_world@Vector(p) for o in meshes for p in o.bound_box]
    dimensions=[(max(p[i] for p in bounds)-min(p[i] for p in bounds))*bpy.context.scene.unit_settings.scale_length for i in range(3)] if bounds else [0,0,0]
    return {'armatures':sum(o.type=='ARMATURE' for o in objects),'meshes':len(meshes),'objects':[o.name for o in objects], 'dimensionsMeters':dimensions,'sceneUnitScale':bpy.context.scene.unit_settings.scale_length,'fps':fps,'clips':[{'name':a.name,'start':float(a.frame_range[0]),'end':float(a.frame_range[1]),'durationSeconds':float(a.frame_range[1]-a.frame_range[0])/fps} for a in actions(objects)],'blenderVersion':bpy.app.version_string,'axes':{'blender':'Z_UP','glTF':'Y_UP','conversion':'Blender glTF importer/exporter only; no implicit rescale'}}


def rigid_demo():
    import bpy
    bpy.context.scene.render.fps=24
    bpy.context.scene.frame_start=1; bpy.context.scene.frame_end=25
    bpy.ops.mesh.primitive_cube_add(size=0.3,location=(0,0,0.15))
    cube=bpy.context.object; cube.name='RigidDemo'
    for frame,angle in ((1,0),(13,math.pi/4),(25,0)):
        cube.rotation_euler.z=angle
        cube.keyframe_insert(data_path='rotation_euler',frame=frame)
    cube.animation_data.action.name='RigidTurn'
    bpy.context.scene.frame_set(1)


def scene_metadata():
    import bpy
    scene=bpy.context.scene
    return {'fps':scene.render.fps/scene.render.fps_base,'unitScale':scene.unit_settings.scale_length}


def validate_rig_transform(rig):
    import bpy
    from mathutils import Matrix
    if rig.constraints or any(bone.constraints for bone in rig.pose.bones):
        raise ValueError('Unsupported rig/pose transform constraints')
    bpy.context.view_layer.update()
    effective=rig.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.to_3x3()
    identity=Matrix.Identity(3)
    if any(not math.isfinite(effective[i][j]) or abs(effective[i][j]-identity[i][j])>1e-6 for i in range(3) for j in range(3)):
        raise ValueError('Apply effective rig object/parent rotation and scale transform before retarget')

def retarget(target_path,motion_path,mapping_path):
    import bpy
    if motion_path.suffix.lower()!='.blend':
        raise ValueError('Retarget motion requires .blend with explicit source scene FPS and units')
    # Read source scene metadata before object append discards it. Loading is
    # read-only; opening the target then replaces this temporary source scene.
    import_asset(motion_path)
    source_metadata=scene_metadata()
    # .blend opens replace the scene, whereas GLB/FBX imports add to it.
    # Keep only captured metadata before loading either target format.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_asset(target_path)
    target_metadata=scene_metadata()
    if abs(source_metadata['fps']-target_metadata['fps'])>1e-6:
        raise ValueError('Source/target FPS mismatch')
    if abs(source_metadata['unitScale']-target_metadata['unitScale'])>1e-6 or abs(target_metadata['unitScale']-1)>1e-6:
        raise ValueError('Source/target units mismatch: explicit matching meters required')
    targets=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
    if len(targets)!=1: raise ValueError('Exactly one target armature required')
    target=targets[0]; target_objects=list(bpy.context.scene.objects)
    before=set(bpy.data.objects)
    import_asset(motion_path,append=True)
    imported=set(bpy.data.objects)-before
    sources=[o for o in imported if o.type=='ARMATURE']
    if len(sources)!=1: raise ValueError('Exactly one source armature required')
    source=sources[0]
    mapping=json.loads(mapping_path.read_text()) if mapping_path else MIXAMO_TO_HUMANOID
    validate_mapping(mapping,source.data.bones.keys(),target.data.bones.keys())
    available=actions([source])
    if len(available)!=1: raise ValueError('Motion file must contain exactly one source action')
    # This profile deliberately rejects incompatible rest bases, instead of applying
    # plausible-looking rotations to arbitrary skeletons.
    for src,dst in mapping.items():
        a=source.data.bones[src]; b=target.data.bones[dst]
        parent=mapping.get(a.parent.name) if a.parent else None
        if (b.parent.name if b.parent else None)!=parent: raise ValueError('Mapped hierarchy differs: '+src)
        qa=a.matrix_local.to_quaternion(); qb=b.matrix_local.to_quaternion()
        if qa.rotation_difference(qb).angle>0.001: raise ValueError('Rest axes mismatch: '+src)
    for rig in (source,target): validate_rig_transform(rig)
    target.animation_data_clear(); target.animation_data_create()
    action=bpy.data.actions.new('Retarget_'+available[0].name); target.animation_data.action=action
    source.animation_data.action=available[0]
    start,end=(int(v) for v in available[0].frame_range)
    for frame in range(start,end+1):
        bpy.context.scene.frame_set(frame)
        for rig in (source,target): validate_rig_transform(rig)
        for src,dst in mapping.items():
            a=source.pose.bones[src]; b=target.pose.bones[dst]
            b.rotation_mode='QUATERNION'; b.rotation_quaternion=a.matrix_basis.to_quaternion()
            b.keyframe_insert(data_path='rotation_quaternion',frame=frame)
            if not b.parent:
                b.location=a.location.copy(); b.keyframe_insert(data_path='location',frame=frame)
    source_action_name=available[0].name
    for obj in imported: bpy.data.objects.remove(obj,do_unlink=True)
    if available[0].users==0: bpy.data.actions.remove(available[0])
    bpy.context.scene.frame_start=start; bpy.context.scene.frame_end=end; bpy.context.scene.frame_set(start)
    return {'mapping':mapping,'sourceAction':source_action_name,'sourceMetadata':source_metadata,'targetMetadata':target_metadata,'policy':'matching rest axes and mapped hierarchy; root translation in meters; target bone lengths preserved'}


def run(args):
    import bpy
    output=args.output_dir.resolve(); output.mkdir(parents=True,exist_ok=True)
    for name in ('inspection.json','scene.blend','asset.glb'):
        if (output/name).exists(): raise ValueError('Refusing to overwrite '+name)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    motion=None
    if args.operation=='demo': rigid_demo()
    elif args.operation=='retarget':
        if not args.motion: raise ValueError('--motion required')
        motion=retarget(args.input,args.motion,args.mapping)
    else: import_asset(args.input)
    original=inspect_scene()
    report={'status':'PASS','inspection':original,'visualReview':'NOT_RUN','motion':motion}
    if args.operation!='inspect':
        bpy.ops.wm.save_as_mainfile(filepath=str(output/'scene.blend'))
        bpy.ops.export_scene.gltf(filepath=str(output/'asset.glb'),export_format='GLB',export_animations=True,export_yup=True,use_active_scene=True,export_animation_mode='ACTIVE_ACTIONS')
        bpy.ops.wm.open_mainfile(filepath=str(output/'scene.blend'),use_scripts=False)
        reopened=inspect_scene()
        bpy.ops.wm.read_factory_settings(use_empty=True)
        # Import at the same FPS to compare frame ranges and seconds coherently.
        bpy.context.scene.render.fps=round(original['fps']); bpy.context.scene.render.fps_base=round(original['fps'])/original['fps']
        bpy.ops.import_scene.gltf(filepath=str(output/'asset.glb'))
        imported=inspect_scene()
        if imported['meshes']!=original['meshes'] or imported['armatures']!=original['armatures']: raise ValueError('Export/reimport object counts differ: '+str((original['meshes'],original['armatures'],imported['meshes'],imported['armatures'])))
        if any(abs(a-b)>1e-4 for a,b in zip(original['dimensionsMeters'],imported['dimensionsMeters'])): raise ValueError('Export/reimport dimensions differ')
        expected=sorted(round(c['durationSeconds'],4) for c in original['clips'])
        actual=sorted(round(c['durationSeconds'],4) for c in imported['clips'])
        if expected!=actual: raise ValueError('Export/reimport clip durations differ')
        report.update(reopened=reopened,reimported=imported,artifacts=['scene.blend','asset.glb'])
    (output/'inspection.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('operation',choices=['inspect','export','demo','retarget'])
    parser.add_argument('--input',type=Path); parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--motion',type=Path); parser.add_argument('--mapping',type=Path)
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    args=parser.parse_args(argv)
    print(json.dumps(run(args)))

if __name__=='__main__':
    import os
    import traceback
    code=0
    try: main()
    except Exception:
        traceback.print_exc(); code=1
    # bpy wheel teardown exits nonzero after glTF I/O on this host. The work and
    # explicit checks above complete synchronously; preserve their actual status.
    # This matches the existing laboratory CPU worker lifecycle.
    sys.stdout.flush(); sys.stderr.flush()
    if Path(sys.executable).name.startswith('python'): os._exit(code)
    if code: raise SystemExit(code)
