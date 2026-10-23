"""Read-only authored degeneracy inventory for a bounded benchmark repair."""
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
run, output = Path(args[0]).resolve(), Path(args[1]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(run / 'source.blend'), load_ui=False, use_scripts=False)
objects = []
parts = {}
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    mesh = obj.data
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    degenerate = 0
    collapsed_edge = 0
    for tri in mesh.loop_triangles:
        a, b, c = [points[index] for index in tri.vertices]
        if (b-a).cross(c-a).length < 1e-14:
            degenerate += 1
            if min((a-b).length, (b-c).length, (c-a).length) < 1e-10:
                collapsed_edge += 1
    if degenerate:
        item = {'object': obj.name, 'part': obj.get('part_id'), 'triangles': len(mesh.loop_triangles),
                'degenerateTriangles': degenerate, 'degenerateWithCollapsedEdge': collapsed_edge}
        objects.append(item)
        part = parts.setdefault(item['part'], {'objects': 0, 'degenerateTriangles': 0})
        part['objects'] += 1
        part['degenerateTriangles'] += degenerate
result = {'sourceBlend': str(run / 'source.blend'),
          'sourceBlendSha256': hashlib.sha256((run / 'source.blend').read_bytes()).hexdigest(),
          'degenerateTriangles': sum(item['degenerateTriangles'] for item in objects),
          'affectedObjects': len(objects), 'parts': parts, 'objects': sorted(objects, key=lambda item: item['object'])}
with output.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
print(json.dumps({key: value for key, value in result.items() if key != 'objects'}, ensure_ascii=False))
