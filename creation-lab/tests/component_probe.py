"""In-memory real Blender adapter regression. Does not write artifacts."""
import importlib.util
from pathlib import Path
import sys
import bpy

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from components import sphere, material, mesh_object


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    spec = importlib.util.spec_from_file_location('component_demo', LAB/'examples/component-demo.py')
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    result = demo.build()
    objects = list(bpy.context.scene.objects)
    assert len(objects) == 19, len(objects)
    assert {o['part_id'] for o in objects} == set(result['parts'])
    assert all(o.type == 'MESH' and not o.modifiers for o in objects)
    assert all(len(p.vertices) == 3 for o in objects for p in o.data.polygons)
    assert all(o.data.has_custom_normals for o in objects)
    assert all(o.data.materials[0].use_nodes for o in objects)
    points = [tuple(o.matrix_world @ vertex.co) for o in objects for vertex in o.data.vertices]
    dimensions = [max(p[k] for p in points)-min(p[k] for p in points) for k in range(3)]
    assert abs(max(dimensions)-0.30) < 1e-5, dimensions
    count = len(objects)
    for part_id, limit in (('', None), ('valid', 1)):
        try:
            mesh_object('invalid', part_id, sphere(), bpy.data.materials[0], max_triangles=limit)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid object unexpectedly created')
    assert len(bpy.context.scene.objects) == count
    try:
        material('invalid', (1, -1, 0))
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid material unexpectedly created')
    print('COMPONENT_ADAPTER=PASS')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
