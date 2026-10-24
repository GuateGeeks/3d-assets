# ==== KIT (coordinador) · primitivas facetadas, paleta y registro de objetos ====
# Se concatena al inicio del generador final. Los módulos usan estos nombres
# sin importarlos. Sin bpy (python3 normal) obj() solo valida y registra.
import math
import random
from components import MeshData, validate_mesh, sphere

try:
    import bpy
    from components import material as _material, mesh_object as _mesh_object
except ImportError:  # comprobación pura de módulos
    bpy = None

# Unidades en metros. Z arriba, frente -Y. Superficie del terreno en Z = GROUND.
GROUND = -0.04

# Paleta Flat/Minimalist: hex sRGB -> RGB lineal para Principled.
PALETTE_HEX = {
    'pasto': '7DB65A', 'tierra': 'C9A27A', 'asfalto': '6E7681', 'banqueta': 'E6E1D6',
    'muro': 'F4E3C1', 'acento': 'E07A5F', 'teja': 'C8553D', 'vidrio': '8EC5E8',
    'blanco': 'F7F7F2', 'madera': '8B5E3C', 'oscuro': '2F3A45', 'celeste': '4997D0',
    'arcilla': 'E9A15B', 'balon': 'F08A24', 'follaje': '4E9F5D', 'follaje_claro': 'A6D46E',
    'tronco': '7A4E33', 'amarillo': 'F2C230', 'uniforme': '3C6EAF', 'piel': 'D9A47E',
}
PALETTE = {k: tuple(((int(v[i:i+2], 16)/255+0.055)/1.055)**2.4 if int(v[i:i+2], 16)/255 > 0.04045
                    else int(v[i:i+2], 16)/255/12.92 for i in (0, 2, 4)) for k, v in PALETTE_HEX.items()}
ANIM_KINDS = {'hinge', 'spin', 'sway', 'swing', 'bounce', 'path', 'drift', 'walk'}
REGISTRY = []      # (name, part_id, MeshData, color, anim) en modo puro
_MATERIALS = {}


# ---------- operaciones de malla ----------
def _centroid(vertices):
    n = len(vertices)
    return tuple(sum(v[k] for v in vertices)/n for k in range(3))


def _orient(vertices, faces):
    """Gira cada triángulo hacia fuera respecto al centroide (solo sólidos convexos)."""
    c = _centroid(vertices)
    out = []
    for a, b, d in faces:
        pa, pb, pd = vertices[a], vertices[b], vertices[d]
        u = [pb[k]-pa[k] for k in range(3)]
        w = [pd[k]-pa[k] for k in range(3)]
        n = (u[1]*w[2]-u[2]*w[1], u[2]*w[0]-u[0]*w[2], u[0]*w[1]-u[1]*w[0])
        m = [(pa[k]+pb[k]+pd[k])/3-c[k] for k in range(3)]
        out.append((a, b, d) if sum(n[k]*m[k] for k in range(3)) > 0 else (a, d, b))
    return MeshData(tuple(tuple(float(x) for x in v) for v in vertices), tuple(out))


def _quads(faces):
    tris = []
    for f in faces:
        if len(f) == 3:
            tris.append(tuple(f))
        else:
            for i in range(1, len(f)-1):
                tris.append((f[0], f[i], f[i+1]))
    return tris


def transform(mesh, *, scale=(1, 1, 1), rot_x=0.0, rot_y=0.0, rot_z=0.0, move=(0, 0, 0)):
    """Escala, rota (radianes, orden X->Y->Z, alrededor del origen local) y traslada."""
    out = []
    for x, y, z in mesh.vertices:
        x, y, z = x*scale[0], y*scale[1], z*scale[2]
        c, s = math.cos(rot_x), math.sin(rot_x); y, z = y*c-z*s, y*s+z*c
        c, s = math.cos(rot_y), math.sin(rot_y); x, z = x*c+z*s, -x*s+z*c
        c, s = math.cos(rot_z), math.sin(rot_z); x, y = x*c-y*s, x*s+y*c
        out.append((x+move[0], y+move[1], z+move[2]))
    faces = mesh.faces
    if scale[0]*scale[1]*scale[2] < 0:
        faces = tuple((a, c2, b) for a, b, c2 in faces)
    return MeshData(tuple(out), faces)


def merge(*meshes):
    """Une sólidos cerrados disjuntos en una sola malla (menos objetos)."""
    vertices, faces = [], []
    for m in meshes:
        base = len(vertices)
        vertices.extend(m.vertices)
        faces.extend(tuple(i+base for i in f) for f in m.faces)
    return MeshData(tuple(vertices), tuple(faces))


# ---------- primitivas cerradas y facetadas ----------
def box(size, center=(0, 0, 0), rot_z=0.0):
    """Caja de tamaño (sx, sy, sz) centrada en center; rot_z en radianes."""
    sx, sy, sz = (s/2 for s in size)
    v = [(x, y, z) for z in (-sz, sz) for y in (-sy, sy) for x in (-sx, sx)]
    f = _quads([(0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5)])
    return transform(_orient(v, f), rot_z=rot_z, move=center)


def box_on(size, x, y, z0, rot_z=0.0):
    """Caja apoyada: base en z0."""
    return box(size, (x, y, z0+size[2]/2), rot_z)


def frustum(r_bottom, r_top, height, base=(0, 0, 0), segments=8, phase=0.0, axis='Z'):
    """Cilindro (r_top=r_bottom), cono (r_top=0) o tronco; tapas cerradas.
    axis 'Z' crece hacia +Z desde base; 'X'/'Y' crece hacia +X/+Y."""
    v, f = [], []
    for r, z in ((r_bottom, 0.0), (r_top, height)):
        if r > 0:
            for i in range(segments):
                a = phase+math.tau*i/segments
                v.append((r*math.cos(a), r*math.sin(a), z))
    n = segments
    if r_top > 0:
        for i in range(n):
            j = (i+1) % n
            f += [(i, j, n+j), (i, n+j, n+i)]
        cb, ct = len(v), len(v)+1
        v += [(0, 0, 0), (0, 0, height)]
        f += [(cb, i, (i+1) % n) for i in range(n)] + [(ct, n+i, n+(i+1) % n) for i in range(n)]
    else:
        apex, cb = len(v), len(v)+1
        v += [(0, 0, height), (0, 0, 0)]
        f += [(i, (i+1) % n, apex) for i in range(n)] + [(cb, i, (i+1) % n) for i in range(n)]
    m = _orient(v, f)
    if axis == 'X':
        m = transform(m, rot_y=math.pi/2)
    elif axis == 'Y':
        m = transform(m, rot_x=-math.pi/2)
    return transform(m, move=base)


def cylinder(radius, height, base=(0, 0, 0), segments=8, axis='Z', phase=0.0):
    return frustum(radius, radius, height, base, segments, phase, axis)


def cone(radius, height, base=(0, 0, 0), segments=8, phase=0.0):
    return frustum(radius, 0.0, height, base, segments, phase)


def pyramid(size_x, size_y, height, base=(0, 0, 0)):
    """Pirámide rectangular (techo de torre) con base centrada en base."""
    hx, hy = size_x/2, size_y/2
    v = [(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0), (0, 0, height)]
    f = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (0, 2, 1), (0, 3, 2)]
    return transform(_orient(v, f), move=base)


def gable(length_x, depth_y, height, base=(0, 0, 0), overhang=0.0):
    """Techo a dos aguas: cumbrera paralela a X, base rectangular centrada en base."""
    hx, hy = length_x/2+overhang, depth_y/2+overhang
    v = [(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0), (-hx, 0, height), (hx, 0, height)]
    f = _quads([(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)])
    return transform(_orient(v, f), move=base)


def blob(radii, center=(0, 0, 0), segments=7, rings=5):
    """Esfera low-poly (copas, nubes, cabezas, balón)."""
    return sphere(radii, center=center, segments=segments, rings=rings)


# ---------- materiales y objetos ----------
def mat(key):
    if key not in PALETTE:
        raise ValueError('Color fuera de la paleta: ' + key)
    if bpy is None:
        return key
    if key not in _MATERIALS:
        _MATERIALS[key] = _material('flat_' + key, PALETTE[key], roughness=0.92, metallic=0.0)
    return _MATERIALS[key]


def obj(name, part_id, mesh, color, anim=None):
    """Crea el objeto final facetado. anim (opcional) describe su movimiento:
    {'clip': str, 'kind': uno de ANIM_KINDS, 'pivot': [x,y,z], 'axis': 'X'|'Y'|'Z',
     'params': {...}}  -> ver CONTRACT.md. Devuelve el objeto (o el nombre en modo puro)."""
    validate_mesh(mesh)
    if anim is not None:
        if not isinstance(anim, dict) or anim.get('kind') not in ANIM_KINDS or not anim.get('clip'):
            raise ValueError('anim inválido en ' + name)
        if len(anim.get('pivot', ())) != 3:
            raise ValueError('anim.pivot requerido en ' + name)
        for key, value in anim.get('params', {}).items():
            flat = value if isinstance(value, list) else [value]
            if not all(isinstance(x, (int, float, str)) and not isinstance(x, bool) for x in flat):
                raise ValueError(f'anim.params.{key} debe ser número, texto o lista plana de números en ' + name)
    if bpy is None:
        REGISTRY.append((name, part_id, mesh, color, anim))
        mat(color)
        return name
    o = _mesh_object(name, part_id, mesh, mat(color), smooth=False)
    if anim is not None:
        o['anim_clip'] = anim['clip']
        o['anim_kind'] = anim['kind']
        o['anim_pivot'] = [float(x) for x in anim['pivot']]
        o['anim_axis'] = anim.get('axis', 'Z')
        o['anim_params'] = anim.get('params', {})
    return o
# ==== FIN KIT ====
