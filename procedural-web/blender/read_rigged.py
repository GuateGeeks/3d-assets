"""Reads a rigged, textured character (one mesh, a Mixamo-style armature) for `pw.py adopt`.

    blender --background --factory-startup --python read_rigged.py -- <file.blend> <map.json> <out.json>

Rest geometry in three.js axes ((x, y, z)_three = (x, z, -y)_blender), triangles in their
winding, the base-colour texture sampled per face (centroid and three inner points), each
vertex's weights summed onto the 12 bones of the campus rig through map.json, the armature
joints, and the ink pixels (dark navy) of the face lifted to 3D: the painted eyes and smile.
"""
import json
import sys

import bpy
import bmesh  # after bpy: the bpy module only exposes bmesh once loaded

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
blend, mapping, out = argv[:3]
bone_map = json.load(open(mapping, encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=blend)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.find_armature() == arm]
if len(meshes) != 1:
    raise SystemExit(f'Se espera una malla riggeada; hay {[o.name for o in meshes]}')
obj = meshes[0]


def three(v):
    return [v.x, v.z, -v.y]


# ---- base-colour image: the one feeding the Principled base colour
def base_image(material):
    tree = material.node_tree if material and material.use_nodes else None
    bsdf = next((n for n in tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if tree else None
    link = bsdf.inputs['Base Color'].links[0] if bsdf and bsdf.inputs['Base Color'].is_linked else None
    node = link.from_node if link else None
    while node is not None and node.type != 'TEX_IMAGE':
        node = next((l.from_node for i in node.inputs for l in i.links), None)
    return node.image if node else None


images = {}
for slot in obj.material_slots:
    img = base_image(slot.material)
    if img and img.name not in images:
        w, h = img.size
        images[img.name] = (w, h, list(img.pixels[:]))  # linear floats? read as stored (byte images: sRGB values)

bm = bmesh.new()
bm.from_mesh(obj.data)
bmesh.ops.triangulate(bm, faces=bm.faces[:])
bm.verts.ensure_lookup_table()
uv = bm.loops.layers.uv.active
m = obj.matrix_world
vertices = [three(m @ v.co) for v in bm.verts]


def texel(img, u, v):
    w, h, px = img
    x = min(w - 1, max(0, int((u % 1) * w)))
    y = min(h - 1, max(0, int((v % 1) * h)))
    o = (y * w + x) * 4
    return px[o:o + 3]


faces, colors, face_uv = [], [], []
for f in bm.faces:
    faces.append([l.vert.index for l in f.loops])
    mat = obj.material_slots[f.material_index].material if obj.material_slots else None
    img = images.get(base_image(mat).name) if mat and base_image(mat) else None
    uvs = [tuple(l[uv].uv) for l in f.loops]
    face_uv.append([list(p) for p in uvs])
    if not img:
        colors.append(None)
        continue
    cu, cv = sum(p[0] for p in uvs) / 3, sum(p[1] for p in uvs) / 3
    samples = [texel(img, cu, cv)] + [texel(img, cu + (p[0] - cu) * .5, cv + (p[1] - cv) * .5) for p in uvs]
    colors.append([round(sum(s[k] for s in samples) / len(samples) * 255, 1) for k in range(3)])

# ---- weights onto the campus bones
names = {g.index: g.name for g in obj.vertex_groups}
weights = []
for v in obj.data.vertices:
    acc = {}
    for g in v.groups:
        target = bone_map.get(names.get(g.group, ''), None)
        if target and g.weight > 0:
            acc[target] = acc.get(target, 0) + g.weight
    weights.append(acc)

# ---- ink: dark navy pixels of the face triangles, lifted to 3D by barycentric coordinates
ink = []
img = next(iter(images.values()), None)
if img:
    w, h, px = img
    for f, tri in zip(bm.faces, faces):
        P = [vertices[i] for i in tri]
        if min(p[2] for p in P) < 0:  # the front of the body only
            continue
        uvs = [(l[uv].uv[0] * w, l[uv].uv[1] * h) for l in f.loops]
        d = (uvs[1][0] - uvs[0][0]) * (uvs[2][1] - uvs[0][1]) - (uvs[2][0] - uvs[0][0]) * (uvs[1][1] - uvs[0][1])
        if abs(d) < 1e-9:
            continue
        x0, x1 = int(min(p[0] for p in uvs)), int(max(p[0] for p in uvs)) + 1
        y0, y1 = int(min(p[1] for p in uvs)), int(max(p[1] for p in uvs)) + 1
        for py in range(max(0, y0), min(h, y1)):
            for pxl in range(max(0, x0), min(w, x1)):
                a = ((pxl + .5 - uvs[0][0]) * (uvs[2][1] - uvs[0][1]) - (uvs[2][0] - uvs[0][0]) * (py + .5 - uvs[0][1])) / d
                b = ((uvs[1][0] - uvs[0][0]) * (py + .5 - uvs[0][1]) - (pxl + .5 - uvs[0][0]) * (uvs[1][1] - uvs[0][1])) / d
                if a < 0 or b < 0 or a + b > 1:
                    continue
                o = (py * w + pxl) * 4
                r, g, bl = px[o] * 255, px[o + 1] * 255, px[o + 2] * 255
                if r + g + bl > 180 or bl < r + 40:
                    continue
                ink.append([P[0][k] + a * (P[1][k] - P[0][k]) + b * (P[2][k] - P[0][k]) for k in range(3)])
bm.free()

joints = {b.name: three(arm.matrix_world @ b.head_local) for b in arm.data.bones}
json.dump({'object': obj.name, 'armature': arm.name, 'vertices': vertices, 'faces': faces, 'colors': colors, 'weights': weights, 'joints': joints,
           'ink': ink, 'images': {k: v[:2] for k, v in images.items()}, 'actions': [a.name for a in bpy.data.actions], 'blender': bpy.app.version_string},
          open(out, 'w', encoding='utf-8'))
print(json.dumps({'out': out, 'triangles': len(faces), 'vertices': len(vertices), 'ink': len(ink), 'images': list(images)}))
