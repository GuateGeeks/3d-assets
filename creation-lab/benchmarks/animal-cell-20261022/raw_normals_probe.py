"""B diagnostic: compare authored surfaces with raw GLB POSITION/NORMAL accessors."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import bpy

args = sys.argv[sys.argv.index('--') + 1:]
run, output = Path(args[0]).resolve(), Path(args[1]).resolve()
spec = importlib.util.spec_from_file_location('raw_probe_geometry', run / 'code/geometry_qa.py')
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)
raw = (run / 'asset.glb').read_bytes()
json_length = struct.unpack_from('<I', raw, 12)[0]
doc = json.loads(raw[20:20+json_length])
binary = raw[28+json_length:]
geometry.load(run / 'asset.glb', static=True)
def accessor(index):
    item = doc['accessors'][index]
    view = doc['bufferViews'][item['bufferView']]
    code, width = {5126: ('f', 4), 5125: ('I', 4), 5123: ('H', 2), 5121: ('B', 1)}[item['componentType']]
    count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[item['type']]
    offset = view.get('byteOffset', 0) + item.get('byteOffset', 0)
    stride = view.get('byteStride', width*count)
    return [struct.unpack_from('<' + code*count, binary, offset + index*stride) for index in range(item['count'])]
surfaces = []
for node in doc['nodes']:
    if 'mesh' not in node:
        continue
    if any(key in node for key in ('matrix', 'translation', 'rotation', 'scale')):
        raise ValueError('This bounded diagnostic expects B world-baked identity mesh nodes')
    for primitive in doc['meshes'][node['mesh']]['primitives']:
        material = bpy.data.materials[doc['materials'][primitive['material']]['name']]
        key = hashlib.sha256(json.dumps(geometry.material_value(material, {}), sort_keys=True).encode()).hexdigest()
        positions, normals = (accessor(primitive['attributes'][name]) for name in ('POSITION', 'NORMAL'))
        indices = [value[0] for value in accessor(primitive['indices'])]
        for start in range(0, len(indices), 3):
            corners = []
            for index in indices[start:start+3]:
                position, normal = positions[index], normals[index]
                corners.append([[position[0], -position[2], position[1]], [], [normal[0], -normal[2], normal[1]]])
            surfaces.append([key, corners])
expected = json.loads((run / 'source-surfaces.json').read_text())
exported = {**expected, 'surfaces': surfaces}
result = {'authoredVsRawExport': geometry.compare_surfaces(expected, exported),
          'rawExportVsImported': geometry.compare_surfaces(exported, geometry.measure()),
          'rawTriangles': len(surfaces)}
with output.open('x') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result))
