"""Real Blender worker, invoked in three independent CPU processes."""
import json
import hashlib
import math
import os
from pathlib import Path
import sys
import traceback
import bpy
import bmesh
from mathutils import Vector

def write(path, data):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write('\n')

def meshes():
    return [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']

def measure():
    points, oriented_triangles, triangles, materials, nonmanifold, raw_nonmanifold, images = [], [], 0, set(), 0, 0, []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in meshes():
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
        world_points = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
        points.extend(world_points)
        quantized = [tuple(round(v * 100000) for v in point) for point in world_points]
        for triangle in mesh.loop_triangles:
            vertices = tuple(quantized[index] for index in triangle.vertices)
            # A cyclic rotation preserves winding; reversal intentionally differs.
            oriented = min(vertices, vertices[1:] + vertices[:1], vertices[2:] + vertices[:2])
            mat = mesh.materials[triangle.material_index] if triangle.material_index < len(mesh.materials) else None
            oriented_triangles.append((oriented, mat.name if mat else None))
        for polygon in mesh.polygons:
            if polygon.material_index < len(mesh.materials) and mesh.materials[polygon.material_index]:
                materials.add(mesh.materials[polygon.material_index].name)
        bm = bmesh.new()
        bm.from_mesh(mesh)
        raw_nonmanifold += sum(1 for edge in bm.edges if not edge.is_manifold)
        # glTF duplicates vertices at normal/material seams. Diagnose geometric
        # closure on a disposable welded copy; preserve the imported mesh itself.
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.000001)
        nonmanifold += sum(1 for edge in bm.edges if not edge.is_manifold)
        bm.free()
        evaluated.to_mesh_clear()
    for name in materials:
        material = bpy.data.materials[name]
        if material.use_nodes:
            images.extend(node.image for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image)
    minimum = [min(point[i] for point in points) for i in range(3)]
    maximum = [max(point[i] for point in points) for i in range(3)]
    signature = sorted(set(tuple(round(v * 100000) for v in point) for point in points))
    material_values = []
    for name in sorted(materials):
        shader = bpy.data.materials[name].node_tree.nodes.get('Principled BSDF')
        material_values.append({'name': name, 'baseColor': list(shader.inputs['Base Color'].default_value),
                                'roughness': shader.inputs['Roughness'].default_value,
                                'metallic': shader.inputs['Metallic'].default_value})
    return {'meshCount': len(meshes()), 'triangles': triangles, 'materialCount': len(materials),
            'maxTextureSize': max([max(image.size) for image in images] or [0]),
            'missingImages': any(image.source == 'FILE' and not image.packed_file and not Path(bpy.path.abspath(image.filepath)).is_file() for image in images),
            'finite': all(math.isfinite(v) for point in points for v in point),
            'nonManifoldEdges': nonmanifold, 'rawNonManifoldEdges': raw_nonmanifold,
            'geometrySignature': hashlib.sha256(json.dumps(signature).encode()).hexdigest(),
            'surfaceSignature': hashlib.sha256(json.dumps(sorted(oriented_triangles)).encode()).hexdigest(),
            'materialValues': material_values, 'bboxMinM': minimum, 'bboxMaxM': maximum,
            'dimensionsM': [maximum[i] - minimum[i] for i in range(3)],
            'transformsApplied': all(all(abs(v) < 1e-5 for v in obj.rotation_euler) and all(abs(v-1) < 1e-5 for v in obj.scale) for obj in meshes())}

def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()

def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = 0.65
    return mat

def build(run):
    brief = json.loads((run / 'brief.json').read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    teal = material('Canary teal', (0.025, 0.45, 0.38))
    amber = material('Canary amber', (0.95, 0.43, 0.055))
    # Original three-block calibration beacon. Front is -Y.
    parts = [((0, 0, 0.10), (0.14, 0.12, 0.20), teal),
             ((0, -0.01, 0.25), (0.18, 0.16, 0.10), amber),
             ((0, -0.085, 0.25), (0.07, 0.035, 0.035), teal)]
    for index, (location, dimensions, mat) in enumerate(parts):
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        obj = bpy.context.object
        obj.name = 'Canary part ' + str(index)
        obj.dimensions = dimensions
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.data.materials.append(mat)
        bevel = obj.modifiers.new('Small edge chamfer', 'BEVEL')
        bevel.width = 0.003
        bevel.segments = 1
        bpy.ops.object.modifier_apply(modifier=bevel.name)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes():
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes()[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = brief['assetId']
    dims = brief['dimensionsM']
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    m = measure()
    obj.location -= Vector(((m['bboxMaxM'][0] + m['bboxMinM'][0])/2, (m['bboxMaxM'][1] + m['bboxMinM'][1])/2, m['bboxMinM'][2]))
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    center = Vector((0, 0, dims[2]/2))
    bpy.ops.object.camera_add(location=(0, -1, 0.5))
    camera = bpy.context.object
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = max(dims) * 1.65
    camera.data.clip_start = 0.0001
    camera.data.clip_end = 1000
    scene.camera = camera
    bpy.ops.object.light_add(type='AREA', location=(max(dims)*2, -max(dims)*2, max(dims)*3))
    bpy.context.object.data.energy = 8
    bpy.context.object.data.shape = 'DISK'
    bpy.context.object.data.size = max(dims)*3
    point_at(bpy.context.object, center)
    world = bpy.data.worlds.new('Canary world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.19, 0.19, 0.19, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = 0.65
    scene.world = world
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 8
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.resolution_x = 256
    scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'Standard'
    radius = max(dims)*3
    views = {'front': (0, -radius, center.z), 'side': (radius, 0, center.z), 'back': (0, radius, center.z),
             'three-quarter': (radius, -radius, center.z+radius*0.55), 'wireframe': (radius, -radius, center.z+radius*0.55)}
    camera.location = views['three-quarter']
    point_at(camera, center)
    bpy.ops.wm.save_as_mainfile(filepath=str(run / 'source.blend'), check_existing=False)
    write(run / 'source-metrics.json', measure())
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes():
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(run / 'asset.glb'), export_format='GLB', use_selection=True,
                              export_yup=True, export_apply=True, export_cameras=False, export_lights=False)

def render_reopened(run):
    # These views are evidence of the persisted .blend, rendered only after a
    # separate worker process has reopened that file with scripts disabled.
    dims = json.loads((run / 'brief.json').read_text())['dimensionsM']
    scene = bpy.context.scene
    camera = scene.camera
    center = Vector((0, 0, dims[2]/2))
    radius = max(dims)*3
    views = {'front': (0, -radius, center.z), 'side': (radius, 0, center.z), 'back': (0, radius, center.z),
             'three-quarter': (radius, -radius, center.z+radius*0.55), 'wireframe': (radius, -radius, center.z+radius*0.55)}
    (run / 'renders').mkdir()
    for view, location in views.items():
        camera.location = location
        point_at(camera, center)
        if view == 'wireframe':
            for obj in meshes():
                modifier = obj.modifiers.new('Wireframe QA', 'WIREFRAME')
                modifier.thickness = min(dims)*0.012
                modifier.use_replace = True
        scene.render.filepath = str(run / 'renders' / (view + '.png'))
        bpy.ops.render.render(write_still=True)
    write(run / 'render-provenance.json', {'stage': 'reopen', 'pid': os.getpid(),
                                          'loadedBlend': bpy.data.filepath,
                                          'sourceBlendSha256': hashlib.sha256((run / 'source.blend').read_bytes()).hexdigest(),
                                          'version': bpy.app.version_string, 'views': list(views)})

def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    if args[0] == 'topology-test':
        original = bmesh.new()
        bmesh.ops.create_cube(original, size=0.3)
        split = bmesh.new()
        for face in original.faces:
            split.faces.new([split.verts.new(v.co) for v in face.verts])
        raw = sum(not edge.is_manifold for edge in split.edges)
        bmesh.ops.remove_doubles(split, verts=list(split.verts), dist=0.000001)
        welded = sum(not edge.is_manifold for edge in split.edges)
        bmesh.ops.delete(split, geom=[next(iter(split.faces))], context='FACES_ONLY')
        hole = sum(not edge.is_manifold for edge in split.edges)
        original.free()
        split.free()
        if not (raw > 0 and welded == 0 and hole > 0):
            raise AssertionError('Topology seam/hole discrimination failed')
        print('CREATION_TOPOLOGY=' + json.dumps({'rawSeamEdges': raw, 'weldedClosedEdges': welded, 'realHoleEdges': hole}))
        return
    if args[0] == 'surface-test':
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.mesh.primitive_cube_add(size=0.3)
        obj = bpy.context.object
        obj.data.materials.append(material('A', (0.1, 0.2, 0.3)))
        obj.data.materials.append(material('B', (0.9, 0.8, 0.7)))
        for index, polygon in enumerate(obj.data.polygons):
            polygon.material_index = index % 2
        before = measure()
        for polygon in obj.data.polygons:
            polygon.material_index = 1 - polygon.material_index
        swapped = measure()
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        bm.free()
        reversed_mesh = measure()
        if not (before['geometrySignature'] == swapped['geometrySignature'] == reversed_mesh['geometrySignature']
                and before['surfaceSignature'] != swapped['surfaceSignature']
                and swapped['surfaceSignature'] != reversed_mesh['surfaceSignature']):
            raise AssertionError('Surface material/winding discrimination failed')
        print('CREATION_SURFACE=' + json.dumps({'materialSwapDetected': True, 'windingReversalDetected': True}))
        return
    if args[0] == 'probe':
        print('CREATION_BACKEND=' + json.dumps({'version': bpy.app.version_string, 'binaryPath': bpy.app.binary_path,
                                                'pythonVersion': sys.version, 'cpuOnly': True,
                                                'renderEngine': 'CYCLES', 'renderDevice': 'CPU', 'gpuRender': 'NOT_RUN'}))
        return
    run = Path(args[1]).resolve(strict=True)
    if args[0] == 'build':
        build(run)
    elif args[0] == 'reopen':
        bpy.ops.wm.open_mainfile(filepath=str(run / 'source.blend'), load_ui=False, use_scripts=False)
        write(run / 'reopened-metrics.json', measure())
        render_reopened(run)
    elif args[0] == 'import':
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(run / 'asset.glb'))
        write(run / 'imported-metrics.json', measure())
        # Add only the saved camera/light/world after clean import measurements.
        with bpy.data.libraries.load(str(run / 'source.blend'), link=False) as (available, loaded):
            loaded.objects = [name for name in available.objects if name in ('Camera', 'Area')]
            loaded.worlds = available.worlds
        scene = bpy.context.scene
        for obj in loaded.objects:
            scene.collection.objects.link(obj)
            if obj.type == 'CAMERA':
                scene.camera = obj
        scene.world = next(world for world in loaded.worlds if world.name.startswith('Canary world'))
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = 8
        scene.render.threads_mode = 'FIXED'
        scene.render.threads = 2
        scene.render.resolution_x = scene.render.resolution_y = 256
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.view_settings.view_transform = 'Standard'
        scene.render.filepath = str(run / 'renders' / 'reimport-three-quarter.png')
        bpy.ops.render.render(write_still=True)
    else:
        raise ValueError('Unknown worker stage')

if __name__ == '__main__':
    code = 0
    try:
        main()
    except Exception:
        traceback.print_exc()
        code = 1
    # bpy wheel teardown can crash. Explicit stage status and flush precede exit.
    sys.stdout.flush()
    sys.stderr.flush()
    if not bpy.app.binary_path:
        os._exit(code)
    raise SystemExit(code)
