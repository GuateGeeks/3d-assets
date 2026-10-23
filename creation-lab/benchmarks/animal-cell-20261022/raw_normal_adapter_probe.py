"""Diagnostic importer adapter: decode only GLB data, never source QA normals.

Triangles use independent vertices so Blender need not compress a custom normal
against a nearly singular multi-face fan. Source GLB and authored scene stay intact.
"""
import importlib.util
import json
from pathlib import Path
import struct
import sys
import bpy

args = sys.argv[sys.argv.index('--') + 1:]
run, output = Path(args[0]).resolve(), Path(args[1]).resolve()
spec = importlib.util.spec_from_file_location('adapter_probe_geometry', run / 'code/geometry_qa.py')
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)
geometry.load(run / 'asset.glb', static=True)
raw = (run / 'asset.glb').read_bytes()
json_length = struct.unpack_from('<I', raw, 12)[0]
doc = json.loads(raw[20:20+json_length])
binary = raw[28+json_length:]
def accessor(index):
    item = doc['accessors'][index]
    view = doc['bufferViews'][item['bufferView']]
    code, width = {5126: ('f', 4), 5125: ('I', 4), 5123: ('H', 2), 5121: ('B', 1)}[item['componentType']]
    count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[item['type']]
    offset = view.get('byteOffset', 0) + item.get('byteOffset', 0)
    stride = view.get('byteStride', width*count)
    return [struct.unpack_from('<' + code*count, binary, offset + i*stride) for i in range(item['count'])]
cache = {}
for node in doc['nodes']:
    if 'mesh' not in node:
        continue
    obj = bpy.data.objects[node['name']]
    mesh_id = node['mesh']
    if mesh_id in cache:
        obj.data = cache[mesh_id]
        continue
    positions, normals, faces, material_ids = [], [], [], []
    primitives = doc['meshes'][mesh_id]['primitives']
    uv_names = sorted({name for primitive in primitives for name in primitive['attributes'] if name.startswith('TEXCOORD_')})
    uv_values = {name: [] for name in uv_names}
    for primitive in primitives:
        if primitive.get('mode', 4) != 4:
            raise ValueError('Probe supports triangle primitives only')
        source_positions = accessor(primitive['attributes']['POSITION'])
        source_normals = accessor(primitive['attributes']['NORMAL'])
        source_uvs = {name: accessor(primitive['attributes'][name]) for name in uv_names if name in primitive['attributes']}
        indices = [item[0] for item in accessor(primitive['indices'])] if 'indices' in primitive else list(range(len(source_positions)))
        for start in range(0, len(indices), 3):
            base = len(positions)
            for index in indices[start:start+3]:
                p, n = source_positions[index], source_normals[index]
                positions.append((p[0], -p[2], p[1]))
                normals.append((n[0], -n[2], n[1]))
                for name in uv_names:
                    uv = source_uvs[name][index] if name in source_uvs else (0, 0)
                    uv_values[name].append((uv[0], 1-uv[1]))
            faces.append((base, base+1, base+2))
            material_ids.append(primitive['material'])
    mesh = bpy.data.meshes.new(obj.data.name + '-raw-normal-adapter')
    mesh.from_pydata(positions, [], faces)
    for mat in doc['materials']:
        mesh.materials.append(bpy.data.materials[mat['name']])
    for poly, material_id in zip(mesh.polygons, material_ids):
        poly.material_index = material_id
        poly.use_smooth = True
    for name in uv_names:
        layer = mesh.uv_layers.new(name=name)
        for loop, uv in zip(layer.data, uv_values[name]):
            loop.uv = uv
    mesh.update()
    mesh.normals_split_custom_set(normals)
    obj.data = mesh
    cache[mesh_id] = mesh
bpy.context.view_layer.update()
expected = json.loads((run / 'source-surfaces.json').read_text())
actual = geometry.measure()
result = {'fullStrictComparison': geometry.compare_surfaces(expected, actual),
          'triangles': actual['triangles'], 'adapterVertices': actual['vertices'],
          'sourceQaUsedByAdapter': False, 'sourceGlbMutated': False}
with output.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result))
