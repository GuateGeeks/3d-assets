"""Small deterministic CPU-only static and weighted GLB fixtures; no learned model."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback
import bpy
from mathutils import Matrix, Vector


def export(path):
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', export_yup=True, export_animations=False)


def static(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    image = bpy.data.images.new('Embedded 2x2 calibration', width=2, height=2, alpha=True)
    image.pixels[:] = [1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1]
    image.file_format = 'PNG'
    image.pack()
    materials = []
    for index in range(2):
        mat = bpy.data.materials.new('Same material name')
        mat.use_nodes = True
        shader = mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Roughness'].default_value = 0.4 + index * 0.2
        shader.inputs['Base Color'].default_value = (0.15, 0.5, 0.7, 1)
        if index == 0:
            node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            node.image = image
            mat.node_tree.links.new(node.outputs['Color'], shader.inputs['Base Color'])
        materials.append(mat)
    parent = bpy.data.objects.new('Non-identity hierarchy', None)
    bpy.context.scene.collection.objects.link(parent)
    parent.rotation_euler = (0.2, 0.3, 0.4)
    parent.scale = (1.4, 0.7, 1.1)
    for index in range(2):
        bpy.ops.mesh.primitive_cube_add(size=1)
        obj = bpy.context.object
        obj.name = 'Part ' + str(index)
        obj.parent = parent
        obj.location = (index * 0.85 - 0.25, 0.1, index * 0.3)
        obj.rotation_euler = (0.1 * index, 0.2, -0.15)
        obj.scale = (0.5, 0.35 + index * 0.15, 0.7)
        for material in materials:
            obj.data.materials.append(material)
        for polygon in obj.data.polygons:
            polygon.material_index = polygon.index % 2
    bpy.context.view_layer.update()
    points = [obj.matrix_world @ vertex.co for obj in bpy.context.scene.objects if obj.type == 'MESH' for vertex in obj.data.vertices]
    longest = max(max(v[i] for v in points) - min(v[i] for v in points) for i in range(3))
    parent.matrix_world = Matrix.Translation((0.7, -0.2, 1.1)) @ Matrix.Scale(0.3 / longest, 4) @ parent.matrix_world
    bpy.context.view_layer.update()
    export(path)


def weighted(source, output, broken):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    armature = bpy.data.objects.new('Deterministic rig', bpy.data.armatures.new('Fixture bones'))
    bpy.context.scene.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    root = armature.data.edit_bones.new('Lower')
    root.head = (0, 0, 0)
    root.tail = (0, 0, 1)
    upper = armature.data.edit_bones.new('Upper')
    upper.head = (0, 0, 1)
    upper.tail = (0, 0, 2)
    upper.parent = root
    bpy.ops.object.mode_set(mode='OBJECT')
    for index, obj in enumerate(objects):
        if broken == 'unweighted' and index == len(objects) - 1:
            continue
        world = obj.matrix_world.copy()
        obj.parent = armature
        obj.matrix_world = world
        modifier = obj.modifiers.new('Fixture skin', 'ARMATURE')
        modifier.object = armature
        low = obj.vertex_groups.new(name='Lower')
        high = obj.vertex_groups.new(name='Upper')
        for vertex in obj.data.vertices:
            (low if (world @ vertex.co).z < 1 else high).add([vertex.index], 1.0, 'REPLACE')
    # Parent hierarchy has a non-identity transform while rig and mesh remain at
    # their original world coordinates. Restore must transform this root once.
    parent = bpy.data.objects.new('Rig parent offset', None)
    bpy.context.scene.collection.objects.link(parent)
    parent.location = (0.4, -0.8, 0.3)
    parent.rotation_euler = (0.2, -0.1, 0.4)
    parent.scale = (1.1, 1.1, 1.1)
    bpy.context.view_layer.update()
    armature.parent = parent
    armature.matrix_world = Matrix.Identity(4)
    bpy.context.view_layer.update()
    if broken == 'uv':
        objects[0].data.uv_layers[0].data[0].uv.x += 0.15
    if broken == 'material':
        material = next(mat for obj in objects for mat in obj.data.materials if mat)
        material.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = 0.99
    export(output)


def appearance_regression(output, broken):
    """Reproduce QA false positives without exporting or changing production code."""
    sys.dont_write_bytecode = True
    worker = Path(__file__).resolve().parents[1] / 'scripts/creation_geometry.py'
    spec = importlib.util.spec_from_file_location('creation_geometry_under_test', worker)
    geometry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(geometry)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=0.3)
    obj = bpy.context.object
    material = bpy.data.materials.new('Routing regression')
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    texture_nodes = []
    for name, color in [('Red', (1, 0, 0, 1)), ('Blue', (0, 0, 1, 1))]:
        image = bpy.data.images.new(name, width=1, height=1, alpha=True)
        image.pixels[:] = color
        node = material.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = image
        texture_nodes.append(node)
    links = material.node_tree.links
    links.new(texture_nodes[0].outputs['Color'], shader.inputs['Base Color'])
    links.new(texture_nodes[1].outputs['Color'], shader.inputs['Roughness'])
    obj.data.materials.append(material)
    bpy.context.view_layer.update()
    before = geometry.measure()
    if broken == 'routing':
        # Both sockets stay linked and both images/pixels remain unchanged.
        for socket in [shader.inputs['Base Color'], shader.inputs['Roughness']]:
            for link in list(socket.links):
                links.remove(link)
        links.new(texture_nodes[1].outputs['Color'], shader.inputs['Base Color'])
        links.new(texture_nodes[0].outputs['Color'], shader.inputs['Roughness'])
    elif broken == 'normals':
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        obj.data.update()
    else:
        raise ValueError('Appearance regression requires routing or normals')
    bpy.context.view_layer.update()
    after = geometry.measure()
    def image_pixels(snapshot):
        return sorted({texture['image']['pixelsSha256'] for value in snapshot['materials'].values() for texture in value['textures']})
    def coordinates_uv(snapshot):
        return [[corner[:2] for corner in corners] for _, corners in snapshot['surfaces']]
    accepted, reason = geometry.compare_surfaces(before, after)
    output.write_text(json.dumps({'case': broken, 'baselineAccepted': geometry.compare_surfaces(before, before)[0],
        'mutationAccepted': accepted, 'reason': reason,
        'coordinatesAndUvUnchanged': coordinates_uv(before) == coordinates_uv(after),
        'materialsEqual': before['materials'] == after['materials'],
        'textureImageCount': len(image_pixels(before)), 'texturePixelsUnchanged': image_pixels(before) == image_pixels(after),
        'bothSocketsStillLinked': shader.inputs['Base Color'].is_linked and shader.inputs['Roughness'].is_linked,
        'normalsChanged': [[corner[2] for corner in corners] for _, corners in before['surfaces']] !=
                          [[corner[2] for corner in corners] for _, corners in after['surfaces']]}, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['static', 'weighted', 'appearance-regression'])
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--broken', choices=['unweighted', 'uv', 'material', 'routing', 'normals'])
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    if args.kind == 'static':
        static(args.output)
    elif args.kind == 'weighted':
        weighted(args.input, args.output, args.broken)
    else:
        appearance_regression(args.output, args.broken)


if __name__ == '__main__':
    try:
        main()
        code = 0
    except Exception:
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
