"""Blender CPU review of native glTF and separately reopened packed GLB.

Run with --background --factory-startup --disable-autoexec --threads 2.
Source files and prepared GLBs are never edited by this reviewer.
"""
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_model(path):
    options = {'filepath': str(path)}
    if 'disable_bone_shape' in bpy.ops.import_scene.gltf.get_rna_type().properties:
        options['disable_bone_shape'] = True
    bpy.ops.import_scene.gltf(**options)
    if path.suffix == '.glb':
        import struct
        raw = path.read_bytes()
        length = struct.unpack_from('<I', raw, 12)[0]
        source = json.loads(raw[20:20 + length])
    else:
        source = json.loads(path.read_text(encoding='utf-8'))
    named_meshes = {n.get('name') for n in source.get('nodes', []) if 'mesh' in n}
    excluded = []
    for obj in list(bpy.context.scene.objects):
        if obj.type == 'MESH' and obj.name.startswith('Icosphere') and obj.name not in named_meshes:
            excluded.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    expected = sum('mesh' in n for n in source.get('nodes', []))
    if sum(o.type == 'MESH' for o in bpy.context.scene.objects) != expected:
        raise ValueError('Importer mesh count differs from source node inventory')
    return excluded


def geometry():
    bpy.context.view_layer.update()
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.hide_render]
    graph = bpy.context.evaluated_depsgraph_get()
    points = [o.matrix_world @ v.co for o in meshes for v in o.evaluated_get(graph).data.vertices]
    if not points or not all(math.isfinite(value) for p in points for value in p):
        raise ValueError('Missing or non-finite geometry')
    lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    if max(hi - lo) <= 0:
        raise ValueError('Empty model bounds')
    return meshes, lo, hi, {
        'dimensionsBlender': list(hi - lo), 'boundsMinBlender': list(lo), 'boundsMaxBlender': list(hi),
        'meshObjects': len(meshes), 'polygons': sum(len(o.data.polygons) for o in meshes),
        'vertices': sum(len(o.data.vertices) for o in meshes),
        'materials': len({m.name for o in meshes for m in o.data.materials if m}),
        'blenderVersion': bpy.app.version_string
    }


def render(path, azimuth=35, elevation=25, wire=False):
    meshes, lo, hi, stats = geometry()
    center, extent = (lo + hi) / 2, max(hi - lo)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 8
    scene.render.resolution_x = 320
    scene.render.resolution_y = 286
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('ReviewWorld')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.94, .93, .91, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .7
    scene.world = world
    created = []
    for name, offset, power in [('Key', (2, -3, 4), 450), ('Fill', (-3, -1, 2), 250)]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.shape, data.size = power * extent * extent, 'DISK', extent * 3
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = center + Vector(offset) * extent
        obj.rotation_euler = (center - obj.location).to_track_quat('-Z', 'Y').to_euler()
        created.append(obj)
    data = bpy.data.cameras.new('ReviewCamera')
    camera = bpy.data.objects.new('ReviewCamera', data)
    scene.collection.objects.link(camera)
    a, e = math.radians(azimuth), math.radians(elevation)
    camera.location = center + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * extent * 4
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    data.type, data.ortho_scale = 'ORTHO', extent * 1.5
    data.clip_start, data.clip_end = max(extent / 10000, .00001), max(extent * 100, 100)
    scene.camera = camera
    previous_override = scene.view_layers[0].material_override
    if wire:
        # A shader diagnostic leaves thin/disconnected source geometry untouched.
        material = bpy.data.materials.new('ReviewWireShader')
        material.use_nodes = True
        nodes, links = material.node_tree.nodes, material.node_tree.links
        shader = nodes.get('Principled BSDF')
        shader.inputs['Roughness'].default_value = .7
        edges = nodes.new('ShaderNodeWireframe')
        edges.use_pixel_size = True
        edges.inputs['Size'].default_value = .8
        mix = nodes.new('ShaderNodeMixRGB')
        mix.inputs[1].default_value = (.6, .65, .68, 1)
        mix.inputs[2].default_value = (.025, .025, .025, 1)
        links.new(edges.outputs[0], mix.inputs[0])
        links.new(mix.outputs[0], shader.inputs['Base Color'])
        scene.view_layers[0].material_override = material
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    scene.view_layers[0].material_override = previous_override
    for obj in created + [camera]:
        bpy.data.objects.remove(obj, do_unlink=True)
    return stats


run = Path(sys.argv[sys.argv.index('--') + 1])
acquired = json.loads((run / 'acquisition.json').read_text(encoding='utf-8'))
wire_only = '--wireframe-only' in sys.argv
review_directory = sys.argv[sys.argv.index('--review-directory') + 1] if '--review-directory' in sys.argv else 'prepared'
only_asset = sys.argv[sys.argv.index('--only-asset') + 1] if '--only-asset' in sys.argv else None
for item in acquired['items']:
    if only_asset and item['asset'] != only_asset:
        continue
    folder = run / review_directory / item['id']
    folder.mkdir(parents=True, exist_ok=True)
    if wire_only and (folder / 'review-v2.json').exists():
        continue
    if (folder / 'review.json').exists() and not wire_only:
        continue
    try:
        source = run / 'downloads' / item['asset'] / item['entryFile']
        glb = run / 'prepared' / item['id'] / 'model.glb'
        before = sha(glb)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        excluded_source = import_model(source)
        _, lo, hi, stats = geometry()
        if wire_only:
            assessment = json.loads((folder / 'review.json').read_text(encoding='utf-8'))
            assert assessment['glbSha256'] == before
            assert all(abs(a-b) < 1e-6 for a,b in zip(stats['dimensionsBlender'], assessment['dimensionsBlender']))
            render(folder / 'source-wireframe-v2.png', wire=True)
            assessment['images'].pop('source-wireframe.png', None)
            assessment['images']['source-wireframe-v2.png'] = sha(folder / 'source-wireframe-v2.png')
            assessment['wireframeDiagnostic'] = 'Clay wire shader; no geometry modifier. Earlier modifier diagnostic retained only in staging.'
            (folder / 'review-v2.json').write_text(json.dumps(assessment, indent=2) + '\n', encoding='utf-8')
            print('POLYHAVEN_WIRE_REVIEW', item['id'], flush=True)
            continue
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'source-review.blend'))
        for name, azimuth, elevation, wire in [
            ('source-three-quarter', 35, 25, False), ('source-front', 0, 0, False),
            ('source-side', 90, 0, False), ('source-back', 180, 0, False),
            ('source-wireframe', 35, 25, True)
        ]:
            render(folder / (name + '.png'), azimuth, elevation, wire)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        excluded_reimport = import_model(glb)
        _, rlo, rhi, reopened = geometry()
        tolerance = max(max(hi - lo) * .0001, .00001)
        if any(abs(a - b) > tolerance for a, b in zip(list(lo) + list(hi), list(rlo) + list(rhi))):
            raise ValueError('Source/reimport bounds changed')
        if any(stats[key] != reopened[key] for key in ['meshObjects', 'vertices', 'polygons', 'materials']):
            raise ValueError('Source/reimport structure changed')
        render(folder / 'reimport-three-quarter.png')
        assert sha(glb) == before
        stats.update(id=item['id'], sourceFile=item['entryFile'], glbSha256=before,
                     reimport=reopened, dimensionTolerance=tolerance,
                     importerHelpersExcluded={'source': excluded_source, 'reimport': excluded_reimport},
                     images={p.name: sha(p) for p in folder.glob('*.png')},
                     technical='PASS', visual='NOT_RUN')
        (folder / 'review.json').write_text(json.dumps(stats, indent=2) + '\n', encoding='utf-8')
        print('POLYHAVEN_REVIEW', item['id'], flush=True)
    except Exception as error:
        (folder / 'failure.json').write_text(json.dumps({'technical': 'FAIL', 'error': str(error)}) + '\n')
        print('POLYHAVEN_FAILED', item['id'], str(error), flush=True)
print('POLYHAVEN_REVIEW_COMPLETE', flush=True)
sys.stdout.flush()
sys.stderr.flush()
os._exit(0)
