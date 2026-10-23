"""Read-only trials of native Blender NORMALS import without QA-based repair."""
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import bpy

args = sys.argv[sys.argv.index('--') + 1:]
run, output = Path(args[0]).resolve(), Path(args[1]).resolve()
spec = importlib.util.spec_from_file_location('import_probe_geometry', run / 'code/geometry_qa.py')
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)
expected = json.loads((run / 'source-surfaces.json').read_text())
geometry.load(run / 'asset.glb', static=True)
result = {'default': geometry.compare_surfaces(expected, geometry.measure())}
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        obj.data.update()
bpy.context.view_layer.update()
result['smoothAfterImport'] = geometry.compare_surfaces(expected, geometry.measure())
native = importlib.import_module('io_scene_gltf2.blender.imp.mesh')
original = native.set_poly_smoothing
def smooth_before_custom_normals(gltf, pymesh, mesh, vert_normals, loop_vidxs):
    mesh.shade_smooth()
try:
    native.set_poly_smoothing = smooth_before_custom_normals
    geometry.load(run / 'asset.glb', static=True)
finally:
    native.set_poly_smoothing = original
result['smoothBeforeCustomNormals'] = geometry.compare_surfaces(expected, geometry.measure())
with output.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result))
