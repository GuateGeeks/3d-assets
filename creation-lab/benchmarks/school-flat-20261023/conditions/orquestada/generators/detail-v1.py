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


# ==== MÓDULO entorno · module_entorno.py · sha256 eff736fd7e8d1be0f1ae4887c6815e9d243ec06d66916a8dc259eb97aa5de68e ====
# ==== MÓDULO ENTORNO (DETALLE) · terreno, calle/banqueta/cebra y bus escolar ====
# Partes: terreno, camino, autobus. Sin imports; usa solo primitivas del kit.
# Bus: centro estático y pivote en (0.060, -0.133); recorrido que empieza y termina en el pivote.


def _entorno_bus_anim():
    """Circuito cerrado del bus por la calle, empezando en el pivote: carril delantero hacia +X,
    vuelta en U, carril trasero hacia -X, vuelta en U."""
    return {
        'clip': 'autobus',
        'kind': 'path',
        'pivot': [0.060, -0.133, -0.0385],
        'axis': 'Z',
        'params': {
            'forward': '+X',
            'period': 14,
            'points': [
                0.060, -0.133, -0.0385,
                0.15, -0.133, -0.0385,
                0.165, -0.126, -0.0385,
                0.15, -0.117, -0.0385,
                -0.15, -0.117, -0.0385,
                -0.165, -0.126, -0.0385,
                -0.15, -0.133, -0.0385,
                -0.08, -0.133, -0.0385,
                0.060, -0.133, -0.0385,
            ],
        },
    }


def _entorno_bushes():
    """Matas bajas junto al borde trasero y lateral, lejos de los árboles."""
    spots = [(-0.150, 0.142), (-0.090, 0.142), (-0.030, 0.142), (0.030, 0.142),
             (0.090, 0.142), (0.150, 0.142), (-0.193, 0.075), (0.193, 0.075)]
    return merge(*[blob((0.006, 0.006, 0.005), center=(x, y, GROUND + 0.005), segments=6, rings=4)
                   for x, y in spots])


def _entorno_dashes():
    """Línea central discontinua: rectángulos de 0.012 x 0.0016, pitch 0.022. Se omiten los dos
    que caen en el paso de cebra para que no se toquen."""
    parts = []
    for i in range(18):
        if i in (8, 9):
            continue
        cx = -0.187 + i * 0.022
        parts.append(box((0.012, 0.0016, 0.0012), center=(cx, -0.126, -0.0384)))
    return merge(*parts)


def _entorno_zebra():
    """Paso de cebra: 5 franjas paralelas a Y, 0.0036 de ancho, 0.0006 por encima del asfalto."""
    stripes = [box((0.0036, 0.0416, 0.0011), center=(x, -0.1260, -0.03845))
               for x in (-0.0112, -0.0056, 0.0, 0.0056, 0.0112)]
    return merge(*stripes)


def _entorno_wheel(x, y0):
    """Rueda: cilindro de 8 lados, eje Y, radio 0.0045, grosor 0.003, apoyada en el asfalto."""
    return cylinder(0.0045, 0.003, base=(x, y0, -0.034), segments=8, axis='Y')


def _entorno_bus_body(xc):
    """Carrocería amarilla: caja principal más cofre delantero más bajo."""
    main = box((0.060, 0.024, 0.0235), center=(xc - 0.005, -0.133, -0.02225))
    hood = box((0.0115, 0.024, 0.0165), center=(xc + 0.02925, -0.133, -0.02550))
    return merge(main, hood)


def _entorno_bus_details(xc):
    """Franja oscura, ruedas, parachoques y letrero liso en el techo (todo 'oscuro')."""
    stripes = [box((0.056, 0.0012, 0.0025), center=(xc - 0.005, yf, -0.02775)) for yf in (-0.145, -0.121)]
    wheels = [_entorno_wheel(xc + dx, y0) for dx in (-0.026, 0.026) for y0 in (-0.1468, -0.1222)]
    bumpers = [box((0.0016, 0.026, 0.0030), center=(xc + sx * 0.0358, -0.133, -0.0355))
               for sx in (1, -1)]
    sign = box((0.014, 0.010, 0.0020), center=(xc, -0.133, -0.0097))
    return merge(*stripes, *wheels, *bumpers, sign)


def _entorno_bus_glass(xc):
    """Ventanas laterales (cajas que sobresalen 0.0006 a cada lado) y parabrisas."""
    windows = []
    for yf in (-0.145, -0.121):
        for dx in (-0.030, -0.016, -0.002, 0.012):
            windows.append(box((0.010, 0.0012, 0.011), center=(xc + dx + 0.005, yf, -0.019)))
    windshield = box((0.0012, 0.018, 0.005), center=(xc + 0.025, -0.133, -0.0145))
    return merge(*windows, windshield)


def _entorno_bus_lights(xc):
    """Luces delanteras blancas sobre la cara frontal del cofre."""
    return merge(*[box((0.0012, 0.0035, 0.0025), center=(xc + 0.035, -0.133 + sy * 0.0070, -0.0262))
                   for sy in (1, -1)])


def _entorno_bus_taillights(xc):
    """Luces traseras de acento sobre la cara trasera de la caja principal."""
    return merge(*[box((0.0012, 0.0035, 0.0025), center=(xc - 0.035, -0.133 + sy * 0.0070, -0.0262))
                   for sy in (1, -1)])


def module_entorno():
    xc = 0.060
    obj('tierra', 'terreno', box((0.40, 0.30, 0.012), center=(0, 0, -0.050)), 'tierra')
    obj('pasto', 'terreno', box((0.40, 0.30, 0.004), center=(0, 0, -0.042)), 'pasto')
    obj('matas', 'terreno', _entorno_bushes(), 'follaje_claro')

    obj('asfalto', 'camino', box((0.40, 0.042, 0.0015), center=(0, -0.126, -0.03925)), 'asfalto')
    obj('linea_central', 'camino', merge(_entorno_dashes(), _entorno_zebra()), 'blanco')
    obj('banqueta', 'camino', merge(
        box((0.40, 0.012, 0.0025), center=(0, -0.099, -0.03875)),
        box((0.028, 0.083, 0.0015), center=(0, -0.0515, -0.03925))), 'banqueta')

    obj('bus_carroceria', 'autobus', _entorno_bus_body(xc), 'amarillo', _entorno_bus_anim())
    obj('bus_detalles', 'autobus', _entorno_bus_details(xc), 'oscuro', _entorno_bus_anim())
    obj('bus_vidrio', 'autobus', _entorno_bus_glass(xc), 'vidrio', _entorno_bus_anim())
    obj('bus_luces', 'autobus', _entorno_bus_lights(xc), 'blanco', _entorno_bus_anim())
    obj('bus_luces_traseras', 'autobus', _entorno_bus_taillights(xc), 'acento', _entorno_bus_anim())

    return {
        'terreno': {'label_position': [0.035, -0.088, -0.040]},
        'camino': {'label_position': [0.0, -0.126, -0.0379]},
        'autobus': {'label_position': [xc, -0.133, -0.0087]},
    }
# ==== FIN MÓDULO ENTORNO (DETALLE) ====


# ==== MÓDULO edificio · module_edificio.py · sha256 f484d19940ce97127ce3ce8834f9ca76fec9d39d40a6816e6cc6b1d980a55634 ====
# module_edificio: edificio, techo, ventanas, puerta, torre_reloj (diorama escuela).
# Plano: huella X[-0.10,0.10] Y[0,0.075], Z GROUND..0.030; torre X[-0.022,0.022] Y[-0.010,0.030].


def _edificio_window(w, h, side, cx, cy, cz):
    """Ventana centrada en (cx,cy,cz) sobre una pared. side: 'F' (cara -Y), 'L' (-X), 'R' (+X).
    Construida sobre el plano y=0 y rotada. Marco: 4 barras + travesaño, sobresale 0.0012;
    vidrio hundido 0.0006 por delante de la pared (sobresale 0.0006), detrás del marco."""
    t, fy = 0.0015, 0.0012
    bars = [box((w, fy, t), (0, -fy/2, h/2-t/2)), box((w, fy, t), (0, -fy/2, -h/2+t/2)),
            box((t, fy, h-2*t), (-w/2+t/2, -fy/2, 0)), box((t, fy, h-2*t), (w/2-t/2, -fy/2, 0)),
            box((t*0.8, fy, h-2*t), (0, -fy/2, 0))]
    glass = box((w-2*t, 0.0006, h-2*t), (0, -0.0003, 0))
    rz = {'F': 0.0, 'L': -math.pi/2, 'R': math.pi/2, 'B': math.pi}[side]
    mv = (cx, cy, cz)
    return (merge(*[transform(b, rot_z=rz, move=mv) for b in bars]),
            transform(glass, rot_z=rz, move=mv))


def module_edificio():
    G = GROUND
    # ---------- edificio ----------
    muros = box((0.2, 0.075, 0.07), (0, 0.0375, (G+0.030)/2))
    obj('edificio_muros', 'edificio', muros, 'muro')
    zoc = box((0.202, 0.077, 0.0095), (0, 0.0375, G-0.0005+0.0095/2))
    banda = box((0.202, 0.077, 0.003), (0, 0.0375, -0.005))
    obj('edificio_acentos', 'edificio', merge(zoc, banda), 'acento')
    cornisa = box((0.204, 0.079, 0.0035), (0, 0.0375, 0.02825))
    pil = []
    for x, w in ((-0.0975, 0.005), (0.0975, 0.005), (-0.0595, 0.003), (0.0595, 0.003)):
        pil.append(box((w, 0.0015, 0.0580), (x, -0.00075, -0.031+0.0580/2)))
    obj('edificio_cornisa_pilastras', 'edificio', merge(cornisa, *pil), 'blanco')
    # escalones (y -0.020..-0.010), 2 peldaños; puerta abre por encima (base de hoja en -0.0375)
    e1 = box((0.032, 0.005, 0.0025), (0, -0.0175, G-0.0005+0.0025/2 - 0.0005 + 0.0005))
    e2 = box((0.032, 0.0055, 0.0035), (0, -0.01275, G-0.0005+0.0035/2))
    obj('edificio_escalones', 'edificio', merge(e1, e2), 'banqueta')
    # rótulo liso sobre la puerta
    obj('edificio_rotulo', 'edificio', box((0.024, 0.0012, 0.004), (0, -0.0106, -0.0065)), 'celeste')
    # marquesina sobre el rótulo (por encima de la hoja: la puerta abre sin tocarla)
    obj('edificio_marquesina', 'edificio', box((0.030, 0.0025, 0.0012), (0, -0.01125, -0.0039)), 'acento')
    # rebaje oscuro detrás de la puerta (caja que sobresale 0.0005 de la torre; se ve al abrir)
    obj('edificio_rebaje', 'edificio', box((0.019, 0.0006, 0.0275), (0, -0.0103, -0.02425)), 'oscuro')

    # ---------- techo ----------
    obj('techo_gable', 'techo', gable(0.2, 0.075, 0.028, (0, 0.0375, 0.030), overhang=0.006), 'teja')
    # caballete blanco a lo largo de la cumbrera y frontones laterales cerrados (misma pendiente del techo)
    cab = box((0.214, 0.005, 0.0022), (0, 0.0375, 0.0580))
    fr = [gable(0.001, 0.087, 0.028, (sx*0.1065, 0.0375, 0.030)) for sx in (-1, 1)]
    obj('techo_caballete_frontones', 'techo', merge(cab, *fr), 'blanco')
    # chimenea pequeña en el ala derecha (atraviesa el faldón trasero)
    obj('techo_chimenea', 'techo', box((0.008, 0.008, 0.026), (0.075, 0.052, 0.053)), 'acento')

    # ---------- ventanas ----------
    frames, glasses = [], []
    for zc in (-0.0205, 0.0085):
        for x in (-0.085, -0.068, -0.051, -0.034, 0.034, 0.051, 0.068, 0.085):
            f, g = _edificio_window(0.012, 0.016, 'F', x, 0.0, zc)
            frames.append(f); glasses.append(g)
        for x in (-0.075, -0.045, -0.015, 0.015, 0.045, 0.075):
            f, g = _edificio_window(0.012, 0.016, 'B', x, 0.075, zc)
            frames.append(f); glasses.append(g)
        for y in (0.025, 0.050):
            for side, x in (('L', -0.1), ('R', 0.1)):
                f, g = _edificio_window(0.012, 0.016, side, x, y, zc)
                frames.append(f); glasses.append(g)
    sills = []
    for zc in (-0.0205, 0.0085):
        for x in (-0.085, -0.068, -0.051, -0.034, 0.034, 0.051, 0.068, 0.085):
            sills.append(box((0.014, 0.0015, 0.0015), (x, -0.00075, zc-0.008-0.00075)))
        for x in (-0.075, -0.045, -0.015, 0.015, 0.045, 0.075):
            sills.append(box((0.014, 0.0015, 0.0015), (x, 0.075+0.00075, zc-0.008-0.00075)))
    obj('ventanas_marcos', 'ventanas', merge(*frames, *sills), 'blanco')
    obj('ventanas_vidrios', 'ventanas', merge(*glasses), 'vidrio')

    # ---------- puerta ----------
    # Hoja en y[-0.0123,-0.0108], base elevada a -0.0375 para pasar sobre los escalones.
    # Signo: +angle gira CCW visto desde arriba (hacia +Y, adentro); se usa -100 para abrir hacia -Y.
    door_anim = {'clip': 'puerta', 'kind': 'hinge', 'pivot': [-0.010, -0.0115, G], 'axis': 'Z',
                 'params': {'angle_deg': -100, 'period': 3.0}}
    z0, z1 = G+0.0025, G+0.030
    zm = (z0+z1)/2
    hoja = box((0.020, 0.0015, z1-z0), (0, -0.01155, zm))
    p1 = box((0.013, 0.0005, 0.0105), (0, -0.01255+0.00005, z0+0.0075))
    p2 = box((0.013, 0.0005, 0.0105), (0, -0.01255+0.00005, z1-0.0075))
    obj('puerta_hoja', 'puerta', merge(hoja, p1, p2), 'madera', door_anim)
    obj('puerta_manija', 'puerta', box((0.0016, 0.0010, 0.0016), (0.0075, -0.0128, zm)), 'amarillo', door_anim)

    # ---------- torre del reloj ----------
    obj('torre_cuerpo', 'torre_reloj', box((0.044, 0.040, 0.125), (0, 0.010, (G+0.085)/2)), 'muro')
    b1 = box((0.047, 0.043, 0.003), (0, 0.010, 0.0415))
    b2 = box((0.047, 0.043, 0.003), (0, 0.010, 0.0835))
    obj('torre_bandas', 'torre_reloj', merge(b1, b2), 'acento')
    obj('torre_techo', 'torre_reloj', pyramid(0.052, 0.048, 0.030, (0, 0.010, 0.085)), 'teja')
    cz = 0.065
    obj('reloj_esfera', 'torre_reloj', cylinder(0.012, 0.0015, (0, -0.01125, cz), 12, 'Y'), 'blanco')
    obj('reloj_aro', 'torre_reloj', cylinder(0.0135, 0.0010, (0, -0.0107, cz), 12, 'Y'), 'oscuro')
    marks = []
    for k in range(12):
        a = math.tau*k/12
        px, pz = 0.0095*math.sin(a), 0.0095*math.cos(a)
        sz = (0.0014, 0.0006, 0.0024) if k % 3 == 0 else (0.0010, 0.0006, 0.0010)
        rot = 0.0 if k % 3 == 0 and k % 6 == 0 else 0.0
        if k % 6 == 3:
            sz = (0.0024, 0.0006, 0.0014)
        marks.append(box(sz, (px, -0.01155, cz+pz)))
    obj('reloj_marcas', 'torre_reloj', merge(*marks), 'oscuro')
    rej = [box((0.008, 0.0006, 0.0022), (0, -0.0103, 0.0803)),
           box((0.0006, 0.008, 0.012), (-0.0223, 0.010, 0.060)),
           box((0.0006, 0.008, 0.012), (0.0223, 0.010, 0.060))]
    obj('torre_campanario', 'torre_reloj', merge(*rej), 'oscuro')
    # Convención: direction +1 = giro positivo alrededor de +Y = sentido horario visto de frente (desde -Y).
    # Pose inicial: minutero a las 12, horaria a las 3.
    obj('reloj_minutero', 'torre_reloj', box((0.0012, 0.0010, 0.0105), (0, -0.0127, cz+0.0045)), 'oscuro',
        {'clip': 'reloj', 'kind': 'spin', 'pivot': [0, -0.0127, cz], 'axis': 'Y',
         'params': {'period': 6, 'direction': 1}})
    obj('reloj_horario', 'torre_reloj', box((0.0066, 0.0008, 0.0016), (0.003, -0.0119, cz)), 'oscuro',
        {'clip': 'reloj', 'kind': 'spin', 'pivot': [0, -0.0119, cz], 'axis': 'Y',
         'params': {'period': 72, 'direction': 1}})

    return {'edificio': {'label_position': [0.070, -0.003, 0.010]},
            'techo': {'label_position': [0.060, 0.022, 0.049]},
            'ventanas': {'label_position': [-0.06, -0.004, 0.022]},
            'puerta': {'label_position': [0.0, -0.016, -0.004]},
            'torre_reloj': {'label_position': [0.0, 0.01, 0.12]}}


# ==== MÓDULO patio · module_patio.py · sha256 c8841b0e479e15ec70e60f0684f8b49d697c21d59196d7840ca31e5d7684b57b ====
_patio_line_w = 0.0012
_patio_line_h = 0.0008
_patio_surf_top = GROUND + 0.0015
_patio_border_w = 0.0015


def _patio_ring(cx, cy, z0, radius, lw, h, n=10):
    parts = []
    chord = 2 * radius * math.sin(math.pi / n)
    for i in range(n):
        a = math.tau * i / n
        x = cx + radius * math.cos(a)
        y = cy + radius * math.sin(a)
        parts.append(transform(box((lw, chord, h)), rot_z=a, move=(x, y, z0 + h / 2)))
    return merge(*parts)


def _patio_swing_parts(x_s, phase):
    bar_y, bar_z = -0.055, GROUND + 0.045
    seat_z0 = GROUND + 0.010
    seat_top = seat_z0 + 0.003
    chain_h = bar_z - seat_top
    chains = merge(
        box_on((0.0012, 0.0012, chain_h), x_s - 0.008, bar_y, seat_top),
        box_on((0.0012, 0.0012, chain_h), x_s + 0.008, bar_y, seat_top),
    )
    seat = box_on((0.022, 0.010, 0.003), x_s, bar_y, seat_z0)
    anim = {'kind': 'swing', 'axis': 'X', 'pivot': [x_s, bar_y, bar_z],
            'params': {'amplitude_deg': 25, 'period': 2.2, 'phase': phase}}
    return chains, seat, anim


def module_patio():
    # ---------- asta_bandera ----------
    pole_x, pole_y = -0.068, -0.050
    pole_top = GROUND + 0.100
    flag_top = pole_top - 0.002
    flag_h = 0.022
    flag_zc = flag_top - flag_h / 2
    flag_w = 0.034
    stripe_w = flag_w / 3
    flag_t = 0.0008
    flag_yaw = math.radians(37)  # extiende hacia (cos37, sin37): +X y +Y, de cara a la cámara
    flag_anim = {'clip': 'bandera', 'kind': 'sway', 'pivot': [pole_x, pole_y, flag_zc],
                 'axis': 'Z', 'params': {'amplitude_deg': 18, 'period': 2.4, 'phase': 0.0}}

    def stripe(i):
        local_cx = stripe_w * (i + 0.5)
        m = box((stripe_w, flag_t, flag_h), (local_cx, 0.0, flag_zc))
        return transform(m, rot_z=flag_yaw, move=(pole_x, pole_y, 0.0))

    obj('Base asta', 'asta_bandera', box_on((0.012, 0.012, 0.006), pole_x, pole_y, GROUND), 'banqueta')
    obj('Asta', 'asta_bandera', cylinder(0.0012, pole_top - (GROUND + 0.001), base=(pole_x, pole_y, GROUND + 0.001),
                                         segments=6), 'blanco')
    obj('Remate asta', 'asta_bandera', blob((0.0030, 0.0030, 0.0030), (pole_x, pole_y, pole_top + 0.002),
                                            segments=6, rings=4), 'amarillo')
    obj('Bandera celeste', 'asta_bandera', merge(stripe(0), stripe(2)), 'celeste', anim=dict(flag_anim))
    obj('Bandera blanca', 'asta_bandera', stripe(1), 'blanco', anim=dict(flag_anim))

    # ---------- juegos (columpios) ----------
    bar_y, bar_z = -0.055, GROUND + 0.045
    bar_x0, bar_len = -0.170, 0.070
    leg_len = math.hypot(0.020, 0.045)
    leg_theta = math.atan2(0.020, 0.045)
    legs, feet = [], []
    for ax in (-0.170, -0.100):
        for side in (-1, 1):
            # Pata desde el vértice superior hasta el pie en y = bar_y +/- 0.020.
            rot = -leg_theta if side < 0 else leg_theta
            zmid = GROUND + 0.0225
            ymid = bar_y + side * 0.010
            legs.append(transform(box((0.003, 0.003, leg_len)), rot_x=rot, move=(ax, ymid, zmid)))
            feet.append(box_on((0.005, 0.005, 0.002), ax, bar_y + side * 0.020, GROUND))
    bar = cylinder(0.0015, bar_len, base=(bar_x0, bar_y, bar_z), segments=6, axis='X')
    obj('Estructura A', 'juegos', merge(*legs, bar), 'amarillo')
    obj('Tacos base', 'juegos', merge(*feet), 'oscuro')

    swing_xs = (-0.150, -0.120)
    for i, (x_s, phase) in enumerate(zip(swing_xs, (0.0, 0.5)), start=1):
        chains, seat, anim = _patio_swing_parts(x_s, phase)
        obj(f'Cadenas columpio {i}', 'juegos', chains, 'oscuro', anim=dict(anim, clip='columpios'))
        obj(f'Asiento columpio {i}', 'juegos', seat, 'acento', anim=dict(anim, clip='columpios'))

    # ---------- cancha (region X[0.055,0.190], Y[-0.088,-0.012]) ----------
    xa, xb, yb, yt = 0.055, 0.190, -0.088, -0.012
    cx, cy = (xa + xb) / 2, (yb + yt) / 2
    outer_w, outer_d = xb - xa, yt - yb
    bw = _patio_border_w
    bh = 0.0035
    bz0 = GROUND - 0.0005
    surf_w, surf_d = outer_w - 2 * bw, outer_d - 2 * bw
    surface = box_on((surf_w, surf_d, 0.002), cx, cy, bz0)
    obj('Superficie cancha', 'cancha', surface, 'uniforme')
    border = merge(
        box_on((bw, outer_d, bh), xa + bw / 2, cy, bz0),
        box_on((bw, outer_d, bh), xb - bw / 2, cy, bz0),
        box_on((outer_w - 2 * bw, bw, bh), cx, yb + bw / 2, bz0),
        box_on((outer_w - 2 * bw, bw, bh), cx, yt - bw / 2, bz0),
    )
    obj('Borde cancha', 'cancha', border, 'banqueta')

    lz = _patio_surf_top + 0.0006
    xl, xr, lyb, lyt = xa + 0.004, xb - 0.004, -0.084, -0.016
    lw = _patio_line_w
    lh = _patio_line_h
    white = [
        box_on((lw, lyt - lyb + lw, lh), xl, (lyt + lyb) / 2, lz),
        box_on((lw, lyt - lyb + lw, lh), xr, (lyt + lyb) / 2, lz),
        box_on((xr - xl + lw, lw, lh), (xl + xr) / 2, lyb, lz),
        box_on((xr - xl + lw, lw, lh), (xl + xr) / 2, lyt, lz),
        box_on((lw, lyt - lyb, lh), cx, (lyt + lyb) / 2, lz),
        _patio_ring(cx, cy, lz, 0.012, lw, lh),
    ]
    # Canastas en ambos extremos, espejo respecto al centro cx (lado izquierdo calculado desde xa).
    boards, poles, hoops, paints, nets = [], [], [], [], []
    for mirror in (False, True):
        def mx(x):
            return 2 * cx - x if mirror else x
        pole_xx = mx(xa + 0.004)
        board_xx = mx(xa + 0.0054)
        hoop_xx = mx(xa + 0.0086)
        paint_xx = mx(xa + 0.0057 + 0.0004 + 0.0004)  # cara delantera del tablero + grosor 0.0008
        poles.append(cylinder(0.0012, 0.034, base=(pole_xx, cy, GROUND), segments=6))
        boards.append(box((0.0008, 0.014, 0.012), (board_xx, cy, GROUND + 0.034)))
        hoops.append(cylinder(0.0032, 0.0010, base=(hoop_xx, cy, GROUND + 0.030), segments=8))
        paints.append(box((0.0008, 0.010, 0.006), (paint_xx, cy, GROUND + 0.035)))
        nets.append(frustum(0.0012, 0.0032, 0.006, base=(hoop_xx, cy, GROUND + 0.024), segments=6))
    obj('Lineas y redes cancha', 'cancha', merge(*white, *boards, *nets), 'blanco')
    obj('Postes canasta', 'cancha', merge(*poles), 'oscuro')
    obj('Aros y cuadros canasta', 'cancha', merge(*hoops, *paints), 'acento')

    ball_x, ball_y, ball_r = cx - 0.012, -0.046, 0.004
    ball_z = _patio_surf_top + ball_r
    obj('Balon', 'cancha', blob((ball_r, ball_r, ball_r), (ball_x, ball_y, ball_z), segments=7, rings=5),
        'balon', anim={'clip': 'balon', 'kind': 'bounce', 'pivot': [ball_x, ball_y, ball_z],
                       'axis': 'Z', 'params': {'height': 0.025, 'period': 0.8, 'phase': 0.0}})

    return {
        'asta_bandera': {'label_position': [pole_x, pole_y, round(pole_top + 0.005, 4)]},
        'juegos': {'label_position': [-0.135, bar_y, round(bar_z + 0.003, 4)]},
        'cancha': {'label_position': [round(cx, 4), round(cy, 4), round(_patio_surf_top + 0.002, 4)]},
    }


# ==== MÓDULO vida · module_vida.py · sha256 0f0e3d72496cc1be3bec96c898c4b1a00aff395e856c8e027f53d0e1c588493b ====
# Módulo "vida" detalle: árboles, nubes y estudiantes. Usa solo primitivas del kit.
# Todas las coordenadas son de mundo (metros); pies y pivotes en GROUND.


def _vida_tree(i, x, y, style, color):
    """Árbol de dos objetos (tronco y copa) con el mismo anim sway."""
    phase = round(i / 8.0, 3)
    amplitude = (3, 4, 5)[i % 3]
    period = round(3.0 + 0.12 * i, 2)
    anim = {'clip': 'arboles', 'kind': 'sway', 'pivot': [x, y, GROUND], 'axis': 'X',
            'params': {'amplitude_deg': amplitude, 'period': period, 'phase': phase}}
    if style == 'round':
        trunk = cylinder(0.0030, 0.016, base=(x, y, GROUND), segments=6)
        crown = merge(
            blob((0.012, 0.012, 0.013), center=(x, y, GROUND + 0.027), segments=7, rings=5),
            blob((0.0075, 0.0075, 0.0075), center=(x + 0.006, y - 0.004, GROUND + 0.033),
                 segments=6, rings=4),
        )
    else:
        trunk = cylinder(0.0030, 0.012, base=(x, y, GROUND), segments=6)
        crown = merge(
            cone(0.011, 0.015, base=(x, y, GROUND + 0.010), segments=7),
            cone(0.0085, 0.013, base=(x, y, GROUND + 0.018), segments=7),
            cone(0.006, 0.014, base=(x, y, GROUND + 0.026), segments=7),
        )
    obj(f'arbol_{i}_tronco', 'arboles', trunk, 'tronco', anim)
    obj(f'arbol_{i}_copa', 'arboles', crown, color, anim)


def _vida_trees():
    spots = [
        (-0.175, 0.120, 'round', 'follaje'),
        (-0.120, 0.125, 'pine', 'follaje'),
        (0.120, 0.125, 'round', 'follaje_claro'),
        (0.175, 0.115, 'pine', 'follaje'),
        (-0.170, 0.040, 'round', 'follaje'),
        (0.170, 0.040, 'pine', 'follaje'),
        (-0.060, 0.125, 'round', 'follaje_claro'),
        (0.060, 0.125, 'pine', 'follaje'),
    ]
    for i, (x, y, style, color) in enumerate(spots):
        _vida_tree(i, x, y, style, color)


def _vida_cloud(i, cx, cy, cz, distance, period, phase):
    """Nube de cuatro blobs aplanados fusionados en un objeto 'blanco' con drift en X."""
    anim = {'clip': 'nubes', 'kind': 'drift', 'pivot': [cx, cy, cz], 'axis': 'X',
            'params': {'distance': distance, 'period': period, 'phase': phase}}
    mesh = merge(
        blob((0.014, 0.011, 0.009), center=(cx - 0.016, cy, cz), segments=6, rings=4),
        blob((0.019, 0.013, 0.011), center=(cx, cy + 0.003, cz + 0.003), segments=6, rings=4),
        blob((0.014, 0.011, 0.009), center=(cx + 0.016, cy, cz), segments=6, rings=4),
        blob((0.011, 0.008, 0.007), center=(cx + 0.004, cy - 0.006, cz - 0.002), segments=6, rings=4),
    )
    obj(f'nube_{i}', 'nubes', mesh, 'blanco', anim)


def _vida_clouds():
    # Z[0.141,0.164]; izquierda X[-0.17,-0.06], derecha X[0.06,0.17] con drift incluido.
    _vida_cloud(0, -0.115, -0.030, 0.150, 0.025, 9.0, 0.0)   # izquierda, adelantada
    _vida_cloud(1, -0.115, 0.080, 0.148, 0.025, 11.0, 0.37)  # izquierda, atrás
    _vida_cloud(2, 0.115, 0.020, 0.152, 0.020, 10.0, 0.71)   # derecha, media profundidad


def _vida_student(i, x, y, shirt, pants, backpack, kind, params):
    """Figura de ~0.0206 m. Pies en (x, y, GROUND); el pivote de todas las piezas es ese punto.
    Piezas: pantalón/piernas (color pants), torso (shirt), cabeza 'piel', casquete de cabello
    'oscuro' en la parte alta y trasera de la cabeza, y mochila opcional en la espalda (+Y)."""
    z = GROUND
    legs = merge(
        box((0.0016, 0.0024, 0.0080), center=(x - 0.0011, y, z + 0.0040)),
        box((0.0016, 0.0024, 0.0080), center=(x + 0.0011, y, z + 0.0040)),
    )
    torso = frustum(0.0048, 0.0040, 0.0062, base=(x, y, z + 0.0080), segments=6)
    head = blob((0.0032, 0.0031, 0.0032), center=(x, y, z + 0.0174), segments=6, rings=4)
    cap = blob((0.0034, 0.0031, 0.0015), center=(x, y + 0.0010, z + 0.0190), segments=6, rings=4)
    anim = {'clip': 'estudiantes', 'kind': kind, 'pivot': [x, y, z], 'params': params}
    if pants == 'oscuro':
        obj(f'estudiante_{i}_piernas_cabello', 'estudiantes', merge(legs, cap), 'oscuro', anim)
    else:
        obj(f'estudiante_{i}_piernas', 'estudiantes', legs, pants, anim)
        obj(f'estudiante_{i}_cabello', 'estudiantes', cap, 'oscuro', anim)
    obj(f'estudiante_{i}_torso', 'estudiantes', torso, shirt, anim)
    obj(f'estudiante_{i}_cabeza', 'estudiantes', head, 'piel', anim)
    if backpack is not None:
        bag = box((0.0042, 0.0018, 0.0055), center=(x, y + 0.0049, z + 0.0118))
        obj(f'estudiante_{i}_mochila', 'estudiantes', bag, backpack, anim)


def _vida_students():
    z = GROUND
    # Tres caminantes con recorrido en bucle cerrado (último punto = primero).
    _vida_student(0, 0.006, -0.090, 'blanco', 'uniforme', 'acento', 'walk', {
        'points': [0.006, -0.090, z, 0.006, -0.020, z, 0.006, -0.090, z],
        'period': 10.0, 'bob': 0.0015, 'forward': '-Y'})
    _vida_student(1, -0.160, -0.099, 'uniforme', 'oscuro', None, 'walk', {
        'points': [-0.160, -0.099, z, 0.160, -0.099, z, -0.160, -0.099, z],
        'period': 12.0, 'bob': 0.0015, 'forward': '-Y'})
    _vida_student(2, -0.070, -0.084, 'blanco', 'uniforme', 'amarillo', 'walk', {
        'points': [-0.070, -0.084, z, -0.030, -0.084, z, -0.030, -0.072, z,
                   -0.070, -0.072, z, -0.070, -0.084, z],
        'period': 8.0, 'bob': 0.0015, 'forward': '-Y'})
    # Dos quietos con un leve rebote: uno en el patio izquierdo, otro junto a la banqueta.
    _vida_student(3, -0.035, -0.030, 'blanco', 'uniforme', None, 'bounce',
                  {'height': 0.002, 'period': 0.9, 'phase': 0.0})
    _vida_student(4, 0.030, -0.080, 'uniforme', 'oscuro', None, 'bounce',
                  {'height': 0.002, 'period': 0.9, 'phase': 0.5})


def module_vida():
    _vida_trees()
    _vida_clouds()
    _vida_students()
    return {
        'arboles': {'label_position': [0.170, 0.040, GROUND + 0.042]},
        'nubes': {'label_position': [-0.115, -0.030, 0.166]},
        'estudiantes': {'label_position': [-0.035, -0.030, GROUND + 0.0215]},
    }


# ==== COMPOSITOR (coordinador) ====
def build():
    parts = {}
    for fn in (module_entorno, module_edificio, module_patio, module_vida):
        got = fn()
        overlap = set(parts) & set(got)
        if overlap:
            raise ValueError('Partes duplicadas entre módulos: ' + str(sorted(overlap)))
        parts.update(got)
    return {
        'title': 'Escuela · diorama Flat Minimal',
        'design_notes': [
            'Estilo Flat Shaded / Minimalist: caras planas, paleta limitada, sin texturas.',
            'Módulos por modelo: entorno, patio y vida (Haiku); edificio (Sonnet); kit y composición (Opus).',
            'Los objetos animados llevan anim_* para el paso de animación; esta escena es estática.',
        ],
        'parts': parts,
    }
