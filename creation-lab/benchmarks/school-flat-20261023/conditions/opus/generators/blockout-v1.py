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
    'pasto': '9CCB6B', 'tierra': 'C9A27A', 'asfalto': '6E7681', 'banqueta': 'E6E1D6',
    'muro': 'F4E3C1', 'acento': 'E07A5F', 'teja': 'C8553D', 'vidrio': '8EC5E8',
    'blanco': 'F7F7F2', 'madera': '8B5E3C', 'oscuro': '2F3A45', 'celeste': '4997D0',
    'arcilla': 'E9A15B', 'balon': 'F08A24', 'follaje': '4E9F5D', 'follaje_claro': '7CC46F',
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


# ==== MÓDULO entorno · module_entorno.py · sha256 fb2fd95af1bfe1b6bbd4791f1c7239f18e4bb790d9e5b51db30242b302a9acee ====
# Módulo entorno: terreno, camino (calle, banqueta, camino a la puerta) y autobús.
# Estilo Flat/Minimal: pocas caras, piezas unidas por color.

_entorno_STREET_TOP = -0.0385
_entorno_BUS_CENTER = (-0.08, -0.133)


def _entorno_terreno():
    tierra = box((0.40, 0.30, 0.012), (0.0, 0.0, -0.050))
    pasto = box((0.40, 0.30, 0.004), (0.0, 0.0, -0.042))
    obj('terreno_tierra', 'terreno', tierra, 'tierra')
    obj('terreno_pasto', 'terreno', pasto, 'pasto')
    # Matas bajas en el borde trasero y laterales, lejos de árboles, columpios y cancha.
    spots = [(0.0, 0.142), (-0.090, 0.142), (0.090, 0.142),
             (-0.191, 0.000), (0.191, 0.000), (-0.191, 0.085), (0.191, 0.085)]
    matas = [blob((0.0045, 0.0045, 0.0032), (x, y, GROUND + 0.0018), segments=6, rings=4)
             for x, y in spots]
    obj('terreno_matas', 'terreno', merge(*matas), 'follaje_claro')


def _entorno_camino():
    asfalto = box((0.40, 0.042, 0.0015), (0.0, -0.126, -0.03925))
    obj('camino_calle', 'camino', asfalto, 'asfalto')
    dashes = [box((0.012, 0.0016, 0.0012), (-0.187 + i * 0.022, -0.126, -0.0384))
              for i in range(18)]
    obj('camino_linea', 'camino', merge(*dashes), 'blanco')
    banqueta = box((0.40, 0.012, 0.0025), (0.0, -0.099, -0.03875))
    sendero = box((0.028, 0.083, 0.0015), (0.0, -0.0515, -0.03925))
    obj('camino_banqueta', 'camino', merge(banqueta, sendero), 'banqueta')


def _entorno_autobus():
    cx, cy = _entorno_BUS_CENTER
    z0 = _entorno_STREET_TOP
    r = 0.0045
    body_bottom = z0 + 0.0025
    top = z0 + 0.028
    x_back, x_front = cx - 0.035, cx + 0.035
    x_cab = x_front - 0.012          # frente de la caja principal
    width = 0.024
    # Carrocería: caja principal + cofre delantero más bajo.
    main = box((x_cab - x_back, width, top - body_bottom),
               ((x_back + x_cab) / 2, cy, (body_bottom + top) / 2))
    hood_top = body_bottom + 0.012
    hood = box((x_front - x_cab + 0.001, width - 0.0016, hood_top - body_bottom),
               ((x_cab - 0.001 + x_front) / 2, cy, (body_bottom + hood_top) / 2))
    # Franja oscura a lo largo (sobresale 0.0006 por lado) y 4 ruedas.
    stripe = box((x_cab - x_back + 0.0012, width + 0.0012, 0.0012),
                 ((x_back + x_cab) / 2, cy, body_bottom + 0.009))
    wheels = []
    for wx in (x_back + 0.011, x_front - 0.010):
        for wy in (cy - width / 2 - 0.0005, cy + width / 2 - 0.0035):
            wheels.append(cylinder(r, 0.004, (wx, wy, z0 + r), segments=8, axis='Y',
                                   phase=math.pi / 8))
    # Ventanas laterales (atraviesan la caja y sobresalen 0.0006 por lado) y parabrisas.
    win_lo, win_hi = body_bottom + 0.0135, top - 0.0035
    windows = [box((0.006, width + 0.0012, win_hi - win_lo),
                   (x_back + 0.0065 + i * 0.0075, cy, (win_lo + win_hi) / 2))
               for i in range(7)]
    windshield = box((0.0012, width - 0.006, win_hi - win_lo + 0.001),
                     (x_cab, cy, (win_lo + win_hi) / 2))
    anim = {'clip': 'autobus', 'kind': 'path', 'axis': 'Z',
            'pivot': [cx, cy, z0],
            'params': {'forward': '+X', 'period': 14,
                       'points': [-0.08, -0.133, -0.0385, 0.15, -0.133, -0.0385,
                                  0.165, -0.126, -0.0385, 0.15, -0.117, -0.0385,
                                  -0.15, -0.117, -0.0385, -0.165, -0.126, -0.0385,
                                  -0.15, -0.133, -0.0385, -0.08, -0.133, -0.0385]}}
    obj('autobus_carroceria', 'autobus', merge(main, hood), 'amarillo', dict(anim))
    obj('autobus_oscuro', 'autobus', merge(stripe, *wheels), 'oscuro', dict(anim))
    obj('autobus_vidrios', 'autobus', merge(windshield, *windows), 'vidrio', dict(anim))
    return top


def module_entorno():
    _entorno_terreno()
    _entorno_camino()
    top = _entorno_autobus()
    return {
        'terreno': {'label_position': [0.025, -0.050, -0.039]},
        'camino': {'label_position': [0.100, -0.099, -0.0365]},
        'autobus': {'label_position': [_entorno_BUS_CENTER[0], _entorno_BUS_CENTER[1], top + 0.004]},
    }


# ==== MÓDULO edificio · module_edificio.py · sha256 451cf054ce1ac0403f3b97fa3d65040373c35cabbd8278ab6f876983867f03b2 ====
# ==== MÓDULO edificio · edificio, techo, ventanas, puerta, torre_reloj ====
# Autor: módulo principal de geometría (estilo Flat Shaded / Minimalist 3D).
# Plano: huella X[-0.10,0.10] Y[0.00,0.075]; dos pisos GROUND->0.030; frente -Y.
# Pisos: planta baja GROUND..-0.005, planta alta -0.005..0.030 (banda en -0.005).

_edificio_X0, _edificio_X1 = -0.100, 0.100
_edificio_Y0, _edificio_Y1 = 0.000, 0.075
_edificio_TOP = 0.030
_edificio_TOWER_Y0 = -0.010          # cara frontal de la torre
_edificio_CLOCK_Z = 0.065
_edificio_DOOR_TOP = GROUND + 0.030  # -0.010
_edificio_STEP_TOP = GROUND + 0.0036  # peldaño superior
_edificio_DOOR_BOTTOM = GROUND + 0.004  # holgura sobre el peldaño para que la hoja gire libre


def _edificio_span(lo, hi, z0, z1, x0, x1):
    """Caja por extremos: Y[lo,hi], Z[z0,z1], X[x0,x1]."""
    return box((x1 - x0, hi - lo, z1 - z0), ((x0 + x1) / 2, (lo + hi) / 2, (z0 + z1) / 2))


def _edificio_bb(x0, x1, y0, y1, z0, z1):
    return box((x1 - x0, y1 - y0, z1 - z0), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def _edificio_fbox(face, u0, u1, z0, z1, d0, d1):
    """Caja sobre una fachada. u = coordenada en el plano (X en frente/trasera,
    Y en laterales); d = distancia hacia fuera de la pared (d0<0 = empotrado)."""
    if face == 'front':
        return _edificio_bb(u0, u1, _edificio_Y0 - d1, _edificio_Y0 - d0, z0, z1)
    if face == 'tower':
        return _edificio_bb(u0, u1, _edificio_TOWER_Y0 - d1, _edificio_TOWER_Y0 - d0, z0, z1)
    if face == 'back':
        return _edificio_bb(u0, u1, _edificio_Y1 + d0, _edificio_Y1 + d1, z0, z1)
    if face == 'left':
        return _edificio_bb(_edificio_X0 - d1, _edificio_X0 - d0, u0, u1, z0, z1)
    return _edificio_bb(_edificio_X1 + d0, _edificio_X1 + d1, u0, u1, z0, z1)  # right


def _edificio_window(face, u, zc, w, h, frames, glasses):
    """Marco blanco (anillo + cruz) que sobresale 0.0012 y vidrio que sobresale 0.0006."""
    f = 0.0012
    e = -0.0005
    hu, hz = w / 2, h / 2
    frames += [
        _edificio_fbox(face, u - hu - f, u + hu + f, zc + hz, zc + hz + f, e, 0.0012),          # dintel
        _edificio_fbox(face, u - hu - f - 0.0006, u + hu + f + 0.0006,
                       zc - hz - f * 1.2, zc - hz, e, 0.0018),                                   # alféizar
        _edificio_fbox(face, u - hu - f, u - hu, zc - hz, zc + hz, e, 0.0012),                  # jamba izq.
        _edificio_fbox(face, u + hu, u + hu + f, zc - hz, zc + hz, e, 0.0012),                  # jamba der.
        _edificio_fbox(face, u - 0.00045, u + 0.00045, zc - hz, zc + hz, e, 0.0012),            # parteluz
        _edificio_fbox(face, u - hu, u + hu, zc + h * 0.18 - 0.00045, zc + h * 0.18 + 0.00045,
                       e, 0.0012),                                                               # travesaño
    ]
    # El vidrio entra f/2 bajo el marco: sin caras coplanares con las jambas.
    glasses.append(_edificio_fbox(face, u - hu - f / 2, u + hu + f / 2,
                                  zc - hz - f / 2, zc + hz + f / 2, e, 0.0006))


def _edificio_roof_slab(sign, half_depth, z_ridge, tan_a, thick, overhang, length_x):
    """Faldón del techo apoyado sobre el plano del hastial. sign=-1 frente, +1 trasera."""
    a = math.atan(tan_a)
    ca, sa = math.cos(a), math.sin(a)
    y_r = (_edificio_Y0 + _edificio_Y1) / 2
    run = half_depth + overhang
    s0 = -run / ca                 # alero (sobre el plano inferior)
    s1 = thick * tan_a             # cierre en la cumbrera
    length = s1 - s0
    sm = (s0 + s1) / 2
    # Punto medio en el plano inferior y desplazamiento normal t/2 (vista de frente: sign=-1).
    ym = y_r + sm * ca * (-sign)
    zm = z_ridge + sm * sa
    ny, nz = sign * sa, ca
    cy, cz = ym + ny * thick / 2, zm + nz * thick / 2
    slab = box((length_x, length, thick))
    # Frente: sube hacia +Y => rot_x = +a. Trasera: sube hacia -Y => rot_x = -a.
    return transform(slab, rot_x=-sign * a, move=(0.0, cy, cz))


def module_edificio():
    frames, glasses = [], []

    # ------------------------------------------------------------ edificio
    gable_base, gable_h = 0.0305, 0.0255
    half_d = (_edificio_Y1 - _edificio_Y0) / 2
    yc = (_edificio_Y0 + _edificio_Y1) / 2
    muro = merge(
        _edificio_bb(_edificio_X0, _edificio_X1, _edificio_Y0, _edificio_Y1, GROUND - 0.0005, _edificio_TOP),
        gable(_edificio_X1 - _edificio_X0, _edificio_Y1 - _edificio_Y0, gable_h, base=(0.0, yc, gable_base)),
        _edificio_bb(_edificio_X0, _edificio_X1, _edificio_Y0, _edificio_Y1, _edificio_TOP - 0.001, gable_base + 0.0002),
    )
    obj('edificio_muros', 'edificio', muro, 'muro')

    acento = merge(
        _edificio_bb(-0.101, 0.101, -0.001, 0.076, GROUND - 0.0005, GROUND + 0.005),   # zócalo
        _edificio_bb(-0.101, 0.101, -0.001, 0.076, -0.0065, -0.0035),                  # banda entre pisos
    )
    obj('edificio_zocalo_banda', 'edificio', acento, 'acento')

    blancos = [_edificio_bb(-0.1025, 0.1025, -0.0025, 0.0775, 0.027, 0.031)]          # cornisa
    pz0, pz1 = GROUND + 0.0045, 0.0275
    for sx in (-1, 1):
        # pilastras de ritmo entre ventanas del frente
        for px in (0.0295, 0.0505, 0.0715):
            x = sx * px
            blancos.append(_edificio_fbox('front', x - 0.0015, x + 0.0015, pz0, pz1, -0.0005, 0.0018))
        # columnas de esquina (envuelven la arista)
        x0, x1 = (0.0970, 0.1018) if sx > 0 else (-0.1018, -0.0970)
        blancos.append(_edificio_bb(x0, x1, -0.0018, 0.0030, pz0, pz1))
        blancos.append(_edificio_bb(x0, x1, 0.0720, 0.0768, pz0, pz1))
    obj('edificio_cornisa_pilastras', 'edificio', merge(*blancos), 'blanco')

    # Escalones frente a la puerta: dos peldaños en Y[-0.020,-0.010]; el superior
    # entra al vano como umbral hasta el fondo oscuro.
    steps = merge(
        _edificio_bb(-0.014, 0.014, -0.020, -0.0095, GROUND - 0.0005, GROUND + 0.0018),
        _edificio_bb(-0.012, 0.012, -0.015, -0.0058, GROUND - 0.0005, _edificio_STEP_TOP),
    )
    obj('edificio_escalones', 'edificio', steps, 'banqueta')

    # Rótulo liso sobre la puerta (encima de la banda de la torre), sin texto.
    obj('edificio_rotulo', 'edificio',
        _edificio_bb(-0.013, 0.013, -0.0115, -0.0095, -0.002, 0.006), 'celeste')

    # Rebaje oscuro: fondo del vano de la puerta; su cara frontal queda 4 mm detrás
    # de la fachada de la torre y se ve al abrir la hoja.
    obj('edificio_interior_oscuro', 'edificio',
        _edificio_bb(-0.0105, 0.0105, -0.0060, -0.0035, GROUND - 0.0005, _edificio_DOOR_TOP + 0.0005), 'oscuro')

    # ------------------------------------------------------------ techo
    tan_a = gable_h / half_d
    z_ridge = gable_base + gable_h
    thick, over = 0.0025, 0.006
    lx = (_edificio_X1 - _edificio_X0) + 2 * over
    techo = merge(_edificio_roof_slab(-1, half_d, z_ridge, tan_a, thick, over, lx),
                  _edificio_roof_slab(1, half_d, z_ridge, tan_a, thick, over, lx))
    obj('techo_dos_aguas', 'techo', techo, 'teja')

    # ------------------------------------------------------------ ventanas
    w, h = 0.012, 0.015
    z_floors = (-0.021, 0.012)
    for zc in z_floors:
        for sx in (-1, 1):
            for px in (0.040, 0.061, 0.082):
                _edificio_window('front', sx * px, zc, w, h, frames, glasses)
        for face in ('left', 'right'):
            for py in (0.025, 0.051):
                _edificio_window(face, py, zc, w, h, frames, glasses)
        for px in (-0.068, -0.027, 0.027, 0.068):
            _edificio_window('back', px, zc, w, h, frames, glasses)
    _edificio_window('tower', 0.0, 0.016, 0.010, 0.012, frames, glasses)   # ventana alta de la torre
    obj('ventanas_marcos', 'ventanas', merge(*frames), 'blanco')
    obj('ventanas_vidrios', 'ventanas', merge(*glasses), 'vidrio')

    # ------------------------------------------------------------ torre_reloj
    tx0, tx1, ty0, ty1, tz1 = -0.022, 0.022, _edificio_TOWER_Y0, 0.030, 0.085
    dz = _edificio_DOOR_TOP
    torre = merge(
        _edificio_bb(tx0, tx1, -0.0040, ty1, GROUND - 0.0005, tz1),        # cuerpo trasero
        _edificio_bb(tx0, tx1, ty0, -0.0039, dz, tz1),                     # frente sobre el vano
        _edificio_bb(tx0, -0.010, ty0, -0.0039, GROUND - 0.0005, dz + 0.0005),   # jamba izq. del vano
        _edificio_bb(0.010, tx1, ty0, -0.0039, GROUND - 0.0005, dz + 0.0005),    # jamba der. del vano
    )
    obj('torre_cuerpo', 'torre_reloj', torre, 'muro')
    bandas = merge(
        _edificio_bb(tx0 - 0.001, tx1 + 0.001, ty0 - 0.001, ty1 + 0.001, -0.0065, -0.0035),
        _edificio_bb(tx0 - 0.001, tx1 + 0.001, ty0 - 0.001, ty1 + 0.001, 0.044, 0.047),
    )
    obj('torre_bandas', 'torre_reloj', bandas, 'acento')

    cy = _edificio_TOWER_Y0 - 0.0005   # -0.0105: centro de la esfera
    cz = _edificio_CLOCK_Z
    blanco_torre = merge(
        _edificio_bb(tx0 - 0.0015, tx1 + 0.0015, ty0 - 0.0015, ty1 + 0.0015, 0.0825, 0.0865),  # cornisa
        cylinder(0.012, 0.0015, base=(0.0, cy - 0.00075, cz), segments=12, axis='Y'),       # esfera
    )
    obj('torre_cornisa_esfera', 'torre_reloj', blanco_torre, 'blanco')

    face_front = cy - 0.00075          # -0.01125
    aro = [cylinder(0.0135, 0.0011, base=(0.0, -0.0106, cz), segments=12, axis='Y')]
    for k in range(4):                 # marcas de 12, 3, 6 y 9
        ang = k * math.pi / 2
        mx, mz = 0.0098 * math.sin(ang), 0.0098 * math.cos(ang)
        sx, sz = (0.0010, 0.0022) if k % 2 == 0 else (0.0022, 0.0010)
        aro.append(_edificio_bb(mx - sx / 2, mx + sx / 2, face_front - 0.00065, face_front + 0.0002,
                                mz - sz / 2, mz + sz / 2))
    obj('torre_aro_reloj', 'torre_reloj', merge(*aro), 'oscuro')

    techo_torre = pyramid((tx1 - tx0) + 0.008, (ty1 - ty0) + 0.008, 0.115 - 0.086,
                          base=(0.0, (ty0 + ty1) / 2, 0.086))
    obj('torre_techo', 'torre_reloj', techo_torre, 'teja')

    # Manecillas: spin alrededor de Y con pivote en el centro de la esfera.
    # Convención: rotación positiva (regla de la mano derecha) sobre +Y lleva +Z
    # (las 12) hacia +X (las 3); el espectador mira desde -Y, con +X a su derecha,
    # así que direction=+1 es sentido horario visto de frente.
    pivot = [0.0, cy, cz]
    minutero = merge(
        _edificio_bb(-0.00055, 0.00055, -0.0131, -0.0123, cz - 0.0015, cz + 0.0092),   # apunta a las 12
        cylinder(0.0014, 0.0010, base=(0.0, -0.0133, cz), segments=8, axis='Y'),       # eje central
    )
    obj('torre_minutero', 'torre_reloj', minutero, 'oscuro',
        anim={'clip': 'reloj', 'kind': 'spin', 'pivot': pivot, 'axis': 'Y',
              'params': {'period': 6, 'direction': 1}})
    horario = _edificio_bb(-0.0010, 0.0058, -0.0123, -0.0115, cz - 0.0008, cz + 0.0008)  # apunta a las 3
    obj('torre_horario', 'torre_reloj', horario, 'oscuro',
        anim={'clip': 'reloj', 'kind': 'spin', 'pivot': pivot, 'axis': 'Y',
              'params': {'period': 72, 'direction': 1}})

    # ------------------------------------------------------------ puerta
    # Bisagra en x=-0.010. Rotación positiva sobre +Z llevaría el borde libre (+X)
    # hacia +Y (dentro de la torre); por eso angle_deg = -100: abre hacia fuera (-Y).
    # La hoja empieza en GROUND+0.004 (no en GROUND) para librar el peldaño superior.
    door_anim = {'clip': 'puerta', 'kind': 'hinge', 'pivot': [-0.010, -0.0115, GROUND], 'axis': 'Z',
                 'params': {'angle_deg': -100, 'period': 3.0}}
    db, dt = _edificio_DOOR_BOTTOM, _edificio_DOOR_TOP
    hoja = merge(
        _edificio_bb(-0.010, 0.010, -0.0123, -0.0108, db, dt),
        _edificio_bb(-0.007, 0.007, -0.0128, -0.0121, db + 0.0030, db + 0.0110),   # panel inferior
        _edificio_bb(-0.007, 0.007, -0.0128, -0.0121, db + 0.0140, dt - 0.0030),   # panel superior
    )
    obj('puerta_hoja', 'puerta', hoja, 'madera', anim=door_anim)
    manija = _edificio_bb(0.0068, 0.0084, -0.0134, -0.0121, db + 0.0118, db + 0.0132)
    obj('puerta_manija', 'puerta', manija, 'amarillo', anim=dict(door_anim))

    return {
        'edificio': {'label_position': [-0.072, 0.0, 0.034]},
        'techo': {'label_position': [-0.060, 0.0375, 0.064]},
        'ventanas': {'label_position': [0.061, -0.004, 0.024]},
        'puerta': {'label_position': [0.0, -0.016, -0.006]},
        'torre_reloj': {'label_position': [0.0, 0.010, 0.122]},
    }


# ==== MÓDULO patio · module_patio.py · sha256 20063aeece61fa8f5fc2e54f194900fb7e9b284e2bbd1d683361b5867d681ed3 ====
# ==== MODULO patio · asta_bandera, juegos (columpios), cancha ====
# Autor: patio. Usa solo nombres del kit (sin imports).


def _patio_bar(p0, p1, thick):
    """Caja delgada entre dos puntos en un plano vertical YZ (rot_x)."""
    dy, dz = p1[1]-p0[1], p1[2]-p0[2]
    length = math.hypot(dy, dz)
    ang = -math.atan2(dy, dz)
    mid = ((p0[0]+p1[0])/2, (p0[1]+p1[1])/2, (p0[2]+p1[2])/2)
    return transform(box((thick, thick, length)), rot_x=ang, move=mid)


def _patio_ring(cx, cy, z, radius, n, width, height):
    """Anillo poligonal de n cajas (aro o círculo central)."""
    seg = 2*radius*math.sin(math.pi/n)+width
    parts = []
    for i in range(n):
        a = math.tau*(i+0.5)/n
        parts.append(box((seg, width, height),
                         (cx+radius*math.cos(a), cy+radius*math.sin(a), z), rot_z=a+math.pi/2))
    return merge(*parts)


def _patio_flag():
    px, py = -0.045, -0.060
    top = GROUND+0.11
    obj('asta_base', 'asta_bandera', box_on((0.010, 0.010, 0.003), px, py, GROUND-0.0005), 'banqueta')
    obj('asta_poste', 'asta_bandera', cylinder(0.0012, 0.11, (px, py, GROUND-0.0005), segments=6), 'blanco')
    obj('asta_remate', 'asta_bandera', blob((0.0024, 0.0024, 0.0024), (px, py, top+0.0012), 6, 4), 'amarillo')
    h, w_total, t = 0.022, 0.034, 0.0008
    z_top = top-0.004
    zc = z_top-h/2
    x0 = px+0.0008  # ligeramente dentro del asta para quedar unida
    w = w_total/3
    stripes = [box((w, t, h), (x0+w*(i+0.5), py, zc)) for i in range(3)]
    anim = {'clip': 'bandera', 'kind': 'sway', 'pivot': [px, py, zc], 'axis': 'Z',
            'params': {'amplitude_deg': 18, 'period': 2.4, 'phase': 0.0}}
    obj('bandera_celeste', 'asta_bandera', merge(stripes[0], stripes[2]), 'celeste', anim)
    obj('bandera_blanco', 'asta_bandera', stripes[1], 'blanco', dict(anim))
    return [px, py, top+0.012]


def _patio_swings():
    cy = -0.055
    bar_z = GROUND+0.045
    xl, xr = -0.175, -0.095
    spread = 0.018
    frame = [cylinder(0.0012, (xr-xl)+0.006, (xl-0.003, cy, bar_z), segments=6, axis='X')]
    for x in (xl, xr):
        for s in (-1, 1):
            foot = (x, cy+s*spread, GROUND-0.0006)
            frame.append(_patio_bar(foot, (x, cy, bar_z+0.0008), 0.0022))
    obj('columpios_estructura', 'juegos', merge(*frame), 'acento')
    seat_z0 = GROUND+0.010
    seat_h = 0.0015
    for i, (sx, phase) in enumerate(((-0.150, 0.0), (-0.120, 0.5))):
        anim = {'clip': 'columpios', 'kind': 'swing', 'pivot': [sx, cy, bar_z], 'axis': 'X',
                'params': {'amplitude_deg': 25, 'period': 2.2, 'phase': phase}}
        z_lo = seat_z0+seat_h-0.0003
        length = bar_z-z_lo
        chains = merge(*[box((0.0009, 0.0009, length), (sx+dx, cy, z_lo+length/2)) for dx in (-0.006, 0.006)])
        obj(f'columpio_{i+1}_cadenas', 'juegos', chains, 'oscuro', anim)
        obj(f'columpio_{i+1}_asiento', 'juegos', box_on((0.014, 0.008, seat_h), sx, cy, seat_z0),
            'uniforme', dict(anim))
    return [-0.135, cy, bar_z+0.012]


def _patio_court():
    cx, cy = 0.115, -0.050
    sx, sy = 0.146, 0.072
    surf_h = 0.002
    z0 = GROUND-0.0005
    s_top = z0+surf_h
    obj('cancha_superficie', 'cancha', box_on((sx, sy, surf_h), cx, cy, z0), 'arcilla')
    lw, lh = 0.0012, 0.0010
    lz = s_top+0.0006-lh/2  # tope de las líneas 0.0006 sobre la superficie
    x0, x1, y0, y1 = 0.048, 0.182, -0.081, -0.019
    white = [
        box((x1-x0+lw, lw, lh), (cx, y0, lz)),
        box((x1-x0+lw, lw, lh), (cx, y1, lz)),
        box((lw, y1-y0+lw, lh), (x0, cy, lz)),
        box((lw, y1-y0+lw, lh), (x1, cy, lz)),
        box((lw, y1-y0+lw, lh), (cx, cy, lz)),
        _patio_ring(cx, cy, lz, 0.010, 10, lw, lh),
    ]
    dark, rims = [], []
    hoop_z = GROUND+0.030
    for side, px in ((1, 0.044), (-1, 0.186)):
        dark.append(cylinder(0.0012, (GROUND+0.040)-(s_top-0.0005), (px, cy, s_top-0.0005), segments=6))
        bx = px+side*0.0016
        white.append(box((0.0010, 0.016, 0.011), (bx, cy, hoop_z+0.004)))
        r = 0.0030
        rims.append(_patio_ring(bx+side*(0.0005+r), cy, hoop_z, r, 6, 0.0008, 0.0008))
    obj('cancha_lineas_tableros', 'cancha', merge(*white), 'blanco')
    obj('cancha_postes', 'cancha', merge(*dark), 'oscuro')
    obj('cancha_aros', 'cancha', merge(*rims), 'acento')
    br = 0.004
    bpos = (cx+0.010, cy+0.006, s_top+br)
    obj('cancha_balon', 'cancha', blob((br, br, br), bpos, 7, 5), 'balon',
        {'clip': 'balon', 'kind': 'bounce', 'pivot': list(bpos), 'axis': 'Z',
         'params': {'height': 0.025, 'period': 0.8, 'phase': 0.0}})
    return [cx, cy, GROUND+0.050]


def module_patio():
    return {
        'asta_bandera': {'label_position': _patio_flag()},
        'juegos': {'label_position': _patio_swings()},
        'cancha': {'label_position': _patio_court()},
    }


# ==== MÓDULO vida · module_vida.py · sha256 15644fffeb973f003a882c0e9946c9e88c0ba959a304de24f54ebdc70f0567c6 ====
# ==== MÓDULO vida · árboles, nubes y estudiantes (Flat/Minimal) ====
# Sin imports: se concatena después de kit.py.

_vida_trees = [
    # (x, y, estilo, color copa, escala de altura)
    (-0.175, 0.120, 'pino', 'follaje', 1.00),
    (-0.120, 0.125, 'copa', 'follaje_claro', 1.00),
    (0.120, 0.125, 'pino', 'follaje', 0.95),
    (0.175, 0.115, 'copa', 'follaje', 1.05),
    (-0.170, 0.040, 'copa', 'follaje', 1.12),
    (0.170, 0.040, 'pino', 'follaje', 1.08),
    (-0.060, 0.125, 'copa', 'follaje_claro', 0.96),
    (0.060, 0.125, 'copa', 'follaje_claro', 1.00),
]

_vida_clouds = [
    # (cx, cy, cz, distance, period, phase)
    (-0.110, 0.060, 0.118, 0.025, 10.0, 0.00),
    (0.020, -0.010, 0.108, 0.020, 8.5, 0.37),
    (0.115, 0.075, 0.122, 0.030, 11.5, 0.71),
]


def _vida_tree(i, x, y, style, color, k):
    g = GROUND
    if style == 'copa':
        trunk_h = 0.016*k
        trunk = cylinder(0.0024, trunk_h + 0.003, base=(x, y, g - 0.001), segments=6)
        rz = 0.012*k
        canopy = merge(
            blob((0.0115, 0.011, rz), center=(x, y, g + trunk_h + rz*0.85), segments=7, rings=5),
            blob((0.0075, 0.0072, 0.0072*k), center=(x + 0.006, y - 0.003, g + trunk_h + 0.004),
                 segments=6, rings=4),
        )
    else:
        trunk_h = 0.008*k
        trunk = cylinder(0.0022, trunk_h + 0.002, base=(x, y, g - 0.001), segments=6)
        z0 = g + trunk_h
        canopy = merge(
            cone(0.0125, 0.016*k, base=(x, y, z0), segments=7),
            cone(0.0095, 0.014*k, base=(x, y, z0 + 0.009*k), segments=7, phase=0.22),
            cone(0.0065, 0.012*k, base=(x, y, z0 + 0.018*k), segments=7, phase=0.45),
        )
    anim = {'clip': 'arboles', 'kind': 'sway', 'pivot': [x, y, g], 'axis': 'X',
            'params': {'amplitude_deg': 3.0 + (i % 3)*0.8, 'period': 3.0 + (i % 4)*0.3,
                       'phase': round(i/8.0, 3)}}
    obj(f'vida_arbol_{i}_tronco', 'arboles', trunk, 'tronco', anim)
    obj(f'vida_arbol_{i}_copa', 'arboles', canopy, color, anim)
    return max(v[2] for v in canopy.vertices)


def _vida_cloud(i, cx, cy, cz, dist, period, phase):
    puffs = [
        ((0.020, 0.012, 0.0075), (cx, cy, cz)),
        ((0.013, 0.010, 0.0065), (cx - 0.018, cy + 0.002, cz - 0.002)),
        ((0.014, 0.010, 0.0070), (cx + 0.017, cy - 0.002, cz - 0.0015)),
    ]
    if i != 1:
        puffs.append(((0.010, 0.008, 0.0060), (cx + 0.004, cy + 0.004, cz + 0.005)))
    mesh = merge(*[blob(r, center=c, segments=7, rings=4) for r, c in puffs])
    anim = {'clip': 'nubes', 'kind': 'drift', 'pivot': [cx, cy, cz], 'axis': 'X',
            'params': {'distance': dist, 'period': period, 'phase': phase}}
    obj(f'vida_nube_{i}', 'nubes', mesh, 'blanco', anim)


def _vida_figure(i, x, y, torso_color, anim):
    g = GROUND
    legs = merge(
        box_on((0.0016, 0.0020, 0.0080), x - 0.0012, y, g - 0.0005),
        box_on((0.0016, 0.0020, 0.0080), x + 0.0012, y, g - 0.0005),
    )
    torso = frustum(0.0036, 0.0026, 0.0070, base=(x, y, g + 0.0072), segments=6, phase=math.pi/6)
    head = blob((0.0025, 0.0025, 0.0026), center=(x, y, g + 0.0168), segments=7, rings=5)
    hair = blob((0.0027, 0.0027, 0.0012), center=(x, y + 0.0003, g + 0.0186), segments=7, rings=4)
    obj(f'vida_estudiante_{i}_piernas', 'estudiantes', legs, 'oscuro', anim)
    obj(f'vida_estudiante_{i}_torso', 'estudiantes', torso, torso_color, anim)
    obj(f'vida_estudiante_{i}_cabeza', 'estudiantes', head, 'piel', anim)
    obj(f'vida_estudiante_{i}_cabello', 'estudiantes', hair, 'oscuro', anim)


def _vida_flat(points):
    out = []
    for x, y in points:
        out += [x, y, GROUND]
    return out


def _vida_students():
    walks = [
        ([(0.006, -0.090), (0.006, -0.020), (0.006, -0.090)], 9.0, 'uniforme'),
        ([(-0.160, -0.099), (0.160, -0.099), (-0.160, -0.099)], 12.0, 'blanco'),
        ([(-0.070, -0.085), (-0.030, -0.085), (-0.030, -0.070), (-0.070, -0.070), (-0.070, -0.085)],
         10.0, 'uniforme'),
    ]
    i = 0
    for pts, period, color in walks:
        x, y = pts[0]
        anim = {'clip': 'estudiantes', 'kind': 'walk', 'pivot': [x, y, GROUND], 'axis': 'Z',
                'params': {'points': _vida_flat(pts), 'period': period, 'bob': 0.0015,
                           'forward': '-Y'}}
        _vida_figure(i, x, y, color, anim)
        i += 1
    for (x, y), color, phase in (((-0.066, -0.040), 'blanco', 0.0), ((0.027, -0.058), 'uniforme', 0.45)):
        anim = {'clip': 'estudiantes', 'kind': 'bounce', 'pivot': [x, y, GROUND], 'axis': 'Z',
                'params': {'height': 0.002, 'period': 0.9, 'phase': phase}}
        _vida_figure(i, x, y, color, anim)
        i += 1


def module_vida():
    tops = [_vida_tree(i, *t) for i, t in enumerate(_vida_trees)]
    for i, c in enumerate(_vida_clouds):
        _vida_cloud(i, *c)
    _vida_students()
    return {
        'arboles': {'label_position': [-0.120, 0.125, round(tops[1] + 0.008, 4)]},
        'nubes': {'label_position': [0.020, -0.010, 0.124]},
        'estudiantes': {'label_position': [-0.066, -0.040, round(GROUND + 0.028, 4)]},
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
            'Condición solo-Opus: todos los módulos, animación y visor escritos por Opus 5.5; kit y composición (coordinador Opus).',
            'Los objetos animados llevan anim_* para el paso de animación; esta escena es estática.',
        ],
        'parts': parts,
    }
