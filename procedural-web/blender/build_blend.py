"""Builds an editable .blend from a cotizador procedural character (inside Blender).

    blender --background --factory-startup --python build_blend.py -- <model.json> <clips.json> <out.blend>

Also runs as a plain script with the `bpy` module. Conventions (README):
- three.js (Y up, +Z front) -> Blender (Z up, -Y front): (x, y, z) -> (x, -z, y). It is a proper
  rotation, so the triangle winding (counter-clockwise from outside) is kept.
- Every bone points up (+Z) with roll 0: its local X, Y, Z are three.js X, Y, Z. A three.js
  rotation in Euler order 'YXZ' (R = Ry Rx Rz) is the Blender pose rotation mode 'ZXY'.
- One object per part and variant ('bag.head', 'plain.torso'...), one vertex group per bone
  (weight 1; most parts have one, a skinned model's seams more), one material per colour class. Variant collections: 'bag' (standing,
  with backpack) and 'plain' (seated); 'plain' starts hidden.
- One action per clip ('clip.walk'...), linear keys from frame 1, its metadata in action['gg_clip'].
"""
import json
import sys

import bpy

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
model_file, clips_file, out = argv[:3]
model = json.load(open(model_file, encoding='utf-8'))
clips = json.load(open(clips_file, encoding='utf-8'))['clips'] if clips_file != '-' else {}
H = model['H']


def conv(v, scale=H):
    return (v[0] * scale, -v[2] * scale, v[1] * scale)


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 24
scene.unit_settings.system = 'METRIC'

# ---- armature: the 12 bones of the rig at their root-rest pivots
arm_data = bpy.data.armatures.new(f"GG.{model['model']}.rig")
arm = bpy.data.objects.new(f"GG.{model['model']}", arm_data)
scene.collection.objects.link(arm)
arm['gg_model'] = model['model']
arm['gg_H'] = H
arm['gg_landmarks'] = json.dumps(model['landmarks'])
arm['gg_source'] = json.dumps(model['source'])
arm['gg_module'] = model['module']
arm_data.display_type = 'STICK'
arm.show_in_front = True
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
edit = {}
for name, b in model['rig'].items():
    e = arm_data.edit_bones.new(name)
    e.head = conv(b['at'])
    e.tail = (e.head[0], e.head[1], e.head[2] + .04 * H)
    e.roll = 0
    edit[name] = e
for name, b in model['rig'].items():
    if b['parent']:
        edit[name].parent = edit[b['parent']]
        edit[name].use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')
for pb in arm.pose.bones:
    pb.rotation_mode = 'ZXY'

# ---- materials: one per colour class
materials = {}
for name in model['classes']:
    m = bpy.data.materials.new(f'gg.{name}')
    hexc = model['palette'][name].lstrip('#')
    rgb = [int(hexc[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb]
    m.diffuse_color = (*lin, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (*lin, 1)
        bsdf.inputs['Roughness'].default_value = .9
    materials[name] = m

# ---- one object per part and variant
for variant, data in model['variants'].items():
    col = bpy.data.collections.new(variant)
    scene.collection.children.link(col)
    for part in data['parts']:
        mesh = bpy.data.meshes.new(f"{variant}.{part['id']}")
        mesh.from_pydata([conv(v) for v in part['vertices']], [], [tuple(f) for f in part['faces']])
        for name in model['classes']:
            mesh.materials.append(materials[name])
        for poly, c in zip(mesh.polygons, part['classes']):
            poly.material_index = c
            poly.use_smooth = False
        mesh.update()
        obj = bpy.data.objects.new(mesh.name, mesh)
        col.objects.link(obj)
        obj.parent = arm
        # one group per bone: a skinned model's seam vertices follow a neighbouring bone (weight 1)
        own = part.get('vertexBones') or [part['bone']] * len(part['vertices'])
        for name in dict.fromkeys([part['bone']] + own):
            obj.vertex_groups.new(name=name).add([i for i, b in enumerate(own) if b == name], 1.0, 'REPLACE')
        obj['gg_bone'] = part['bone']
        mod = obj.modifiers.new('rig', 'ARMATURE')
        mod.object = arm
        obj['gg_part'] = part['id']
        obj['gg_variant'] = variant
    if variant != 'bag':
        bpy.context.view_layer.layer_collection.children[variant].hide_viewport = True

# ---- actions: one per clip, linear keys from frame 1
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
arm.animation_data_create()
for key, clip in clips.items():
    act = bpy.data.actions.new(f'clip.{key}')
    act.use_fake_user = True
    meta = {k: clip[k] for k in ('name', 'args', 'time', 'offset', 'duration', 'fps')}
    meta['count'] = len(clip['frames'])
    act['gg_clip'] = json.dumps(meta)
    arm.animation_data.action = act
    for i, frame in enumerate(clip['frames']):
        for bone, rot in frame.items():
            if bone == 'y':
                pb = arm.pose.bones['hips']
                pb.location = (0, rot, 0)
                pb.keyframe_insert('location', frame=i + 1)
                continue
            pb = arm.pose.bones[bone]
            pb.rotation_euler = rot
            pb.keyframe_insert('rotation_euler', frame=i + 1)
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
if clips:
    first = bpy.data.actions.get('clip.stand') or next(a for a in bpy.data.actions if a.name.startswith('clip.'))
    arm.animation_data.action = first
    scene.frame_start, scene.frame_end = 1, max(1, int(first.frame_range[1]))
bpy.ops.wm.save_as_mainfile(filepath=out)
print(json.dumps({'out': out, 'parts': sum(len(v['parts']) for v in model['variants'].values()), 'actions': len(clips), 'blender': bpy.app.version_string}))
