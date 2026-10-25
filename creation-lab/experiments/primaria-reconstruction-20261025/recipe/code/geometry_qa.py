"""CPU Blender bridge: flatten a static GLB for inference, then restore physical space.

Invoked with the lab's isolated bpy Python. The host validates/copies provenance;
this worker accepts only owned copies and never opens the editable .blend source.
"""
import argparse
from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import sys
import traceback

import bpy
from mathutils import Matrix, Vector, kdtree

POSITION_TOLERANCE = 1e-5  # metres in original physical space
UV_TOLERANCE = 1e-6


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def glb_document(path):
    data = Path(path).read_bytes()
    if len(data) < 20 or data[:4] != b'glTF' or struct.unpack_from('<I', data, 4)[0] != 2:
        raise ValueError('Expected a GLB version 2')
    if struct.unpack_from('<I', data, 8)[0] != len(data):
        raise ValueError('GLB declared length differs from actual bytes')
    length, kind = struct.unpack_from('<II', data, 12)
    if kind != 0x4E4F534A or 20 + length > len(data):
        raise ValueError('Invalid GLB JSON chunk')
    doc = json.loads(data[20:20 + length])
    if any('uri' in entry for entry in doc.get('images', []) + doc.get('buffers', [])):
        raise ValueError('Only self-contained GLB resources are supported')
    if doc.get('animations'):
        raise ValueError('Animation is outside the static creation bridge contract')
    return doc


def load(path, *, static=False):
    doc = glb_document(path)
    if static and (doc.get('skins') or any('weights' in mesh for mesh in doc.get('meshes', []))
                   or any('targets' in primitive for mesh in doc.get('meshes', []) for primitive in mesh.get('primitives', []))):
        raise ValueError('Creation input must be static, without skins or morph targets')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # The default importer creates an Icosphere mesh solely for bone display.
    # Disable that generated helper; never exclude real content by object name.
    bpy.ops.import_scene.gltf(filepath=str(Path(path).resolve()), import_pack_images=True, disable_bone_shape=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.0
    for armature in (o for o in bpy.context.scene.objects if o.type == 'ARMATURE'):
        armature.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    return doc


def image_value(image):
    pixels = array('f', [0.0]) * len(image.pixels)
    image.pixels.foreach_get(pixels)
    if not pixels or not all(math.isfinite(value) for value in pixels):
        raise ValueError('Missing or non-finite texture pixels')
    return {'size': list(image.size), 'channels': image.channels,
            'pixelsSha256': hashlib.sha256(pixels.tobytes()).hexdigest(),
            'colorspace': image.colorspace_settings.name}


def rounded(value):
    if isinstance(value, (float, int)):
        if not math.isfinite(value):
            raise ValueError('Non-finite material value')
        return round(value, 5)
    return [rounded(v) for v in value]


def material_value(material, image_cache):
    if material is None:
        return {'unassigned': True}
    nodes = material.node_tree.nodes if material.use_nodes else []
    shader = next((node for node in nodes if node.type == 'BSDF_PRINCIPLED'), None)
    if shader is None:
        raise ValueError('Expected an imported glTF Principled PBR material')
    def socket_value(socket, trail):
        value = {'default': rounded(socket.default_value)} if hasattr(socket, 'default_value') else {}
        links = []
        for link in socket.links:
            node = link.from_node
            pointer = node.as_pointer()
            if pointer in trail:
                raise ValueError('Cyclic material graph is not supported')
            source = {'type': node.type, 'output': link.from_socket.identifier,
                      'inputs': [socket_value(item, trail | {pointer}) for item in node.inputs]}
            for key in ['operation', 'blend_type', 'data_type', 'clamp_type', 'use_clamp', 'uv_map', 'vector_type', 'space']:
                if hasattr(node, key):
                    source[key] = getattr(node, key)
            if node.type == 'TEX_IMAGE' and node.image:
                if node.image.as_pointer() not in image_cache:
                    image_cache[node.image.as_pointer()] = image_value(node.image)
                source.update(image=image_cache[node.image.as_pointer()], interpolation=node.interpolation,
                              extension=node.extension, projection=node.projection)
            links.append(source)
        value['links'] = links
        return value
    inputs = {}
    for name in ['Base Color', 'Metallic', 'Roughness', 'Alpha', 'Normal', 'Emission Color', 'Emission Strength']:
        socket = shader.inputs.get(name)
        if socket is not None:
            inputs[name] = socket_value(socket, set())
    textures = []
    for node in nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            if node.image.as_pointer() not in image_cache:
                image_cache[node.image.as_pointer()] = image_value(node.image)
            textures.append({'image': image_cache[node.image.as_pointer()], 'interpolation': node.interpolation,
                             'extension': node.extension, 'projection': node.projection})
    return {'inputs': inputs, 'textures': sorted(textures, key=lambda value: json.dumps(value, sort_keys=True)),
            'backfaceCulling': material.use_backface_culling}


def summary(snapshot):
    return {key: value for key, value in snapshot.items() if key != 'surfaces'}


def measure(coordinate_transform=None):
    transform = coordinate_transform if coordinate_transform is not None else Matrix.Identity(4)
    points, surfaces, material_values, images = [], [], {}, {}
    objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not objects:
        raise ValueError('No mesh in input')
    depsgraph = bpy.context.evaluated_depsgraph_get()
    vertex_count = 0
    for obj in objects:
        if not all(math.isfinite(v) for row in obj.matrix_world for v in row):
            raise ValueError('Non-finite object transform')
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        try:
            mesh.calc_loop_triangles()
            matrix = transform @ obj.matrix_world
            normal_matrix = matrix.to_3x3().inverted().transposed()
            world = [matrix @ vertex.co for vertex in mesh.vertices]
            vertex_count += len(world)
            points.extend(world)
            slot_keys = []
            for material in mesh.materials:
                value = material_value(material, images)
                key = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
                material_values[key] = value
                slot_keys.append(key)
            if not slot_keys:
                key = hashlib.sha256(b'unassigned').hexdigest()
                material_values[key] = {'unassigned': True}
                slot_keys.append(key)
            for triangle in mesh.loop_triangles:
                if triangle.material_index >= len(slot_keys):
                    raise ValueError('Invalid material slot index')
                corners = []
                for vertex_index, loop_index in zip(triangle.vertices, triangle.loops):
                    uvs = [list(layer.data[loop_index].uv) for layer in mesh.uv_layers]
                    normal = normal_matrix @ mesh.corner_normals[loop_index].vector
                    if normal.length < 1e-10:
                        raise ValueError('Degenerate shading normal')
                    normal.normalize()
                    corners.append([list(world[vertex_index]), uvs, list(normal)])
                surfaces.append([slot_keys[triangle.material_index], corners])
        finally:
            evaluated.to_mesh_clear()
    if not points or not surfaces or not all(math.isfinite(v) for point in points for v in point):
        raise ValueError('Empty or non-finite surface')
    lo = [min(point[i] for point in points) for i in range(3)]
    hi = [max(point[i] for point in points) for i in range(3)]
    used_materials = {surface[0] for surface in surfaces}
    return {'meshes': len(objects), 'vertices': vertex_count, 'triangles': len(surfaces),
            'bboxMinM': lo, 'bboxMaxM': hi, 'dimensionsM': [hi[i] - lo[i] for i in range(3)],
            'materials': {key: material_values[key] for key in sorted(used_materials)},
            'textureCount': len(images), 'surfaces': surfaces}


def compare_surfaces(expected, actual):
    """Match oriented triangles by position, semantic material and per-corner UVs.

    This tolerates vertex splits, triangle order and Blender's .001 renaming, but
    detects mirrored winding, lost components and material/UV reassignment.
    """
    if len(expected['surfaces']) != len(actual['surfaces']):
        return False, 'Triangle count changed'
    if expected['materials'] != actual['materials']:
        return False, 'PBR material values or decoded texture pixels changed'
    tree = kdtree.KDTree(len(expected['surfaces']))
    for index, (_, corners) in enumerate(expected['surfaces']):
        tree.insert(sum((Vector(corner[0]) for corner in corners), Vector()) / 3, index)
    tree.balance()
    remaining = set(range(len(expected['surfaces'])))
    for material, corners in actual['surfaces']:
        center = sum((Vector(corner[0]) for corner in corners), Vector()) / 3
        matched = None
        for _, index, _ in tree.find_range(center, POSITION_TOLERANCE * 2):
            expected_material, expected_corners = expected['surfaces'][index]
            if index not in remaining or material != expected_material:
                continue
            for shift in range(3):
                pairs = list(zip(expected_corners, corners[shift:] + corners[:shift]))
                positions_match = all((Vector(left[0]) - Vector(right[0])).length <= POSITION_TOLERANCE for left, right in pairs)
                uv_match = all(len(left[1]) == len(right[1]) and all(abs(a - b) <= UV_TOLERANCE
                               for luv, ruv in zip(left[1], right[1]) for a, b in zip(luv, ruv)) for left, right in pairs)
                normal_match = all(Vector(left[2]).dot(Vector(right[2])) >= 1 - 1e-5 for left, right in pairs)
                if positions_match and uv_match and normal_match:
                    matched = index
                    break
            if matched is not None:
                break
        if matched is None:
            return False, 'World-space oriented surface, material assignment, UV coordinates or shading normals changed'
        remaining.remove(matched)
    return True, 'All oriented triangles, materials and UVs match within physical-space tolerance'


def record(checks, name, passed, detail):
    checks.append({'name': name, 'status': 'passed' if passed else 'failed', 'detail': detail})


def compare(checks, name, expected, actual):
    passed, detail = compare_surfaces(expected, actual)
    record(checks, name, passed, detail)
    record(checks, name + '-bounds', all(abs(expected[key][i] - actual[key][i]) <= POSITION_TOLERANCE
           for key in ['bboxMinM', 'bboxMaxM', 'dimensionsM'] for i in range(3)),
           {'expected': expected['dimensionsM'], 'actual': actual['dimensionsM']})


def export(path):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type in {'MESH', 'ARMATURE', 'EMPTY'}:
            obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                              export_yup=True, export_animations=False, export_extras=False,
                              export_cameras=False, export_lights=False)
    glb_document(path)


def weights():
    failures, weighted, total, armatures = [], 0, 0, set()
    for obj in (o for o in bpy.context.scene.objects if o.type == 'MESH'):
        total += len(obj.data.vertices)
        modifiers = [m for m in obj.modifiers if m.type == 'ARMATURE' and m.show_viewport and m.object]
        if len(modifiers) != 1 or modifiers[0].object.type != 'ARMATURE':
            failures.append('Each mesh requires exactly one active armature modifier: ' + obj.name)
            continue
        armature = modifiers[0].object
        armatures.add(armature.name)
        valid_bones = {bone.name for bone in armature.data.bones if bone.use_deform}
        if not valid_bones or not all(math.isfinite(value) for bone in armature.data.bones for row in bone.matrix_local for value in row):
            failures.append('Missing deformation bones or non-finite bind matrices')
        groups = {group.index: group.name for group in obj.vertex_groups}
        for vertex in obj.data.vertices:
            values = [group.weight for group in vertex.groups if groups.get(group.group) in valid_bones]
            if any(not math.isfinite(value) or value < 0 for value in values) or abs(sum(values) - 1.0) > 1e-4:
                failures.append('Unweighted, invalid or non-normalized vertex: ' + obj.name + ':' + str(vertex.index))
            else:
                weighted += 1
    if not total or weighted != total:
        failures.append('Not every mesh vertex has valid deformation weights')
    return {'status': 'passed' if not failures else 'failed', 'vertices': total,
            'weightedVertices': weighted, 'armatures': len(armatures), 'failures': failures[:30]}


def matrices(value):
    forward = Matrix(value['matrix'])
    inverse = Matrix(value['inverse'])
    if len(forward) != 4 or len(inverse) != 4 or not all(math.isfinite(v) for matrix in [forward, inverse] for row in matrix for v in row):
        raise ValueError('Normalization matrices must be finite 4x4')
    product = forward @ inverse
    if max(abs(product[i][j] - float(i == j)) for i in range(4) for j in range(4)) > 1e-5:
        raise ValueError('Normalization inverse does not invert the forward matrix')
    if abs(forward.determinant()) < 1e-12:
        raise ValueError('Singular normalization matrix')
    return forward, inverse


def prepare(args):
    source_digest = digest(args.input)
    load(args.input, static=True)
    original = measure()
    lo, hi = Vector(original['bboxMinM']), Vector(original['bboxMaxM'])
    longest = max(hi - lo)
    if longest <= 1e-8:
        raise ValueError('Degenerate source dimensions')
    scale = 2.0 / longest
    center = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    normalization = Matrix.Scale(scale, 4) @ Matrix.Translation(-center)
    inverse = normalization.inverted()
    old_objects = list(bpy.context.scene.objects)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for index, obj in enumerate(o for o in old_objects if o.type == 'MESH'):
        mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph)
        mesh.transform(normalization @ obj.matrix_world)
        flattened = bpy.data.objects.new('creation-part-' + str(index), mesh)
        bpy.context.scene.collection.objects.link(flattened)
    for obj in old_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.update()
    normalized = measure()
    checks = []
    compare(checks, 'prepare-world-surface', original, measure(inverse))
    record(checks, 'normalized-space', abs(max(normalized['dimensionsM']) - 2.0) < 1e-5 and
           abs(normalized['bboxMinM'][2]) < 1e-5 and all(abs(normalized['bboxMinM'][i] + normalized['bboxMaxM'][i]) < 1e-5 for i in [0, 1]), summary(normalized))
    record(checks, 'flattened-transforms', all(obj.parent is None and all(abs(obj.matrix_world[i][j] - float(i == j)) < 1e-6
           for i in range(4) for j in range(4)) for obj in bpy.context.scene.objects), 'Every inference mesh is unparented with identity transform')
    export(args.output_dir / 'prepared.glb')
    load(args.output_dir / 'prepared.glb', static=True)
    imported = measure(inverse)
    compare(checks, 'prepare-export-reimport', original, imported)
    shutil.copy2(args.input, args.output_dir / 'control.glb')
    record(checks, 'source-unchanged', digest(args.input) == source_digest == digest(args.output_dir / 'control.glb'), source_digest)
    result = {'schemaVersion': 1, 'kind': 'creation-geometry', 'status': 'passed' if all(c['status'] == 'passed' for c in checks) else 'invalid_output',
              'blenderVersion': bpy.app.version_string, 'workerSha256': digest(__file__),
              'units': 'm', 'axes': {'blenderUp': '+Z', 'blenderFront': '-Y', 'gltfUp': '+Y', 'gltfFront': '+Z'},
              'normalization': {'matrix': [list(row) for row in normalization], 'inverse': [list(row) for row in inverse],
                                'scale': scale, 'center': list(center), 'rotation': 'identity', 'targetLongestDimensionM': 2.0},
              'tolerances': {'positionM': POSITION_TOLERANCE, 'uv': UV_TOLERANCE, 'weightSum': 1e-4},
              'sourceSha256': source_digest, 'source': original, 'prepared': summary(normalized), 'reimportedPhysicalSpace': summary(imported),
              'files': {name: {'file': name, 'sha256': digest(args.output_dir / name)} for name in ['prepared.glb', 'control.glb']},
              'checks': checks, 'visualReview': 'pending'}
    write(args.output_dir / 'geometry.json', result)
    write(args.report, {**result, 'source': summary(original)})
    return result


def restore(args):
    geometry = json.loads(args.geometry.read_text(encoding='utf-8'))
    if geometry.get('kind') != 'creation-geometry' or geometry.get('schemaVersion') != 1 or geometry.get('status') != 'passed':
        raise ValueError('Expected a passed creation-geometry manifest')
    _, inverse = matrices(geometry['normalization'])
    input_digest = digest(args.input)
    load(args.input)
    before = measure(inverse)
    weight_before = weights()
    checks = []
    compare(checks, 'merged-physical-surface', geometry['source'], before)
    record(checks, 'merged-weights', weight_before['status'] == 'passed', weight_before)
    # Root-only global transformation moves meshes and bind matrices together.
    # Transforming both an armature and its child mesh would apply it twice.
    roots = [(obj, obj.matrix_world.copy()) for obj in bpy.context.scene.objects if obj.parent is None]
    for obj, matrix in roots:
        obj.matrix_world = inverse @ matrix
    bpy.context.view_layer.update()
    restored = measure()
    compare(checks, 'restored-physical-surface', geometry['source'], restored)
    export(args.output_dir / 'restored.glb')
    load(args.output_dir / 'restored.glb')
    imported = measure()
    compare(checks, 'restore-export-reimport', geometry['source'], imported)
    weight_after = weights()
    record(checks, 'restored-weights', weight_after['status'] == 'passed', weight_after)
    record(checks, 'input-unchanged', digest(args.input) == input_digest, input_digest)
    result = {'schemaVersion': 1, 'kind': 'creation-restoration', 'status': 'passed' if all(c['status'] == 'passed' for c in checks) else 'invalid_output',
              'blenderVersion': bpy.app.version_string, 'workerSha256': digest(__file__), 'geometrySha256': digest(args.geometry),
              'inputSha256': input_digest, 'normalization': geometry['normalization'], 'source': summary(geometry['source']),
              'mergedPhysicalSpace': summary(before), 'restored': summary(restored), 'reimported': summary(imported),
              'weights': weight_after, 'checks': checks, 'visualReview': 'pending',
              'files': {'restored.glb': {'file': 'restored.glb', 'sha256': digest(args.output_dir / 'restored.glb')}}}
    write(args.report, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['prepare', 'restore']:
        command = sub.add_parser(name)
        command.add_argument('--input', type=Path, required=True)
        command.add_argument('--output-dir', type=Path, required=True)
        command.add_argument('--report', type=Path, required=True)
        if name == 'restore':
            command.add_argument('--geometry', type=Path, required=True)
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    args.input = args.input.resolve()
    args.output_dir = args.output_dir.resolve()
    args.report = args.report.resolve()
    if args.output_dir.exists() or args.report.exists():
        parser.error('Use a new output directory and report path; prior evidence is immutable')
    args.output_dir.mkdir(parents=True)
    try:
        result = {'prepare': prepare, 'restore': restore}[args.command](args)
    except Exception as error:
        traceback.print_exc()
        result = {'schemaVersion': 1, 'status': 'invalid_output', 'error': str(error), 'errorType': type(error).__name__}
        if not args.report.exists():
            write(args.report, result)
    print(json.dumps({'status': result['status'], 'report': str(args.report)}), flush=True)
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    code = main()
    # The pinned bpy 4.2 wheel has a known native teardown failure after import.
    # All reports and exports are closed before this exit with actual QA status.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
