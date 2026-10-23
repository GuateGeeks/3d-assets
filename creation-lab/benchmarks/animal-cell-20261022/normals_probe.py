"""One shared export diagnostic; never edits the source run or generator."""
import importlib.util
import json
from pathlib import Path
import sys
import bpy

args = sys.argv[sys.argv.index('--') + 1:]
run, output = Path(args[0]).resolve(), Path(args[1]).resolve()
output.mkdir(exist_ok=False)
spec = importlib.util.spec_from_file_location('probe_geometry', run / 'code/geometry_qa.py')
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)
bpy.ops.wm.open_mainfile(filepath=str(run / 'source.blend'), load_ui=False, use_scripts=False)
before = geometry.measure()
original_custom = {}
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        mesh = obj.data
        original_custom[obj.name] = mesh.has_custom_normals
        normals = [tuple(corner.vector) for corner in mesh.corner_normals]
        mesh.normals_split_custom_set(normals)
        mesh.calc_loop_triangles()
        triangles = list(mesh.loop_triangles)
        uv_data = {layer.name: [tuple(layer.data[loop].uv) for tri in triangles for loop in tri.loops] for layer in mesh.uv_layers}
        loop_normals = [tuple(mesh.corner_normals[loop].vector) for tri in triangles for loop in tri.loops]
        new = bpy.data.meshes.new(mesh.name + '-exact-triangles')
        new.from_pydata([tuple(v.co) for v in mesh.vertices], [], [tuple(tri.vertices) for tri in triangles])
        for mat in mesh.materials:
            new.materials.append(mat)
        for polygon, triangle in zip(new.polygons, triangles):
            polygon.material_index = triangle.material_index
            polygon.use_smooth = mesh.polygons[triangle.polygon_index].use_smooth
        for name, data in uv_data.items():
            layer = new.uv_layers.new(name=name)
            for entry, uv in zip(layer.data, data):
                entry.uv = uv
        new.normals_split_custom_set(loop_normals)
        obj.data = new
bpy.context.view_layer.update()
fixed = geometry.measure()
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        obj.select_set(True)
path = output / 'custom-normal-probe.glb'
bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True, export_yup=True,
                          export_animations=False, export_extras=True, export_cameras=False, export_lights=False)
geometry.load(path, static=True)
after = geometry.measure()
checks = {'freezePreservesSource': geometry.compare_surfaces(before, fixed),
          'roundtripAgainstFrozen': geometry.compare_surfaces(fixed, after),
          'roundtripAgainstAuthored': geometry.compare_surfaces(before, after),
          'originalCustomNormalsObjects': sum(original_custom.values()), 'meshObjects': len(original_custom)}
with (output / 'result.json').open('x') as stream:
    json.dump(checks, stream, indent=2)
print(json.dumps(checks))
