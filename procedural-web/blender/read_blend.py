"""Reads a .blend built by build_blend.py (and retouched by hand) back into interchange JSON.

    blender --background --factory-startup --python read_blend.py -- <file.blend> <out.json>

Geometry is read in rest: the mesh data (the armature modifier is not applied) through each
object's world matrix, back to three.js axes and H units. Polygons are triangulated; each face
keeps the class of its material ('gg.<class>') and each part the bone of its vertex group.
Clips: every action with action['gg_clip'] is evaluated frame by frame (version independent:
layered actions of Blender 4.4+ included) into whole poses, rotations in three.js 'YXZ' order.
"""
import json
import sys

import bpy
import bmesh  # after bpy: the bpy module only exposes bmesh once loaded

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
blend, out = argv[:2]
bpy.ops.wm.open_mainfile(filepath=blend)
scene = bpy.context.scene
arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE' and 'gg_model' in o), None)
if arm is None:
    raise SystemExit('No hay un armature con gg_model: abre un .blend exportado por pw.py')
H = float(arm['gg_H'])
errors = []


def back(v, scale=H):
    return [round(v[0] / scale, 4), round(v[2] / scale, 4), round(-v[1] / scale, 4)]


world = arm.matrix_world
rig = {}
for b in arm.data.bones:
    rig[b.name] = {'parent': b.parent.name if b.parent else None, 'at': back(world @ b.head_local)}

variants = {}
for obj in bpy.data.objects:
    if obj.type != 'MESH' or 'gg_variant' not in obj:
        continue
    # each vertex follows its heaviest group (one influence per vertex, as the campus skins)
    own = [obj.vertex_groups[max(v.groups, key=lambda g: g.weight).group].name if v.groups else None for v in obj.data.vertices]
    if None in own or not set(own) <= set(rig):
        errors.append(f'{obj.name}: cada vértice necesita un grupo con el nombre de un hueso ({sorted(set(map(str, own)))})')
        continue
    bone = obj.get('gg_bone') or max(set(own), key=own.count)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table()
    m = obj.matrix_world
    vertices = [back(m @ v.co) for v in bm.verts]
    faces, face_classes = [], []
    for f in bm.faces:
        mat = obj.material_slots[f.material_index].material if f.material_index < len(obj.material_slots) else None
        name = mat.name.split('.')[1] if mat and mat.name.startswith('gg.') else None
        if not name:
            errors.append(f'{obj.name}: cara sin material gg.<clase>')
            continue
        faces.append([v.index for v in f.verts])
        face_classes.append(name)
    bm.free()
    part = {'id': obj.get('gg_part', obj.name.split('.', 1)[1]), 'object': obj.name, 'bone': bone, 'vertices': vertices, 'faces': faces, 'classes': face_classes}
    if any(b != bone for b in own):
        part['vertexBones'] = own
    variants.setdefault(obj['gg_variant'], []).append(part)

# ---- clips
clips = {}
ad = arm.animation_data
keys = ['torso', 'head', 'armL', 'armR', 'foreL', 'foreR', 'legL', 'legR', 'shinL', 'shinR']
for act in bpy.data.actions:
    if 'gg_clip' not in act:
        continue
    meta = json.loads(act['gg_clip'])
    ad.action = act
    if hasattr(ad, 'action_slot') and getattr(act, 'slots', None) and len(act.slots):
        ad.action_slot = act.slots[0]
    start, end = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
    count = meta['count'] if meta['time'] is None else max(1, end - start + 1)
    frames = []
    for i in range(count):
        scene.frame_set(start + i)
        frame = {}
        for k in keys:
            e = arm.pose.bones[k].matrix_basis.to_euler('ZXY')
            frame[k] = [round(e.x, 5), round(e.y, 5), round(e.z, 5)]
        frame['y'] = round(arm.pose.bones['hips'].matrix_basis.translation.y, 5)
        frames.append(frame)
    # a clip lengthened or shortened in Blender keeps its frame rate: its duration follows
    duration = meta['duration'] if meta['time'] is None or count == meta['count'] else count / meta['fps']
    clips[act.name[5:] if act.name.startswith('clip.') else act.name] = {**{k: meta[k] for k in ('name', 'args', 'time', 'offset', 'fps')}, 'duration': duration, 'frames': frames}

json.dump({'model': arm['gg_model'], 'module': arm['gg_module'], 'H': H, 'landmarks': json.loads(arm['gg_landmarks']), 'source': json.loads(arm['gg_source']),
           'rig': rig, 'variants': {k: {'parts': v} for k, v in variants.items()}, 'clips': clips, 'errors': errors, 'blender': bpy.app.version_string},
          open(out, 'w', encoding='utf-8'))
print(json.dumps({'out': out, 'parts': sum(len(v) for v in variants.values()), 'clips': len(clips), 'errors': len(errors)}))
