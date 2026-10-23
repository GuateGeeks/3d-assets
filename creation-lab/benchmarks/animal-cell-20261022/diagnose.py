"""Read-only roundtrip diagnosis against an existing immutable benchmark run."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector, kdtree

args = sys.argv[sys.argv.index('--') + 1:]
run, output = Path(args[0]).resolve(), Path(args[1]).resolve()
spec = importlib.util.spec_from_file_location('diagnostic_geometry', run / 'code/geometry_qa.py')
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)
expected = json.loads((run / 'source-surfaces.json').read_text())
geometry.load(run / 'asset.glb', static=True)
actual = geometry.measure()
results = {}
for name, ignore_uv, ignore_normal in [('full', False, False), ('ignoreNormals', False, True),
                                      ('ignoreUVs', True, False), ('positionsWindingMaterials', True, True)]:
    left, right = copy.deepcopy(expected), copy.deepcopy(actual)
    for data in (left, right):
        for _, corners in data['surfaces']:
            for corner in corners:
                if ignore_uv:
                    corner[1] = []
                if ignore_normal:
                    corner[2] = [0, 0, 1]
    results[name] = geometry.compare_surfaces(left, right)
tree = kdtree.KDTree(len(expected['surfaces']))
for index, (_, corners) in enumerate(expected['surfaces']):
    tree.insert(sum((Vector(c[0]) for c in corners), Vector()) / 3, index)
tree.balance()
first = []
normal_dots = []
for mat, corners in actual['surfaces']:
    center = sum((Vector(c[0]) for c in corners), Vector()) / 3
    candidates = []
    for _, index, _ in tree.find_range(center, geometry.POSITION_TOLERANCE * 2):
        exp_mat, exp_corners = expected['surfaces'][index]
        if mat != exp_mat:
            continue
        for shift in range(3):
            paired = list(zip(exp_corners, corners[shift:] + corners[:shift]))
            if all((Vector(a[0])-Vector(b[0])).length <= geometry.POSITION_TOLERANCE for a,b in paired):
                dots = [Vector(a[2]).dot(Vector(b[2])) for a,b in paired]
                candidates.append({'expected': exp_corners, 'actual': corners[shift:] + corners[:shift], 'normalDots': dots})
                normal_dots.extend(dots)
    if candidates and max(min(c['normalDots']) for c in candidates) < 1 - 1e-5 and len(first) < 3:
        first.append(candidates[0])
def degenerate(data):
    return sum((Vector(corners[1][0])-Vector(corners[0][0])).cross(Vector(corners[2][0])-Vector(corners[0][0])).length < 1e-14 for _,corners in data['surfaces'])
result = {'comparisons': results, 'sourceTriangles': expected['triangles'], 'importedTriangles': actual['triangles'],
          'sourceDegenerateTriangles': degenerate(expected), 'importedDegenerateTriangles': degenerate(actual),
          'minimumNormalDot': min(normal_dots), 'firstNormalDifferences': first}
with output.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps({key: value for key, value in result.items() if key != 'firstNormalDifferences'}))
