"""Paso de animación del diorama de la escuela (Blender 5.2.3 LTS).

Convierte los metadatos anim_* de los objetos en acciones reales (una por objeto y
clip), las mete en pistas NLA con el nombre exacto del clip y exporta GLB.

  blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
    --python anim_worker.py -- animate SOURCE.blend BRIEF.json OUTDIR
  blender ... --python anim_worker.py -- verify OUTDIR/animated.glb BRIEF.json OUTDIR
  python3 anim_worker.py selftest          # solo matemática pura, sin bpy

Las funciones de la primera mitad (muestreo, bucles, ángulos) no usan bpy.
"""
import bisect
import hashlib
import json
import math
import struct
import sys
import traceback
from pathlib import Path

try:
    import bpy
    from mathutils import Matrix, Vector
except ImportError:  # modo puro (selftest)
    bpy = None

TAU = 2.0 * math.pi
AXES = 'XYZ'
FORWARD_ANGLE = {'+X': 0.0, '-X': math.pi, '+Y': math.pi / 2.0, '-Y': -math.pi / 2.0}
RENDER_TIMES = (0.0, 0.8, 1.6, 2.4)
BBOX_TOL = 1e-6
LOOP_TOL = 1e-6


# ======================================================================
# Matemática pura
# ======================================================================
def wrap_angle(a):
    """Lleva un ángulo a (-pi, pi]."""
    a = math.fmod(a + math.pi, TAU)
    if a <= 0.0:
        a += TAU
    return a - math.pi


def smoothstep(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def hinge_profile(u):
    """Solo abrir: 0 -> 1 con ease in-out (smoothstep) a lo largo del periodo."""
    return smoothstep(u)


def idprop_to_py(value):
    """Convierte IDProperties (grupos, arrays) de Blender a tipos de Python."""
    if hasattr(value, 'to_dict'):
        return {k: idprop_to_py(v) for k, v in value.to_dict().items()}
    if hasattr(value, 'to_list'):
        return [idprop_to_py(v) for v in value.to_list()]
    if isinstance(value, dict):
        return {k: idprop_to_py(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [idprop_to_py(v) for v in value]
    return value


DEFAULTS = {
    'hinge': {'angle_deg': 90.0, 'period': 4.0},
    'spin': {'period': 8.0, 'direction': 1.0},
    'sway': {'amplitude_deg': 10.0, 'period': 3.0, 'phase': 0.0},
    'swing': {'amplitude_deg': 20.0, 'period': 3.0, 'phase': 0.0},
    'bounce': {'height': 0.005, 'period': 1.0, 'phase': 0.0},
    'drift': {'distance': 0.02, 'period': 10.0, 'phase': 0.0},
    'path': {'period': 10.0, 'phase': 0.0, 'turn_ratio': 0.3},
    'walk': {'period': 10.0, 'phase': 0.0, 'turn_ratio': 0.3, 'bob': 0.002, 'step_length': 0.012},
}


def normalize_params(kind, raw):
    """Devuelve (params_usados, advertencias). Rellena valores por defecto."""
    if kind not in DEFAULTS:
        raise ValueError('kind desconocido: %r' % (kind,))
    raw = dict(raw or {})
    warnings = []
    out = {}
    for key, default in DEFAULTS[kind].items():
        if key in raw:
            try:
                out[key] = float(raw[key])
            except (TypeError, ValueError):
                raise ValueError('param %s.%s no numérico: %r' % (kind, key, raw[key]))
        else:
            out[key] = default
            warnings.append('param %s.%s ausente, uso %r' % (kind, key, default))
    if out['period'] <= 0:
        raise ValueError('period debe ser > 0')
    if kind == 'spin':
        out['direction'] = -1.0 if out['direction'] < 0 else 1.0
    if kind in ('path', 'walk'):
        pts = raw.get('points')
        if not isinstance(pts, (list, tuple)) or len(pts) < 6 or len(pts) % 3:
            raise ValueError('path/walk requiere points plano (x,y,z)*n con n>=2')
        pts = [float(x) for x in pts]
        out['points'] = [tuple(pts[i:i + 3]) for i in range(0, len(pts), 3)]
        fwd = str(raw.get('forward', '-Y')).strip()
        if fwd not in FORWARD_ANGLE:
            raise ValueError('forward inválido: %r' % (fwd,))
        out['forward'] = fwd
        if not 0.0 <= out['turn_ratio'] <= 0.45:
            out['turn_ratio'] = min(max(out['turn_ratio'], 0.0), 0.45)
            warnings.append('turn_ratio recortado a [0, 0.45]')
        if kind == 'walk' and out['step_length'] <= 0:
            raise ValueError('step_length debe ser > 0')
    return out, warnings


def build_path(points, turn_ratio):
    """Polígono cerrado con distancia acumulada y rumbos por segmento."""
    pts = []
    for p in points:
        if not pts or math.dist(p, pts[-1]) > 1e-9:
            pts.append(tuple(p))
    if len(pts) > 1 and math.dist(pts[0], pts[-1]) <= 1e-9:
        pts.pop()
    if len(pts) < 2:
        raise ValueError('path con menos de 2 puntos distintos')
    closed = pts + [pts[0]]
    lengths = [math.dist(closed[i], closed[i + 1]) for i in range(len(pts))]
    cum = [0.0]
    for length in lengths:
        cum.append(cum[-1] + length)
    headings = []
    for i in range(len(pts)):
        dx = closed[i + 1][0] - closed[i][0]
        dy = closed[i + 1][1] - closed[i][1]
        headings.append(math.atan2(dy, dx) if math.hypot(dx, dy) > 1e-12 else None)
    last = next((h for h in headings if h is not None), 0.0)
    for i, h in enumerate(headings):  # segmentos verticales heredan el rumbo previo
        if h is None:
            headings[i] = last
        last = headings[i]
    m = len(pts)
    half = [min(lengths[(j - 1) % m], lengths[j]) * turn_ratio for j in range(m)]
    return {'pts': closed, 'cum': cum, 'total': cum[-1], 'lengths': lengths,
            'headings': headings, 'half': half, 'm': m}


def path_position(ctx, s):
    total = ctx['total']
    s = s % total
    k = min(bisect.bisect_right(ctx['cum'], s) - 1, ctx['m'] - 1)
    seg = ctx['lengths'][k]
    t = 0.0 if seg <= 0 else (s - ctx['cum'][k]) / seg
    a, b = ctx['pts'][k], ctx['pts'][k + 1]
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def path_heading(ctx, s):
    """Rumbo (rad, envuelto) en la distancia s; suaviza esquinas con smoothstep."""
    total = ctx['total']
    s = s % total
    m = ctx['m']
    k = min(bisect.bisect_right(ctx['cum'], s) - 1, m - 1)
    for j in range(m):
        h = ctx['half'][j]
        if h <= 0:
            continue
        d = (s - ctx['cum'][j] + total / 2.0) % total - total / 2.0
        if -h < d < h:
            a0 = ctx['headings'][(j - 1) % m]
            a1 = a0 + wrap_angle(ctx['headings'][j] - a0)
            return a0 + (a1 - a0) * smoothstep((d + h) / (2.0 * h))
    return ctx['headings'][k]


def pose_at(kind, p, axis, pivot, u, ctx=None):
    """Pose cruda (rot_euler[3], loc[3]) en la fase u (0..1, u=1 cierra el bucle)."""
    a = AXES.index(axis)
    rot = [0.0, 0.0, 0.0]
    loc = [float(pivot[0]), float(pivot[1]), float(pivot[2])]
    if kind == 'hinge':
        rot[a] = math.radians(p['angle_deg']) * hinge_profile(u)
    elif kind == 'spin':
        rot[a] = p['direction'] * TAU * u  # sin envolver: la rotación es continua
    elif kind == 'sway':
        rot[a] = math.radians(p['amplitude_deg']) * math.sin(TAU * (u + p['phase']))
    elif kind == 'swing':
        rot[a] = math.radians(p['amplitude_deg']) * math.cos(TAU * (u + p['phase']))
    elif kind == 'bounce':
        loc[2] += p['height'] * abs(math.sin(math.pi * (u + p['phase'])))
    elif kind == 'drift':
        loc[a] += p['distance'] * math.sin(TAU * (u + p['phase']))
    elif kind in ('path', 'walk'):
        s = (((u + p['phase']) % 1.0)) * ctx['total']
        loc = list(path_position(ctx, s))
        rot[2] = path_heading(ctx, s) - FORWARD_ANGLE[p['forward']]
        if kind == 'walk' and p['bob'] != 0.0:
            cycles = max(1, round(ctx['total'] / p['step_length']))
            loc[2] += p['bob'] * abs(math.sin(math.pi * cycles * u))
    return rot, loc


def sample_frames(n_frames, max_keys):
    step = max(1, math.ceil(n_frames / max_keys))
    frames = list(range(0, n_frames, step))
    frames.append(n_frames)
    return frames, step


def build_samples(kind, raw_params, axis, pivot, fps, max_keys=720, n_frames=None, cycles=1):
    """Muestrea un clip completo. Frames 0..N; primero == último (salvo hinge).
    n_frames: duración común del clip (si None, period*fps). cycles: ciclos del
    movimiento dentro de n_frames (period efectivo = duración/cycles)."""
    p, warnings = normalize_params(kind, raw_params)
    axis = str(axis or 'Z').upper()
    if axis not in AXES:
        raise ValueError('axis inválido: %r' % (axis,))
    if kind in ('path', 'walk'):
        axis = 'Z'
    if kind == 'bounce':
        axis = 'Z'
    exact = p['period'] * fps
    n = max(2, int(round(exact))) if n_frames is None else int(n_frames)
    cycles = 1 if kind == 'hinge' else max(1, int(cycles))
    if n_frames is None and abs(exact - round(exact)) > 1e-6:
        warnings.append('period*fps=%.4f no entero; redondeo a %d frames' % (exact, n))
    ctx = build_path(p['points'], p['turn_ratio']) if kind in ('path', 'walk') else None
    frames, step = sample_frames(n, max_keys)
    rots, locs = [], []
    prev_yaw = None
    for f in frames:
        rot, loc = pose_at(kind, p, axis, pivot, f / n * cycles, ctx)
        if kind in ('path', 'walk'):  # desenvuelve el giro para interpolar sin saltos
            if prev_yaw is not None:
                rot[2] = prev_yaw + wrap_angle(rot[2] - prev_yaw)
            prev_yaw = rot[2]
        rots.append(rot)
        locs.append(loc)
    r0, l0 = pose_at(kind, p, axis, pivot, 0.0, ctx)
    r1, l1 = pose_at(kind, p, axis, pivot, 1.0 * cycles, ctx)
    loop_error = max([abs(wrap_angle(r1[i] - r0[i])) for i in range(3)] +
                     [abs(l1[i] - l0[i]) for i in range(3)])
    open_only = kind == 'hinge'
    hinge_error = None
    if open_only:  # no es bucle: primer frame cerrado (0), ultimo abierto (angle)
        target = math.radians(p['angle_deg'])
        hinge_error = max(abs(rots[0][AXES.index(axis)]), abs(rots[-1][AXES.index(axis)] - target))
        loop_error = 0.0
    max_rot_step = 0.0
    for i in range(1, len(frames)):
        gap = frames[i] - frames[i - 1]
        for c in range(3):
            max_rot_step = max(max_rot_step, abs(rots[i][c] - rots[i - 1][c]) / gap)
    return {'kind': kind, 'axis': axis, 'cycles': cycles, 'frames': frames, 'step': step, 'n_frames': n,
            'rotation_euler': rots, 'location': locs, 'params_used': p,
            'warnings': warnings, 'loop_error': loop_error,
            'open_only': open_only, 'hinge_error': hinge_error,
            'max_rot_step_rad_per_frame': max_rot_step,
            'path_length': ctx['total'] if ctx else None}


def channel_plan(samples, rest_loc, tol=1e-9):
    """Canales a keyear: los que varían o difieren del reposo (rot 0, loc=pivot)."""
    plan = []
    for c in range(3):
        vals = [r[c] for r in samples['rotation_euler']]
        if max(vals) - min(vals) > tol or abs(vals[0]) > tol:
            plan.append(('rotation_euler', c))
    for c in range(3):
        vals = [l[c] for l in samples['location']]
        if max(vals) - min(vals) > tol or abs(vals[0] - rest_loc[c]) > tol:
            plan.append(('location', c))
    return plan


def read_glb_json(path):
    data = Path(path).read_bytes()
    magic, version, length = struct.unpack_from('<4sII', data, 0)
    if magic != b'glTF':
        raise ValueError('no es GLB: ' + str(path))
    clen, ctype = struct.unpack_from('<I4s', data, 12)
    if ctype != b'JSON':
        raise ValueError('primer chunk no es JSON')
    return json.loads(data[20:20 + clen].decode('utf-8'))


def glb_animation_summary(doc, fps):
    """{nombre: {nodes, channels, duration_s, frames}} desde el JSON de glTF."""
    out = {}
    accessors = doc.get('accessors', [])
    nodes = doc.get('nodes', [])
    for anim in doc.get('animations', []):
        name = anim.get('name', '')
        targets = sorted({nodes[c['target']['node']].get('name', str(c['target']['node']))
                          for c in anim.get('channels', []) if 'node' in c.get('target', {})})
        spans = []
        for sampler in anim.get('samplers', []):
            acc = accessors[sampler['input']]
            if 'min' in acc and 'max' in acc:
                spans.append((acc['min'][0], acc['max'][0]))
        lo = min((s[0] for s in spans), default=0.0)
        hi = max((s[1] for s in spans), default=0.0)
        entry = out.setdefault(name, {'nodes': [], 'channels': 0, 'duration_s': 0.0, 'start_s': 0.0})
        entry['nodes'] = sorted(set(entry['nodes']) | set(targets))
        entry['channels'] += len(anim.get('channels', []))
        entry['duration_s'] = max(entry['duration_s'], hi - lo)
        entry['start_s'] = lo
        entry['frames'] = round(entry['duration_s'] * fps, 3)
    return out


def selftest():
    fps = 24
    cases = [
        ('hinge', {'angle_deg': 100, 'period': 3}, 'Z', [0, 0, 0]),
        ('spin', {'period': 2, 'direction': -1}, 'Y', [0, 0, 0]),
        ('sway', {'amplitude_deg': 18, 'period': 2.4, 'phase': 0.3}, 'Z', [0, 0, 0]),
        ('swing', {'amplitude_deg': 25, 'period': 2, 'phase': 0.1}, 'X', [0, 0, 0.1]),
        ('bounce', {'height': 0.004, 'period': 0.8, 'phase': 0.2}, 'Z', [0, 0, 0]),
        ('drift', {'distance': 0.03, 'period': 20, 'phase': 0.5}, 'X', [0, 0, 0.1]),
        ('path', {'points': [-0.15, -0.126, 0, 0.15, -0.126, 0], 'period': 12, 'forward': '-Y'},
         'Z', [-0.15, -0.126, 0]),
        ('walk', {'points': [0, -0.1, 0, 0.05, -0.1, 0, 0.05, -0.05, 0, 0, -0.05, 0], 'period': 20,
                  'bob': 0.002, 'forward': '+X'}, 'Z', [0, -0.1, 0]),
    ]
    report = {}
    for kind, params, axis, pivot in cases:
        s = build_samples(kind, params, axis, pivot, fps)
        assert s['loop_error'] < LOOP_TOL, (kind, s['loop_error'])
        if kind == 'hinge':
            assert s['hinge_error'] < 1e-9 and s['open_only']
        assert s['frames'][0] == 0 and s['frames'][-1] == s['n_frames']
        assert s['max_rot_step_rad_per_frame'] < math.pi * 0.9, kind
        report[kind] = {'frames': s['n_frames'], 'keys': len(s['frames']),
                        'loop_error': s['loop_error'],
                        'max_rot_deg_per_frame': math.degrees(s['max_rot_step_rad_per_frame']),
                        'channels': channel_plan(s, pivot)}
    # hinge: 0 -> angulo en 25 %, vuelve a 0
    assert hinge_profile(0) == 0 and hinge_profile(1) == 1 and abs(hinge_profile(.5) - .5) < 1e-12
    # path rectangular: el rumbo avanza +90 grados por esquina, sin saltos
    ctx = build_path([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], 0.3)
    hs = [path_heading(ctx, i * ctx['total'] / 400) for i in range(401)]
    assert max(abs(wrap_angle(hs[i + 1] - hs[i])) for i in range(400)) < 0.06
    assert abs(wrap_angle(hs[-1] - hs[0])) < 1e-9
    # wrap_angle
    assert abs(wrap_angle(3 * math.pi) - math.pi) < 1e-9 and abs(wrap_angle(-math.pi / 2) + math.pi / 2) < 1e-12
    print(json.dumps({'ok': True, 'cases': report}, indent=1))


# ======================================================================
# Utilidades con E/S
# ======================================================================
def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False, default=str)
        stream.write('\n')


def check(checks, name, ok, detail=None):
    checks.append({'name': name, 'pass': bool(ok), 'detail': detail})
    return bool(ok)


# ======================================================================
# Blender: helpers de acciones con slots (4.4+ / 5.x)
# ======================================================================
def action_fcurves(action, slot=None):
    """F-curves de una acción: channelbag (5.x) con fallback a action.fcurves."""
    curves = []
    try:
        from bpy_extras import anim_utils
        if slot is not None:
            bag = anim_utils.action_get_channelbag_for_slot(action, slot)
            if bag is not None:
                curves = list(bag.fcurves)
    except Exception:
        curves = []
    if not curves and hasattr(action, 'fcurves'):
        try:
            curves = list(action.fcurves)
        except Exception:
            curves = []
    if not curves:  # último recurso: recorrer capas/tiras/channelbags
        try:
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        curves.extend(bag.fcurves)
        except Exception:
            pass
    return curves


def set_linear(action, slot):
    n = 0
    for fc in action_fcurves(action, slot):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
            n += 1
        fc.update()
    return n


def world_bbox(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return ([min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)])


def mesh_stats(objects):
    tris = 0
    parts = {}
    for o in objects:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
        pid = o.get('part_id', None)
        if pid is None:
            pid = o.data.get('part_id', None)
        parts[str(pid)] = parts.get(str(pid), 0) + 1
    return tris, parts


def repivot(obj, pivot):
    """Traslada la malla y pone location=pivot. Devuelve registro con bbox antes/después."""
    pivot = Vector(pivot)
    rec = {'object': obj.name, 'pivot': list(pivot), 'status': 'unchanged'}
    bpy.context.view_layer.update()
    before = world_bbox(obj)
    ident = (obj.parent is None and obj.location.length < 1e-12 and obj.scale.length_squared - 3.0 < 1e-12
             and abs(obj.scale.x - 1) < 1e-12 and abs(obj.scale.y - 1) < 1e-12 and abs(obj.scale.z - 1) < 1e-12
             and all(abs(a) < 1e-12 for a in obj.rotation_euler)
             and (obj.rotation_mode != 'QUATERNION'))
    already = (obj.parent is None and (obj.location - pivot).length < 1e-9)
    if ident:
        if obj.data.users > 1:
            obj.data = obj.data.copy()
            rec['made_single_user'] = True
        obj.data.transform(Matrix.Translation(-pivot))
        obj.data.update()
        obj.location = pivot
        rec['status'] = 'repivoted'
    elif already:
        rec['status'] = 'already_at_pivot'
    else:
        rec['status'] = 'skipped_not_identity'
    bpy.context.view_layer.update()
    after = world_bbox(obj)
    err = max(abs(before[k][i] - after[k][i]) for k in range(2) for i in range(3))
    rec.update({'bbox_before': before, 'bbox_after': after, 'max_error_m': err,
                'pass': err <= BBOX_TOL and rec['status'] != 'skipped_not_identity'})
    return rec


def author_nla(obj, clip, smp, rest_loc, fps):
    """Keyea con keyframe_insert (crea acción+slot), lo mueve a una pista NLA."""
    obj.rotation_mode = 'XYZ'
    ad = obj.animation_data_create()
    ad.action = None
    plan = channel_plan(smp, rest_loc)
    for k, frame in enumerate(smp['frames']):
        for path, idx in plan:
            getattr(obj, path)[idx] = smp[path][k][idx]
            obj.keyframe_insert(data_path=path, index=idx, frame=frame)
    action = ad.action
    if action is None:
        raise RuntimeError('keyframe_insert no creó acción en ' + obj.name)
    slot = getattr(ad, 'action_slot', None)
    action.name = '%s__%s' % (clip, obj.name)
    interp = set_linear(action, slot)
    for attr, value in (('use_frame_range', True), ('frame_start', float(smp['frames'][0])),
                        ('frame_end', float(smp['frames'][-1])), ('use_cyclic', not smp['open_only'])):
        try:
            setattr(action, attr, value)
        except Exception:
            pass
    track = ad.nla_tracks.new()
    track.name = clip
    strip = track.strips.new(clip, int(smp['frames'][0]), action)
    strip.name = clip
    slot_set = False
    if slot is not None and hasattr(strip, 'action_slot'):
        try:
            strip.action_slot = slot
            slot_set = True
        except Exception:
            slot_set = False
    ad.action = None  # el exportador usa las pistas NLA
    obj.location = rest_loc
    obj.rotation_euler = (0.0, 0.0, 0.0)
    return {'object': obj.name, 'action': action.name, 'slot': getattr(slot, 'name_display', None) if slot else None,
            'channels': ['%s[%d]' % c for c in plan], 'keys': len(smp['frames']),
            'linear_keyframes_set': interp, 'strip_frames': [strip.frame_start, strip.frame_end],
            'strip_slot_set': slot_set, 'active_action_after': ad.action is None and 'None' or ad.action.name}


def export_glb(path, extra_notes):
    wanted = {
        'filepath': str(path), 'export_format': 'GLB', 'use_selection': True, 'export_yup': True,
        'export_extras': True, 'export_cameras': False, 'export_lights': False,
        'export_apply': False, 'export_animations': True,
        'export_animation_mode': 'NLA_TRACKS', 'export_force_sampling': True,
        'export_frame_step': 1, 'export_optimize_animation_size': False,
        'export_current_frame': False, 'export_anim_single_armature': False,
        'export_morph': False, 'export_skins': False,
    }
    props = bpy.ops.export_scene.gltf.get_rna_type().properties
    valid = {p.identifier for p in props}
    applied = {k: v for k, v in wanted.items() if k in valid}
    dropped = sorted(k for k in wanted if k not in valid)
    for o in bpy.context.scene.objects:
        o.select_set(o.type == 'MESH')
    bpy.ops.export_scene.gltf(**applied)
    extra_notes.append('opciones del exportador disponibles: %d' % len(valid))
    return applied, dropped, sorted(valid)


# ======================================================================
# Etapa animate
# ======================================================================
def stage_animate(src, brief_path, outdir):
    out = Path(outdir)
    brief = json.loads(Path(brief_path).read_text(encoding='utf-8'))
    fps = int(brief['animations'].get('fps', 24))
    brief_clips = brief['animations']['clips']
    checks, warnings = [], []
    result = {'stage': 'animate', 'blender': bpy.app.version_string, 'source': str(src),
              'fps': fps, 'checks': checks, 'warnings': warnings, 'status': 'FAIL'}
    try:
        _animate_body(out, src, brief, fps, brief_clips, result, checks, warnings)
    except Exception:
        result['error'] = traceback.format_exc()
        check(checks, 'no-exception', False, result['error'].splitlines()[-1])
        raise
    finally:
        result['status'] = 'PASS' if checks and all(c['pass'] for c in checks) else 'FAIL'
        write_json(out / 'anim-result.json', result)


def _animate_body(out, src, brief, fps, brief_clips, result, checks, warnings):
    if not bpy.app.version_string.startswith('5.'):
        warnings.append('Blender %s != 5.x' % bpy.app.version_string)
    bpy.ops.wm.open_mainfile(filepath=str(src), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    scene.render.fps = fps
    scene.render.fps_base = 1.0
    result['source_sha256'] = sha256_file(src)

    meshes = [o for o in scene.objects if o.type == 'MESH']
    animated = [o for o in meshes if 'anim_clip' in o.keys()]
    result['mesh_objects_before'] = len(meshes)
    result['animated_objects'] = len(animated)

    # ---- metadatos -----------------------------------------------------
    infos = []
    for o in animated:
        raw = idprop_to_py(o.get('anim_params', {}))
        infos.append({'obj': o, 'clip': str(o['anim_clip']), 'kind': str(o['anim_kind']),
                      'pivot': [float(x) for x in o['anim_pivot']],
                      'axis': str(o.get('anim_axis', 'Z')).upper(), 'params': raw,
                      'part_id': o.get('part_id')})
    by_clip = {}
    for info in infos:
        by_clip.setdefault(info['clip'], []).append(info)
    check(checks, 'brief-clips-present', all(c in by_clip for c in brief_clips),
          {c: len(by_clip.get(c, [])) for c in brief_clips})
    check(checks, 'no-unknown-clips', all(c in brief_clips for c in by_clip),
          sorted(c for c in by_clip if c not in brief_clips))
    for clip, group in by_clip.items():
        allowed = set(brief_clips.get(clip, {}).get('parts', []))
        stray = sorted({str(i['part_id']) for i in group if allowed and i['part_id'] not in allowed})
        if stray:
            warnings.append('clip %s incluye part_id fuera del brief: %s' % (clip, stray))

    # ---- re-pivotado ----------------------------------------------------
    repivots = [repivot(i['obj'], i['pivot']) for i in animated_iter(infos)]
    result['repivot'] = repivots
    check(checks, 'repivot-bbox-unchanged', all(r['pass'] for r in repivots) and bool(repivots),
          {'objects': len(repivots), 'max_error_m': max([r['max_error_m'] for r in repivots] or [0.0]),
           'tolerance_m': BBOX_TOL,
           'not_repivoted': [r['object'] for r in repivots if r['status'] == 'skipped_not_identity']})

    # ---- muestreo + NLA -------------------------------------------------
    cache = {}
    clips_report = {}
    for clip, group in by_clip.items():
        # duración común D = period máximo; cada objeto repite k ciclos dentro de D
        for info in group:
            info['norm'], _ = normalize_params(info['kind'], info['params'])
            info['req'] = info['norm']['period']
        D = max(i['req'] for i in group)
        hinge_clip = any(i['kind'] == 'hinge' for i in group)
        n_clip = max(2, int(round(D * fps)))
        if abs(D * fps - round(D * fps)) > 1e-6:
            warnings.append('%s: D*fps=%.4f no entero; redondeo a %d frames' % (clip, D * fps, n_clip))
        kinds, pivots, params_sets, nframes = set(), set(), set(), set()
        rep = {'objects': [], 'kind': None, 'frames': n_clip, 'duration_s': n_clip / fps,
               'common_duration_s': D}
        loop_errors, rot_steps, hinge_errors = [], [], []
        for info in group:
            k = 1 if info['kind'] == 'hinge' else max(1, int(round(D / info['req'])))
            eff = D / k
            key = json.dumps([info['kind'], info['axis'], info['pivot'], info['params'], fps, n_clip, k],
                             sort_keys=True)
            if key not in cache:
                cache[key] = build_samples(info['kind'], info['params'], info['axis'], info['pivot'], fps,
                                           n_frames=n_clip, cycles=k)
            smp = cache[key]
            if abs(eff - info['req']) / info['req'] > 0.15:
                warnings.append('%s/%s: period %.4f -> efectivo %.4f (k=%d, D=%.4f), cambio > 15 %%' % (
                    clip, info['obj'].name, info['req'], eff, k, D))
            kinds.add(info['kind'])
            nframes.add(smp['frames'][-1])
            pivots.add(tuple(info['pivot']))
            params_sets.add(json.dumps(info['params'], sort_keys=True))
            loop_errors.append(smp['loop_error'])
            hinge_errors.append(smp['hinge_error'])
            rot_steps.append(smp['max_rot_step_rad_per_frame'])
            rec = author_nla(info['obj'], clip, smp, tuple(info['pivot']), fps)
            rec.update({'part_id': info['part_id'], 'kind': info['kind'], 'period_requested': info['req'],
                        'period_effective': eff, 'cycles': k,
                        'period_change_pct': round(100.0 * (eff - info['req']) / info['req'], 3),
                        'key_step': smp['step']})
            rep['objects'].append(rec)
            rep['kind'] = info['kind'] if len(kinds) == 1 else 'mixed'
            rep['path_length_m'] = smp['path_length']
            for w in smp['warnings']:
                if w not in warnings:
                    warnings.append('%s: %s' % (clip, w))
        periods = nframes
        rep['loop_error_max'] = max(loop_errors)
        rep['max_rot_step_deg_per_frame'] = math.degrees(max(rot_steps))
        rep['consistent'] = {'kinds': sorted(kinds), 'periods_frames': sorted(periods),
                             'pivots': len(pivots), 'param_sets': len(params_sets)}
        clips_report[clip] = rep
        check(checks, 'clip-consistent:' + clip, len(periods) == 1 and next(iter(periods)) == n_clip, rep['consistent'])
        if hinge_clip:
            rep['hingeMode'] = 'open-only'
            rep['hinge_error_max'] = max([e for e in hinge_errors if e is not None] or [0.0])
            check(checks, 'hinge-open-only:' + clip, rep['hinge_error_max'] <= LOOP_TOL and len(group) > 0,
                  'primer frame cerrado, ultimo abierto; sin bucle: %r' % rep['hinge_error_max'])
        else:
            check(checks, 'loop-closed:' + clip, rep['loop_error_max'] <= LOOP_TOL, rep['loop_error_max'])
        check(checks, 'rotation-step-ok:' + clip, rep['max_rot_step_deg_per_frame'] < 160.0,
              rep['max_rot_step_deg_per_frame'])
    result['clips'] = clips_report
    result['hingeMode'] = 'open-only'
    result['hingeClips'] = sorted(c for c, r in clips_report.items() if r.get('hingeMode'))
    result['clip_objects'] = {c: [r['object'] for r in rep['objects']] for c, rep in clips_report.items()}

    check(checks, 'no-active-actions', all(o.animation_data is None or o.animation_data.action is None
                                           for o in animated), None)
    check(checks, 'nla-track-names', all(
        [t.name for t in o.animation_data.nla_tracks] == [o['anim_clip']] for o in animated), None)

    max_n = max([r['frames'] for r in clips_report.values()] or [1])
    scene.frame_start = 0
    scene.frame_end = max_n
    scene.frame_set(0)

    # ---- guardado ---------------------------------------------------------
    blend_path = out / 'animated.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    result['animated_blend_sha256'] = sha256_file(blend_path)

    # ---- exportación --------------------------------------------------------
    glb_path = out / 'animated.glb'
    notes = []
    applied, dropped, valid = export_glb(glb_path, notes)
    result['exporter'] = {'applied': applied, 'dropped': dropped, 'notes': notes,
                          'available_option_count': len(valid)}
    check(checks, 'exporter-nla-mode', applied.get('export_animation_mode') == 'NLA_TRACKS', applied.get('export_animation_mode'))
    check(checks, 'glb-written', glb_path.is_file() and glb_path.stat().st_size > 0, None)
    result['animated_glb_sha256'] = sha256_file(glb_path)
    result['glb_bytes'] = glb_path.stat().st_size

    doc = read_glb_json(glb_path)
    summary = glb_animation_summary(doc, fps)
    result['glb_animations'] = summary
    result['glb_has_cameras'] = bool(doc.get('cameras'))
    result['glb_has_lights'] = bool(doc.get('extensions', {}).get('KHR_lights_punctual'))
    check(checks, 'glb-no-cameras-lights', not result['glb_has_cameras'] and not result['glb_has_lights'], None)
    for clip, rep in clips_report.items():
        entry = summary.get(clip)
        ok = bool(entry and entry['nodes'])
        check(checks, 'glb-animation:' + clip, ok, entry)
        if entry:
            expected = rep['duration_s']
            check(checks, 'glb-duration:' + clip, abs(entry['duration_s'] - expected) <= 1.5 / fps,
                  {'glb_s': entry['duration_s'], 'expected_s': expected})
            check(checks, 'glb-objects:' + clip, len(entry['nodes']) >= len(rep['objects']),
                  {'glb_nodes': len(entry['nodes']), 'objects': len(rep['objects'])})
    extra = sorted(set(summary) - set(clips_report))
    if extra:
        warnings.append('animaciones GLB extra: %s' % extra)

    tris, parts = mesh_stats([o for o in scene.objects if o.type == 'MESH'])
    result['meshes'] = len([o for o in scene.objects if o.type == 'MESH'])
    result['triangles'] = tris
    result['part_id_counts'] = parts
    check(checks, 'part-ids-present', 'None' not in parts, parts)

    # ---- renders --------------------------------------------------------------
    renders = {}
    if scene.camera is None:
        check(checks, 'render-camera', False, 'la escena no tiene cámara')
    else:
        (out / 'renders').mkdir(exist_ok=True)
        scene.render.resolution_x = scene.render.resolution_y = 768
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        for t in RENDER_TIMES:
            frame = int(round(t * fps))
            scene.frame_set(frame)
            path = out / 'renders' / ('anim-%d.png' % frame)
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            renders['anim-%d.png' % frame] = {'t_s': t, 'frame': frame,
                                              'sha256': sha256_file(path) if path.is_file() else None}
        check(checks, 'renders-written', all(r['sha256'] for r in renders.values()) and len(renders) == len(RENDER_TIMES),
              sorted(renders))
        result['render'] = {'engine': scene.render.engine, 'resolution': [768, 768]}
    result['renders'] = renders


def animated_iter(infos):
    return infos


# ======================================================================
# Etapa verify
# ======================================================================
def stage_verify(glb, brief_path, outdir):
    out = Path(outdir)
    brief = json.loads(Path(brief_path).read_text(encoding='utf-8'))
    fps = int(brief['animations'].get('fps', 24))
    clips = list(brief['animations']['clips'])
    checks, warnings = [], []
    result = {'stage': 'verify', 'blender': bpy.app.version_string, 'glb': str(glb),
              'glb_sha256': sha256_file(glb), 'checks': checks, 'warnings': warnings, 'status': 'FAIL'}
    try:
        expected = json.loads((out / 'anim-result.json').read_text(encoding='utf-8'))
        summary = glb_animation_summary(read_glb_json(glb), fps)
        result['glb_animations'] = summary
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(glb))
        names = set()
        per_object = {}
        for o in bpy.data.objects:
            ad = o.animation_data
            if ad is None:
                continue
            found = set()
            if ad.action:
                found.add(ad.action.name)
            for t in ad.nla_tracks:
                found.add(t.name)
                for s in t.strips:
                    found.add(s.name)
                    if s.action:
                        found.add(s.action.name)
            per_object[o.name] = sorted(found)
            names |= found
        names |= {a.name for a in bpy.data.actions}
        result['imported_animation_names'] = sorted(names)
        for clip in clips:
            hit = [n for n in names if clip in n]
            objs = sorted(n for n, f in per_object.items() if any(clip in x for x in f))
            entry = summary.get(clip)
            check(checks, 'imported-name:' + clip, bool(hit), hit[:6])
            check(checks, 'animates-objects:' + clip, len(objs) >= 1 or bool(entry and entry['nodes']),
                  {'imported_objects': objs[:12], 'imported_count': len(objs),
                   'glb_nodes': len(entry['nodes']) if entry else 0})
            if entry and 'clips' in expected and clip in expected['clips']:
                check(checks, 'duration:' + clip,
                      abs(entry['duration_s'] - expected['clips'][clip]['duration_s']) <= 1.5 / fps,
                      {'glb_s': entry['duration_s'], 'expected_s': expected['clips'][clip]['duration_s']})
        meshes = [o for o in bpy.data.objects if o.type == 'MESH']
        tris, parts = mesh_stats(meshes)
        result.update({'meshes': len(meshes), 'triangles': tris, 'part_id_counts': parts})
        missing = [o.name for o in meshes if 'part_id' not in o.keys() and 'part_id' not in o.data.keys()]
        check(checks, 'part-id-preserved', not missing, missing[:10])
        check(checks, 'part-id-counts-match', parts == expected.get('part_id_counts'),
              {'imported': parts, 'expected': expected.get('part_id_counts')})
        check(checks, 'mesh-count', len(meshes) == expected.get('meshes'),
              {'imported': len(meshes), 'expected': expected.get('meshes')})
        check(checks, 'triangle-count', tris == expected.get('triangles'),
              {'imported': tris, 'expected': expected.get('triangles')})
    except Exception:
        result['error'] = traceback.format_exc()
        check(checks, 'no-exception', False, result['error'].splitlines()[-1])
        raise
    finally:
        result['status'] = 'PASS' if checks and all(c['pass'] for c in checks) else 'FAIL'
        write_json(out / 'verify-result.json', result)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    if not argv:
        raise SystemExit('uso: animate SOURCE BRIEF OUTDIR | verify GLB BRIEF OUTDIR | selftest')
    stage = argv[0]
    if stage == 'selftest':
        return selftest()
    if bpy is None:
        raise SystemExit('bpy no disponible: ejecuta con Blender')
    if len(argv) != 4:
        raise SystemExit('se esperan 3 rutas absolutas')
    paths = [str(Path(a).resolve()) for a in argv[1:]]
    if stage == 'animate':
        stage_animate(*paths)
    elif stage == 'verify':
        stage_verify(*paths)
    else:
        raise SystemExit('etapa desconocida: ' + stage)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(1)
