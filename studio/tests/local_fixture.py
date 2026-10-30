"""Own disposable humanoid fixture; never loads repository models."""
import sys
from pathlib import Path
import json
import math
import os
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from studio.adapters.retarget import MIXAMO_TO_HUMANOID


def create(root):
    root.mkdir(parents=True,exist_ok=False)
    mapping=MIXAMO_TO_HUMANOID
    parent={'Hips':None,'Spine':'Hips','Spine1':'Spine','Spine2':'Spine1','Neck':'Spine2','Head':'Neck'}
    for side in ('Left','Right'):
        parent.update({side+'Shoulder':'Spine2',side+'Arm':side+'Shoulder',side+'ForeArm':side+'Arm',side+'Hand':side+'ForeArm',side+'UpLeg':'Hips',side+'Leg':side+'UpLeg',side+'Foot':side+'Leg'})
    def armature(source):
        bpy.ops.object.armature_add()
        obj=bpy.context.object; obj.name='Source' if source else 'Target'
        bpy.ops.object.mode_set(mode='EDIT'); obj.data.edit_bones.remove(obj.data.edit_bones[0])
        for index,(src,dst) in enumerate(mapping.items()):
            bone=obj.data.edit_bones.new(src if source else dst)
            bone.head=(index*0.03,0,1); bone.tail=(index*0.03,0,1.1)
        for src,dst in mapping.items():
            par=parent[src.split(':')[1]]
            if par: obj.data.edit_bones[src if source else dst].parent=obj.data.edit_bones['mixamorig:'+par if source else mapping['mixamorig:'+par]]
        bpy.ops.object.mode_set(mode='OBJECT')
        return obj
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig=armature(False)
    bpy.ops.mesh.primitive_cube_add(size=.3,location=(0,0,1))
    mesh=bpy.context.object; mesh.parent=rig
    group=mesh.vertex_groups.new(name='hips'); group.add(list(range(len(mesh.data.vertices))),1,'REPLACE')
    modifier=mesh.modifiers.new('Armature','ARMATURE'); modifier.object=rig
    bpy.ops.wm.save_as_mainfile(filepath=str(root/'target.blend'))
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.context.scene.render.fps=24
    rig=armature(True)
    for frame,angle in ((1,0),(13,math.pi/4),(25,0)):
        p=rig.pose.bones['mixamorig:LeftArm']; p.rotation_mode='QUATERNION'
        from mathutils import Quaternion
        p.rotation_quaternion=Quaternion((0,0,1),angle); p.keyframe_insert(data_path='rotation_quaternion',frame=frame)
    rig.animation_data.action.name='HumanoidWave'; bpy.context.scene.frame_start=1; bpy.context.scene.frame_end=25
    bpy.ops.wm.save_as_mainfile(filepath=str(root/'motion.blend'))
    (root/'mapping.json').write_text(json.dumps(mapping))

if __name__=='__main__':
    code=0
    try: create(Path(sys.argv[1]))
    except Exception:
        import traceback; traceback.print_exc(); code=1
    sys.stdout.flush(); sys.stderr.flush(); os._exit(code)
