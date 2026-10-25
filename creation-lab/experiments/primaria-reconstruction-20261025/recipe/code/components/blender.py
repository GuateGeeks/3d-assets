"""Blender adapter; bpy loads only when explicitly calling an adapter."""
import math
from .geometry import validate_mesh, _vector


def material(name, color, *, roughness=0.5, metallic=0.0):
    """Opaque Principled material, linear RGB in [0,1]."""
    import bpy
    color = _vector(color, "color")
    if any(not 0 <= x <= 1 for x in color):
        raise ValueError("color channels must be in [0, 1]")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0 <= x <= 1 for x in (roughness, metallic)):
        raise ValueError("roughness and metallic must be finite and in [0, 1]")
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Roughness'].default_value = roughness
    node.inputs['Metallic'].default_value = metallic
    return mat


def mesh_object(name, part_id, mesh, mat, *, collection=None, smooth=True, max_triangles=None):
    """Final MESH with part_id. Budget comes from the brief, never the robot.

    No modifiers or context operators. Explicit triangles freeze tessellation.
    Corner normals preserve shading through glTF, as observed in benchmark A/D.
    """
    import bpy
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a nonempty string")
    if mat is None or not mat.use_nodes or not any(n.type == 'BSDF_PRINCIPLED' for n in mat.node_tree.nodes):
        raise ValueError("A Principled material is required")
    validate_mesh(mesh, max_triangles=max_triangles)
    data = bpy.data.meshes.new(name+'__mesh')
    data.from_pydata(mesh.vertices, [], mesh.faces)
    data.materials.append(mat)
    for polygon in data.polygons:
        polygon.use_smooth = smooth
    data.update()
    normals = [tuple(n.vector) for n in data.corner_normals]
    data.normals_split_custom_set(normals)
    data.update()
    obj = bpy.data.objects.new(part_id+'__'+name, data)
    obj['part_id'] = part_id
    obj['component_library'] = 'creation-lab/components/v1'
    (collection or bpy.context.collection).objects.link(obj)
    return obj
