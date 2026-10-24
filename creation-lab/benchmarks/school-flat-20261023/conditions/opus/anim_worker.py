"""Paso de animación del diorama escolar (Blender 5.2.3 LTS).

Convierte los metadatos anim_* de los objetos de source.blend en animaciones
glTF reales: una acción por objeto y clip, muestreada cada frame, metida en una
pista NLA con el nombre exacto del clip; el exportador glTF (modo NLA_TRACKS)
fusiona todas las pistas homónimas en una sola animación por clip.

Uso (rutas absolutas):
  blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
    --python anim_worker.py -- animate SOURCE.blend BRIEF.json OUTDIR
  blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
    --python anim_worker.py -- verify OUTDIR/animated.glb BRIEF.json OUTDIR

Las funciones de muestreo (sección PURA) no dependen de bpy y se pueden probar
con python3 normal: `import anim_worker` funciona sin Blender (bpy = None).
"""
import hashlib
import json
import math
import struct
import sys
import traceback
from pathlib import Path

try:
    import bpy
    from mathutils import Euler, Matrix, Vector
except ImportError:  # pruebas puras
    bpy = None

TAU = 2.0 * math.pi
AXES = {'X': 0, 'Y': 1, 'Z': 2}
FORWARD_ANGLE = {'+X': 0.0, '-X': math.pi, '+Y': math.pi / 2, '-Y': -math.pi / 2}
LOOP_KINDS = {'spin', 'sway', 'swing', 'bounce', 'drift', 'path', 'walk'}
ALL_KINDS = LOOP_KINDS | {'hinge'}
RENDER_TIMES = (0.0, 0.8, 1.6, 2.4)
CORNER_FRACTION = 0.15      # ventana de giro suave = 15 % del tramo más corto en cada esquina
WALK_CADENCE_HZ = 2.0       # pasos (jorobas |sin|) por segundo si no hay params.steps
BBOX_TOL = 1e-6
POSE_TOL = 1e-6
GLB_LOOP_TOL = 1e-5
CONVENTIONS = {
    'time': 'frame f -> t = f / fps; primer frame 0',
    'sampling': 'una clave por frame (paso 1), interpolación LINEAR; exportador con muestreo forzado paso 1',
    'clipDuration': 'por clip (salvo hinge): D = max(period); N = round(D*fps) frames; D_eff = N/fps; '
                    'cada objeto k = max(1, round(D/period)) ciclos, period_eff = D_eff/k',
    'hinge': 'apertura única 0 -> angle_deg con smoothstep en round(period*fps) frames; no es bucle; '
             'frame 0 cerrada, último abierta, HOLD después',
    'spin': 'angle = direction * 2pi * (k*t/D + phase)',
    'sway': 'angle = amplitude * sin(2pi*(k*t/D + phase))',
    'swing': 'péndulo: angle = amplitude * sin(2pi*(k*t/D + phase)) (misma forma que sway, pivote arriba)',
    'bounce': 'z = pivot.z + height * |sin(pi*(k*t/D + phase))|',
    'drift': 'offset a lo largo de axis = (distance/2) * sin(2pi*(k*t/D + phase)); excursión total = distance',
    'path': 'polilínea cerrada de points (se cierra al primer punto), velocidad constante por longitud de arco, '
            'phase desplaza el arranque; yaw en Z = heading - ángulo(forward), giro smoothstep en una ventana de corner*min(tramos) a cada lado de la esquina (corner por defecto 0.15, máx. 0.5)',
    'walk': 'path + z += bob * |sin(pi * steps * vuelta)|; steps = params.steps o max(2, round(2.0 Hz * period_eff))',
    'rotation': 'rotation_euler XYZ; solo se clavan los canales usados; yaw desenrollado entre frames',
}


# ============================ PURA (sin bpy) ============================
def num(params, key, default):
    value = params.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'params.{key} debe ser número (recibido {value!r})')
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f'params.{key} no es finito')
    return value


def smoothstep(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def wrap_pi(angle):
    """Lleva un ángulo a [-pi, pi)."""
    return (angle + math.pi) % TAU - math.pi


def clip_timing(specs, fps):
    """specs: lista de dicts con 'kind' y 'params'. Devuelve timing común del clip.

    Retorna {'loopFrames', 'loopDurationRequested', 'loopDurationEffective',
             'frames', 'objects': [{'frames','cycles','periodRequested','periodEffective'}]}.
    """
    loop_periods = [num(s['params'], 'period', 0.0) for s in specs if s['kind'] in LOOP_KINDS]
    for p in loop_periods:
        if p <= 0:
            raise ValueError('period debe ser > 0')
    d_req = max(loop_periods) if loop_periods else 0.0
    n_loop = max(1, int(round(d_req * fps))) if loop_periods else 0
    d_eff = n_loop / fps if loop_periods else 0.0
    per_obj = []
    for s in specs:
        period = num(s['params'], 'period', 0.0)
        if period <= 0:
            raise ValueError('period debe ser > 0')
        if s['kind'] == 'hinge':
            n = max(1, int(round(period * fps)))
            per_obj.append({'frames': n, 'cycles': None, 'periodRequested': period,
                            'periodEffective': n / fps})
        else:
            k = max(1, int(round(d_req / period)))
            per_obj.append({'frames': n_loop, 'cycles': k, 'periodRequested': period,
                            'periodEffective': d_eff / k})
    frames = max([o['frames'] for o in per_obj] or [0])
    return {'loopFrames': n_loop, 'loopDurationRequested': d_req, 'loopDurationEffective': d_eff,
            'frames': frames, 'objects': per_obj}


def build_path(points_flat):
    """points planos (x,y,z,...) -> polilínea cerrada sin tramos nulos y longitudes."""
    if not isinstance(points_flat, (list, tuple)) or len(points_flat) < 6 or len(points_flat) % 3:
        raise ValueError('points debe ser lista plana x,y,z con ≥2 puntos')
    pts = [tuple(float(points_flat[i + j]) for j in range(3)) for i in range(0, len(points_flat), 3)]
    clean = []
    for p in pts:
        if not clean or math.dist(p, clean[-1]) > 1e-9:
            clean.append(p)
    if len(clean) > 1 and math.dist(clean[0], clean[-1]) <= 1e-9:
        clean.pop()
    if len(clean) < 2:
        raise ValueError('points sin recorrido (menos de 2 puntos distintos)')
    segs = []
    for i, a in enumerate(clean):
        b = clean[(i + 1) % len(clean)]
        length = math.dist(a, b)
        heading = math.atan2(b[1] - a[1], b[0] - a[0])
        segs.append({'a': a, 'b': b, 'length': length, 'heading': heading})
    total = sum(s['length'] for s in segs)
    if total <= 1e-9:
        raise ValueError('recorrido de longitud nula')
    # Si un tramo es vertical puro (sin XY) su heading no está definido: hereda el anterior.
    for i, s in enumerate(segs):
        if math.hypot(s['b'][0] - s['a'][0], s['b'][1] - s['a'][1]) <= 1e-9:
            s['heading'] = segs[i - 1]['heading']
    return {'points': clean, 'segments': segs, 'length': total}


def path_sample(path, s, corner_fraction=CORNER_FRACTION):
    """Posición y heading (rad, en XY) a longitud de arco s (módulo la longitud total)."""
    segs = path['segments']
    n = len(segs)
    s = s % path['length']
    j = 0
    while j < n - 1 and s > segs[j]['length']:
        s -= segs[j]['length']
        j += 1
    seg = segs[j]
    d = min(max(s, 0.0), seg['length'])
    u = d / seg['length'] if seg['length'] > 0 else 0.0
    pos = tuple(seg['a'][i] + (seg['b'][i] - seg['a'][i]) * u for i in range(3))
    prev_seg, next_seg = segs[j - 1], segs[(j + 1) % n]
    w_start = corner_fraction * min(prev_seg['length'], seg['length'])
    w_end = corner_fraction * min(seg['length'], next_seg['length'])
    heading = seg['heading']
    if n > 1 and w_start > 0 and d < w_start:
        delta = wrap_pi(seg['heading'] - prev_seg['heading'])
        heading = prev_seg['heading'] + smoothstep(0.5 + d / (2 * w_start)) * delta
    elif n > 1 and w_end > 0 and d > seg['length'] - w_end:
        delta = wrap_pi(next_seg['heading'] - seg['heading'])
        heading = seg['heading'] + smoothstep((d - (seg['length'] - w_end)) / (2 * w_end)) * delta
    return pos, heading


def pose_at(kind, params, axis, pivot, frame, fps, timing_obj, loop_frames, path=None):
    """Pose de mundo del pivote en un frame: (location[3], rotation_euler[3], channels)."""
    pivot = [float(x) for x in pivot]
    loc = list(pivot)
    rot = [0.0, 0.0, 0.0]
    ax = AXES[axis]
    phase = num(params, 'phase', 0.0)
    if kind == 'hinge':
        angle = math.radians(num(params, 'angle_deg', 90.0))
        rot[ax] = angle * smoothstep(frame / timing_obj['frames'])
        return loc, rot, ('rotation_euler', ax)
    k = timing_obj['cycles']
    u = k * frame / loop_frames + phase      # ciclos transcurridos
    if kind == 'spin':
        direction = 1.0 if num(params, 'direction', 1.0) >= 0 else -1.0
        rot[ax] = direction * TAU * u
        return loc, rot, ('rotation_euler', ax)
    if kind in ('sway', 'swing'):
        rot[ax] = math.radians(num(params, 'amplitude_deg', 10.0)) * math.sin(TAU * u)
        return loc, rot, ('rotation_euler', ax)
    if kind == 'bounce':
        loc[2] += num(params, 'height', 0.0) * abs(math.sin(math.pi * u))
        return loc, rot, ('location', None)
    if kind == 'drift':
        loc[ax] += 0.5 * num(params, 'distance', 0.0) * math.sin(TAU * u)
        return loc, rot, ('location', None)
    if kind in ('path', 'walk'):
        forward = params.get('forward', '-Y')
        if forward not in FORWARD_ANGLE:
            raise ValueError(f'forward inválido: {forward!r}')
        corner = num(params, 'corner', CORNER_FRACTION)
        pos, heading = path_sample(path, u * path['length'], min(0.5, max(0.0, corner)))
        loc = list(pos)
        rot[2] = heading - FORWARD_ANGLE[forward]
        if kind == 'walk':
            steps = walk_steps(params, timing_obj)
            loc[2] += num(params, 'bob', 0.0) * abs(math.sin(math.pi * steps * (u - phase)))
        return loc, rot, ('location+yaw', 2)
    raise ValueError('kind desconocido: ' + str(kind))


def walk_steps(params, timing_obj):
    if 'steps' in params:
        return max(1, int(round(num(params, 'steps', 2))))
    return max(2, int(round(WALK_CADENCE_HZ * timing_obj['periodEffective'])))


def sample_object(kind, params, axis, pivot, fps, timing_obj, loop_frames):
    """Lista de poses para frames 0..frames (incluido). Desenrolla rotaciones."""
    path = build_path(params.get('points')) if kind in ('path', 'walk') else None
    n = timing_obj['frames']
    samples = []
    for f in range(n + 1):
        loc, rot, channels = pose_at(kind, params, axis, pivot, f, fps, timing_obj, loop_frames, path)
        if samples:
            prev = samples[-1]['rot']
            rot = [prev[i] + wrap_pi(rot[i] - prev[i]) for i in range(3)]
        samples.append({'frame': f, 'loc': loc, 'rot': rot})
    return samples, channels


def euler_xyz_matrix(rot):
    """Matriz 3x3 de rotation_euler 'XYZ' de Blender (R = Rz @ Ry @ Rx)."""
    cx, sx = math.cos(rot[0]), math.sin(rot[0])
    cy, sy = math.cos(rot[1]), math.sin(rot[1])
    cz, sz = math.cos(rot[2]), math.sin(rot[2])
    return [[cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
            [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
            [-sy, cy * sx, cy * cx]]


def pose_distance(a, b):
    """Máxima diferencia entre dos poses (traslación y matriz de rotación)."""
    dl = max(abs(a['loc'][i] - b['loc'][i]) for i in range(3))
    ma, mb = euler_xyz_matrix(a['rot']), euler_xyz_matrix(b['rot'])
    dr = max(abs(ma[i][j] - mb[i][j]) for i in range(3) for j in range(3))
    return max(dl, dr)


def max_frame_step(samples):
    return max((pose_distance(samples[i], samples[i + 1]) for i in range(len(samples) - 1)), default=0.0)


# ---------- GLB (puro) ----------
COMPONENTS = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
CTYPES = {5126: ('f', 4), 5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2), 5123: ('H', 2), 5125: ('I', 4)}


def parse_glb(data):
    magic, version, length = struct.unpack_from('<III', data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError('no es GLB 2.0')
    offset, doc, binary = 12, None, b''
    while offset < min(length, len(data)):
        chunk_len, chunk_type = struct.unpack_from('<II', data, offset)
        body = data[offset + 8: offset + 8 + chunk_len]
        if chunk_type == 0x4E4F534A:
            doc = json.loads(body.decode('utf-8'))
        elif chunk_type == 0x004E4942:
            binary = body
        offset += 8 + chunk_len
    if doc is None:
        raise ValueError('GLB sin chunk JSON')
    return doc, binary


def read_accessor(doc, binary, index):
    acc = doc['accessors'][index]
    count, ncomp = acc['count'], COMPONENTS[acc['type']]
    fmt, size = CTYPES[acc['componentType']]
    if 'bufferView' not in acc:
        return [tuple([0.0] * ncomp)] * count
    view = doc['bufferViews'][acc['bufferView']]
    base = view.get('byteOffset', 0) + acc.get('byteOffset', 0)
    stride = view.get('byteStride', size * ncomp)
    out = []
    for i in range(count):
        vals = struct.unpack_from('<' + fmt * ncomp, binary, base + i * stride)
        if acc.get('normalized') and fmt != 'f':
            limit = float(2 ** (8 * size - (1 if fmt.islower() else 0)) - 1)
            vals = tuple(max(v / limit, -1.0) for v in vals)
        out.append(tuple(float(v) for v in vals))
    return out


def glb_animation_report(doc, binary):
    """Resumen por animación: duración, nodos animados (con part_id) y cierre de bucle."""
    nodes = doc.get('nodes', [])
    report = {}
    for anim in doc.get('animations', []):
        name = anim.get('name', '')
        targets, t_max, closures = set(), 0.0, []
        for ch in anim.get('channels', []):
            node = ch['target'].get('node')
            path = ch['target'].get('path')
            sampler = anim['samplers'][ch['sampler']]
            times = read_accessor(doc, binary, sampler['input'])
            values = read_accessor(doc, binary, sampler['output'])
            if sampler.get('interpolation') == 'CUBICSPLINE':
                values = values[1::3]
            if node is not None:
                targets.add(node)
            if times:
                t_max = max(t_max, times[-1][0])
            if values:
                first, last = values[0], values[-1]
                diff = max(abs(a - b) for a, b in zip(first, last))
                if path == 'rotation':
                    diff = min(diff, max(abs(a + b) for a, b in zip(first, last)))
                closures.append({'node': node, 'path': path, 'firstLastMaxDiff': diff,
                                 'keys': len(times), 'interpolation': sampler.get('interpolation', 'LINEAR')})
        report[name] = {
            'durationS': t_max,
            'nodes': sorted(nodes[n].get('name', str(n)) for n in targets),
            'partIds': sorted({str((nodes[n].get('extras') or {}).get('part_id')) for n in targets}),
            'channels': len(anim.get('channels', [])),
            'maxFirstLastDiff': max((c['firstLastMaxDiff'] for c in closures), default=0.0),
            'interpolations': sorted({c['interpolation'] for c in closures}),
        }
    return report


# ============================ Blender ============================
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def posix(path):
    """Ruta para JSON con '/' siempre (Blender de Windows desde WSL usa '\\')."""
    return str(path).replace('\\', '/')


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def to_py(value):
    if hasattr(value, 'to_dict'):
        return {k: to_py(v) for k, v in value.to_dict().items()}
    if hasattr(value, 'to_list'):
        return value.to_list()
    if isinstance(value, dict):
        return {k: to_py(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_py(v) for v in value]
    return value


def check(checks, name, ok, actual=None):
    checks.append({'name': name, 'status': 'PASS' if ok else 'FAIL', 'actual': actual})
    return ok


def world_bbox(obj):
    mw = obj.matrix_world
    pts = [mw @ v.co for v in obj.data.vertices]
    if not pts:
        return [[0.0] * 3, [0.0] * 3]
    return [[min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]]


def triangle_count(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def is_identity(matrix, tol=1e-9):
    return all(abs(matrix[i][j] - (1.0 if i == j else 0.0)) <= tol for i in range(4) for j in range(4))


def action_fcurves(action, slot):
    """F-curves de la acción para un slot (Blender 4.4+/5.x) con fallbacks."""
    try:
        from bpy_extras import anim_utils
        getter = getattr(anim_utils, 'action_get_channelbag_for_slot', None)
    except ImportError:
        getter = None
    if getter is not None and slot is not None:
        channelbag = getter(action, slot)
        if channelbag is not None:
            return list(channelbag.fcurves), 'channelbag'
    if hasattr(action, 'fcurves'):
        return list(action.fcurves), 'action.fcurves'
    found = []
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            for bag in getattr(strip, 'channelbags', []):
                found.extend(bag.fcurves)
    return found, 'layers.strips.channelbags'


def read_anim(obj):
    params = to_py(obj.get('anim_params', {})) or {}
    return {'clip': str(obj['anim_clip']), 'kind': str(obj.get('anim_kind', '')),
            'axis': str(obj.get('anim_axis', 'Z')), 'pivot': [float(x) for x in to_py(obj.get('anim_pivot', []))],
            'params': params}


def repivot(obj, pivot):
    """Origen al pivote sin mover la geometría en mundo. Devuelve registro."""
    before = world_bbox(obj)
    record = {'object': obj.name, 'pivot': pivot, 'bboxBefore': before}
    if obj.parent is not None or not is_identity(obj.matrix_world):
        record.update({'repivoted': False, 'reason': 'transformación de reposo no identidad o con padre'})
        return record, False
    if obj.data.users > 1:
        obj.data = obj.data.copy()
        record['meshCopiedFromShared'] = True
    obj.rotation_mode = 'XYZ'
    obj.data.transform(Matrix.Translation(-Vector(pivot)))
    obj.data.update()
    obj.location = Vector(pivot)
    bpy.context.view_layer.update()
    after = world_bbox(obj)
    diff = max(abs(before[a][i] - after[a][i]) for a in range(2) for i in range(3))
    record.update({'repivoted': True, 'bboxAfter': after, 'bboxMaxDiffM': diff, 'pass': diff <= BBOX_TOL})
    return record, diff <= BBOX_TOL


def bake_object(obj, clip, samples, channels, frames):
    """Clava las muestras en una acción nueva y la pasa a una pista NLA llamada clip."""
    ad = obj.animation_data or obj.animation_data_create()
    action = bpy.data.actions.new(f'{clip}__{obj.name}')
    ad.action = action
    paths = []
    if channels[0] in ('location', 'location+yaw'):
        paths.append(('location', -1))
    if channels[0] == 'rotation_euler':
        paths.append(('rotation_euler', channels[1]))
    if channels[0] == 'location+yaw':
        paths.append(('rotation_euler', 2))
    for s in samples:
        obj.location = Vector(s['loc'])
        obj.rotation_euler = Euler(s['rot'], 'XYZ')
        for data_path, index in paths:
            obj.keyframe_insert(data_path=data_path, index=index, frame=s['frame'])
    slot = getattr(ad, 'action_slot', None)
    fcurves, api = action_fcurves(action, slot)
    for fc in fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
        fc.update()
    action.use_frame_range = True
    action.frame_start = 0
    action.frame_end = frames
    track = ad.nla_tracks.new()
    track.name = clip
    strip = track.strips.new(clip, 0, action)
    slot_assigned = None
    if hasattr(strip, 'action_slot'):
        if strip.action_slot is None and slot is not None:
            strip.action_slot = slot
        slot_assigned = strip.action_slot.identifier if strip.action_slot is not None else None
    strip.extrapolation = 'HOLD'
    strip.blend_type = 'REPLACE'
    ad.action = None
    # Reposo = frame 0 (puerta cerrada) para la pose estática del nodo glTF.
    obj.location = Vector(samples[0]['loc'])
    obj.rotation_euler = Euler(samples[0]['rot'], 'XYZ')
    return {'action': action.name, 'slot': slot.identifier if slot is not None else None,
            'stripSlot': slot_assigned, 'fcurveApi': api, 'fcurves': len(fcurves),
            'keysPerFcurve': sorted({len(fc.keyframe_points) for fc in fcurves}),
            'interpolations': sorted({kp.interpolation for fc in fcurves for kp in fc.keyframe_points}),
            'track': track.name, 'strip': [strip.frame_start, strip.frame_end],
            'keyedPaths': [f'{p}[{i}]' for p, i in paths]}


def expected_matrix(sample):
    return Matrix.Translation(Vector(sample['loc'])) @ Euler(sample['rot'], 'XYZ').to_matrix().to_4x4()


def matrix_diff(a, b):
    return max(abs(a[i][j] - b[i][j]) for i in range(4) for j in range(4))


def gltf_kwargs(filepath):
    wanted = {
        'filepath': filepath, 'check_existing': False, 'export_format': 'GLB',
        'use_selection': True, 'use_visible': False, 'use_renderable': False,
        'export_yup': True, 'export_extras': True, 'export_apply': False,
        'export_cameras': False, 'export_lights': False,
        'export_materials': 'EXPORT', 'export_normals': True, 'export_texcoords': True,
        'export_animations': True, 'export_animation_mode': 'NLA_TRACKS',
        'export_nla_strips': True,                      # nombre previo a 3.6 del modo por pistas
        'export_merge_animation': 'NLA_TRACK',
        'export_force_sampling': True, 'export_frame_step': 1, 'export_frame_range': False,
        'export_anim_slide_to_zero': False, 'export_negative_frame': 'SLIDE',
        'export_current_frame': False, 'export_bake_animation': False,
        'export_optimize_animation_size': False, 'export_optimize_animation_keep_anim_object': True,
        'export_def_bones': False, 'export_skins': False,
    }
    always = {'filepath', 'export_format'}     # export_format='GLB' se aplica siempre
    props = bpy.ops.export_scene.gltf.get_rna_type().properties
    applied, dropped, notes = {}, {}, {}
    for key, value in wanted.items():
        if key not in props.keys():
            if key in always:
                applied[key] = value
                notes[key] = 'applied (forced; not in RNA listing)'
            else:
                dropped[key] = 'no existe en esta versión'
            continue
        prop = props[key]
        if prop.type == 'ENUM' and not getattr(prop, 'is_enum_flag', False):
            try:
                items = [item.identifier for item in prop.enum_items]
            except Exception:
                items = []
            # Enums dinámicos (p. ej. export_format en 5.2) devuelven items vacíos
            # sin contexto: se pasan sin validar y se registran.
            if not items:
                applied[key] = value
                notes[key] = 'applied (unvalidated enum)'
                continue
            if value not in items:
                if key in always:
                    applied[key] = value
                    notes[key] = f'applied (forced; {value!r} not in {items})'
                else:
                    dropped[key] = f'valor {value!r} no está en {items}'
                continue
            notes[key] = 'applied (validated enum)'
        applied[key] = value
    return applied, dropped, notes


def gltf_addon_version():
    try:
        import addon_utils
        for mod in addon_utils.modules():
            if mod.__name__.endswith('io_scene_gltf2'):
                return '.'.join(str(x) for x in addon_utils.module_bl_info(mod).get('version', ()))
    except Exception as exc:  # solo informativo
        return f'desconocida ({exc})'
    return 'desconocida'


def animate(source, brief_path, outdir):
    brief = json.loads(brief_path.read_text(encoding='utf-8'))
    anims = brief['animations']
    fps = int(anims.get('fps', 24))
    clips_brief = anims['clips']
    if any(outdir.iterdir()):
        raise ValueError('OUTDIR no está vacío: ' + str(outdir))
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    scene.render.fps = fps
    scene.render.fps_base = 1.0
    checks = []
    meshes = [o for o in scene.objects if o.type == 'MESH']
    check(checks, 'source-has-no-actions', not bpy.data.actions, len(bpy.data.actions))
    check(checks, 'meshes-have-part_id', all(o.get('part_id') for o in meshes),
          [o.name for o in meshes if not o.get('part_id')])

    # Recoger metadatos por clip.
    by_clip, invalid = {}, []
    for o in sorted(meshes, key=lambda x: x.name):
        if 'anim_clip' not in o.keys():
            continue
        spec = read_anim(o)
        problems = []
        if spec['kind'] not in ALL_KINDS:
            problems.append('kind desconocido')
        if spec['axis'] not in AXES:
            problems.append('axis inválido')
        if len(spec['pivot']) != 3 or not all(math.isfinite(x) for x in spec['pivot']):
            problems.append('pivot inválido')
        if problems:
            invalid.append({'object': o.name, 'problems': problems, 'spec': spec})
            continue
        by_clip.setdefault(spec['clip'], []).append((o, spec))
    check(checks, 'anim-metadata-valid', not invalid, invalid)
    check(checks, 'clips-known', set(by_clip) <= set(clips_brief), sorted(set(by_clip) - set(clips_brief)))
    check(checks, 'clips-complete', all(by_clip.get(c) for c in clips_brief),
          {c: len(by_clip.get(c, [])) for c in clips_brief})
    wrong_part = [{'object': o.name, 'part_id': o.get('part_id'), 'clip': c}
                  for c, items in by_clip.items() for o, _ in items
                  if c in clips_brief and o.get('part_id') not in clips_brief[c].get('parts', [])]
    check(checks, 'clip-parts-match-brief', not wrong_part, wrong_part)

    # Re-pivotar (antes de cualquier clave).
    repivots, repivot_ok = [], True
    for clip, items in by_clip.items():
        for o, spec in items:
            record, ok = repivot(o, spec['pivot'])
            repivots.append(record)
            repivot_ok &= ok
    check(checks, 'repivot-bbox-unchanged', repivot_ok,
          {'objects': len(repivots), 'maxDiffM': max((r.get('bboxMaxDiffM', 0.0) for r in repivots), default=0.0),
           'tolM': BBOX_TOL, 'failed': [r['object'] for r in repivots if not r.get('pass')]})

    # Muestreo, acciones y NLA.
    clips_out, objects_out, sample_store = {}, [], {}
    pivoted = {r['object'] for r in repivots if r.get('pass')}
    for clip in sorted(by_clip):
        items = [(o, s) for o, s in by_clip[clip] if o.name in pivoted]
        if not items:
            continue
        timing = clip_timing([s for _, s in items], fps)
        clips_out[clip] = {'objects': [], 'frames': timing['frames'], 'durationS': timing['frames'] / fps,
                           'loopDurationRequestedS': timing['loopDurationRequested'],
                           'loopDurationEffectiveS': timing['loopDurationEffective'],
                           'kinds': sorted({s['kind'] for _, s in items}),
                           'autoplay': clips_brief.get(clip, {}).get('autoplay'),
                           'trigger': clips_brief.get(clip, {}).get('trigger'),
                           'loop': all(s['kind'] != 'hinge' for _, s in items)}
        for (o, spec), t_obj in zip(items, timing['objects']):
            samples, channels = sample_object(spec['kind'], spec['params'], spec['axis'], spec['pivot'],
                                              fps, t_obj, timing['loopFrames'])
            baked = bake_object(o, clip, samples, channels, t_obj['frames'])
            sample_store[o.name] = samples
            clips_out[clip]['objects'].append(o.name)
            objects_out.append({'object': o.name, 'part_id': o.get('part_id'), 'clip': clip, 'kind': spec['kind'],
                                'axis': spec['axis'], 'pivot': spec['pivot'], 'params': spec['params'],
                                'periodRequestedS': t_obj['periodRequested'], 'periodEffectiveS': t_obj['periodEffective'],
                                'cycles': t_obj['cycles'], 'frames': t_obj['frames'],
                                'loopClosurePure': pose_distance(samples[0], samples[-1]),
                                'maxPerFrameChange': max_frame_step(samples), **baked})
    total_frames = max([c['frames'] for c in clips_out.values()] or [1])
    scene.frame_start = 0
    scene.frame_end = total_frames

    # Comprobaciones en Blender: NLA, slots, interpolación y evaluación.
    check(checks, 'nla-tracks-named-by-clip',
          all(len(o.animation_data.nla_tracks) == 1 and o.animation_data.nla_tracks[0].name == rec['clip']
              for rec in objects_out for o in [bpy.data.objects[rec['object']]]),
          len(objects_out))
    check(checks, 'active-action-none',
          all(bpy.data.objects[r['object']].animation_data.action is None for r in objects_out))
    check(checks, 'fcurves-found-linear',
          all(r['fcurves'] > 0 and r['interpolations'] == ['LINEAR'] for r in objects_out),
          sorted({(r['fcurveApi'], tuple(r['interpolations'])) for r in objects_out}))
    check(checks, 'strip-slot-assigned', all(r['stripSlot'] is not None or r['slot'] is None for r in objects_out),
          [r['object'] for r in objects_out if r['slot'] is not None and r['stripSlot'] is None])
    eval_fail, loop_fail, hinge_fail = [], [], []
    max_eval = max_loop = 0.0
    probes = {}                     # frame -> objetos a evaluar (un frame_set por frame)
    for rec in objects_out:
        n = rec['frames']
        for f in {0, n // 3, (2 * n) // 3, n}:
            probes.setdefault(f, []).append(rec['object'])
    evaluated = {}
    for f in sorted(probes):
        scene.frame_set(f)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for name in probes[f]:
            evaluated[(name, f)] = bpy.data.objects[name].evaluated_get(depsgraph).matrix_world.copy()
    for rec in objects_out:
        name, n = rec['object'], rec['frames']
        samples = sample_store[name]
        for f in sorted({0, n // 3, (2 * n) // 3, n}):
            d = matrix_diff(evaluated[(name, f)], expected_matrix(samples[f]))
            max_eval = max(max_eval, d)
            if d > POSE_TOL:
                eval_fail.append({'object': name, 'frame': f, 'diff': d})
        if rec['kind'] == 'hinge':
            angle = math.radians(num(rec['params'], 'angle_deg', 90.0))
            ax = AXES[rec['axis']]
            if abs(samples[0]['rot'][ax]) > 1e-9 or abs(samples[-1]['rot'][ax] - angle) > 1e-9:
                hinge_fail.append(name)
        else:
            d = matrix_diff(evaluated[(name, 0)], evaluated[(name, n)])
            rec['loopClosureEvaluated'] = d
            max_loop = max(max_loop, d)
            if d > POSE_TOL:
                loop_fail.append({'object': name, 'diff': d})
    check(checks, 'nla-evaluation-matches-samples', not eval_fail, {'maxDiff': max_eval, 'failures': eval_fail[:20]})
    check(checks, 'loops-close-exactly', not loop_fail, {'maxDiff': max_loop, 'failures': loop_fail[:20]})
    check(checks, 'hinge-closed-to-open', not hinge_fail, hinge_fail)
    scene.frame_set(0)

    # Conteos para verify.
    tri_total = sum(triangle_count(o) for o in meshes)
    blend_path = outdir / 'animated.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)

    # Exportación: solo mallas, modo pistas NLA.
    for o in bpy.context.view_layer.objects:
        o.select_set(o.type == 'MESH')
    glb_path = outdir / 'animated.glb'
    applied, dropped, notes = gltf_kwargs(str(glb_path))
    essential = {'export_format', 'use_selection', 'export_yup', 'export_extras', 'export_animations'}
    check(checks, 'exporter-essential-kwargs', essential <= set(applied), sorted(essential - set(applied)))
    check(checks, 'exporter-nla-mode', applied.get('export_animation_mode') == 'NLA_TRACKS'
          or applied.get('export_nla_strips') is True,
          {k: applied.get(k) for k in ('export_animation_mode', 'export_nla_strips')})
    bpy.ops.export_scene.gltf(**applied)
    scene.frame_set(0)
    doc, binary = parse_glb(glb_path.read_bytes())
    glb_anims = glb_animation_report(doc, binary)
    check(checks, 'glb-one-animation-per-clip', sorted(glb_anims) == sorted(clips_out),
          {'glb': sorted(glb_anims), 'expected': sorted(clips_out)})
    dur_bad = {c: [glb_anims[c]['durationS'], clips_out[c]['durationS']] for c in clips_out
               if c in glb_anims and abs(glb_anims[c]['durationS'] - clips_out[c]['durationS']) > 0.5 / fps}
    check(checks, 'glb-durations-match', not dur_bad, dur_bad)
    node_bad = {c: [len(glb_anims[c]['nodes']), len(clips_out[c]['objects'])] for c in clips_out
                if c in glb_anims and len(glb_anims[c]['nodes']) != len(clips_out[c]['objects'])}
    check(checks, 'glb-animated-nodes-match', not node_bad, node_bad)
    loop_bad = {c: glb_anims[c]['maxFirstLastDiff'] for c in clips_out
                if c in glb_anims and clips_out[c]['loop'] and glb_anims[c]['maxFirstLastDiff'] > GLB_LOOP_TOL}
    check(checks, 'glb-loops-close', not loop_bad, loop_bad)
    glb_size = glb_path.stat().st_size
    budget = brief.get('budgets', {}).get('glbBytes')
    check(checks, 'glb-size-budget', budget is None or glb_size <= budget, {'bytes': glb_size, 'budget': budget})
    check(checks, 'glb-no-cameras-lights', not doc.get('cameras') and
          not (doc.get('extensions', {}).get('KHR_lights_punctual', {}).get('lights')),
          {'cameras': len(doc.get('cameras', []))})

    # Renders con cámara/luces existentes.
    renders_dir = outdir / 'renders'
    renders_dir.mkdir()
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    renders = []
    for t in RENDER_TIMES:
        frame_f = t * fps
        frame_i = int(math.floor(frame_f + 1e-9))
        sub = max(0.0, frame_f - frame_i)
        scene.frame_set(frame_i, subframe=sub)
        path = renders_dir / f'anim-{frame_f:06.2f}.png'
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders.append({'timeS': t, 'frame': frame_f, 'file': posix(path.relative_to(outdir)),
                        'sha256': digest(path) if path.exists() else None})
    check(checks, 'renders-written', all(r['sha256'] for r in renders), [r['file'] for r in renders])
    scene.frame_set(0)

    status = 'PASS' if all(c['status'] == 'PASS' for c in checks) else 'FAIL'
    write_json(outdir / 'anim-result.json', {
        'status': status, 'stage': 'animate', 'checks': checks,
        'blenderVersion': bpy.app.version_string, 'gltfAddonVersion': gltf_addon_version(),
        'source': {'path': posix(source), 'sha256': digest(source)},
        'brief': {'path': posix(brief_path), 'sha256': digest(brief_path)},
        'worker': {'path': posix(Path(__file__).resolve()), 'sha256': digest(Path(__file__).resolve())},
        'fps': fps, 'sceneFrames': [scene.frame_start, scene.frame_end], 'conventions': CONVENTIONS,
        'clips': clips_out, 'objects': objects_out, 'repivot': repivots,
        'counts': {'meshObjects': len(meshes), 'triangles': tri_total, 'animatedObjects': len(objects_out)},
        'exporter': {'applied': {k: v for k, v in applied.items() if k != 'filepath'}, 'dropped': dropped,
                     'notes': notes},
        'glbAnimations': glb_anims, 'glbBytes': glb_size,
        'files': {'animated.blend': digest(blend_path), 'animated.glb': digest(glb_path)},
        'renders': renders,
    })
    return status


def anim_names(obj):
    ad = obj.animation_data
    names = set()
    if ad is None:
        return names
    if ad.action is not None:
        names.add(ad.action.name)
    for track in ad.nla_tracks:
        names.add(track.name)
        for strip in track.strips:
            names.add(strip.name)
            if strip.action is not None:
                names.add(strip.action.name)
    return names


def name_matches(name, clip):
    return name == clip or name.startswith(clip + '_') or name.startswith(clip + '.') or clip in name


def verify(glb_path, brief_path, outdir):
    brief = json.loads(brief_path.read_text(encoding='utf-8'))
    clips = list(brief['animations']['clips'])
    prior = json.loads((outdir / 'anim-result.json').read_text(encoding='utf-8'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    bpy.context.view_layer.update()
    checks = []
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    imported_names = set(a.name for a in bpy.data.actions)
    for o in bpy.context.scene.objects:
        imported_names |= anim_names(o)
    per_clip = {}
    for clip in clips:
        exact = [o.name for o in bpy.context.scene.objects
                 if any(t.name == clip for t in (o.animation_data.nla_tracks if o.animation_data else []))]
        loose = [o.name for o in bpy.context.scene.objects if any(name_matches(n, clip) for n in anim_names(o))]
        per_clip[clip] = {'objectsExactTrack': len(exact), 'objectsAnyName': len(loose),
                          'names': sorted(n for n in imported_names if name_matches(n, clip))[:10]}
    check(checks, 'imported-clip-names', all(per_clip[c]['names'] for c in clips),
          [c for c in clips if not per_clip[c]['names']])
    check(checks, 'each-clip-animates-objects', all(per_clip[c]['objectsAnyName'] >= 1 for c in clips),
          {c: per_clip[c]['objectsAnyName'] for c in clips})
    missing_part = [o.name for o in meshes if not o.get('part_id')]
    check(checks, 'meshes-keep-part_id', not missing_part, missing_part[:20])
    tris = sum(triangle_count(o) for o in meshes)
    check(checks, 'mesh-count-matches', len(meshes) == prior['counts']['meshObjects'],
          {'imported': len(meshes), 'animate': prior['counts']['meshObjects']})
    check(checks, 'triangle-count-matches', tris == prior['counts']['triangles'],
          {'imported': tris, 'animate': prior['counts']['triangles']})
    check(checks, 'glb-sha256-matches-animate', digest(glb_path) == prior['files']['animated.glb'], digest(glb_path))
    doc, binary = parse_glb(glb_path.read_bytes())
    glb_anims = glb_animation_report(doc, binary)
    check(checks, 'glb-json-clips', all(c in glb_anims for c in clips), sorted(glb_anims))
    no_pid = {c: glb_anims[c]['partIds'] for c in clips if c in glb_anims and 'None' in glb_anims[c]['partIds']}
    check(checks, 'glb-animated-nodes-have-part_id', not no_pid, no_pid)
    write_json(outdir / 'verify-result.json', {
        'status': 'PASS' if all(c['status'] == 'PASS' for c in checks) else 'FAIL', 'stage': 'verify',
        'checks': checks, 'blenderVersion': bpy.app.version_string, 'gltfAddonVersion': gltf_addon_version(),
        'glb': {'path': posix(glb_path), 'sha256': digest(glb_path)},
        'worker': {'path': posix(Path(__file__).resolve()), 'sha256': digest(Path(__file__).resolve())},
        'clips': per_clip, 'importedAnimationNames': sorted(imported_names),
        'counts': {'meshObjects': len(meshes), 'triangles': tris}, 'glbAnimations': glb_anims,
    })


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if len(args) != 4 or args[0] not in ('animate', 'verify'):
        raise SystemExit('uso: -- animate SOURCE.blend BRIEF.json OUTDIR | -- verify GLB BRIEF.json OUTDIR')
    stage, target, brief_path, outdir = args[0], Path(args[1]).resolve(), Path(args[2]).resolve(), Path(args[3]).resolve()
    try:
        if stage == 'animate':
            animate(target, brief_path, outdir)
        else:
            verify(target, brief_path, outdir)
    except Exception:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        name = 'anim-result.json' if stage == 'animate' else 'verify-result.json'
        try:
            write_json(outdir / name, {'status': 'FAIL', 'stage': stage, 'error': tb.replace('\\', '/'),
                                       'blenderVersion': bpy.app.version_string})
        except Exception:
            pass
        sys.exit(1)


if __name__ == '__main__' and bpy is not None:
    main()
