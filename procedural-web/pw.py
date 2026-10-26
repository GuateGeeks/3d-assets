#!/usr/bin/env python3
"""Blender bridge for the procedural web characters of the cotizador (Three.js, rigid 12-bone rig).

    python3 procedural-web/pw.py doctor
    python3 procedural-web/pw.py export --model nino            # -> .local/runs/<run>/nino.blend
    python3 procedural-web/pw.py import --model nino --blend <file.blend> [--apply]

`export` turns a cotizador data module (asesor/lab/paper/meshy/primaria-meshy*-data.js) and the
pose vocabulary (asesor/lab/campus-people.js, sampled by node/sample_poses.mjs) into a .blend:
armature, one object per part and variant, one material per colour class, one action per clip.
`import` reads the retouched .blend back. Without --apply it only reports what changed; with
--apply it writes the model module (provenance in SOURCE.edited) and the clips that differ from
the pose functions (asesor/lab/paper/pose-clips-data.js). Every run keeps its files and a receipt
under procedural-web/.local/runs. Stdlib only; tools come from flags, environment or
procedural-web/.local/config.json (see config.example.json).
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCAL = HERE / '.local'
PALETTE = {'skin': '#E5AD80', 'hair': '#3A2E5C', 'vest': '#6942A1', 'shirt': '#FBFAF7', 'pants': '#33438A', 'shoe': '#2B2340', 'bag': '#19BCCD', 'dark': '#321853'}
MODULES = 'asesor/lab/paper/meshy'
CLIPS_MODULE = 'asesor/lab/paper/pose-clips-data.js'
EXPORT = re.compile(r'^export const (\w+) = Object\.freeze\((.*)\);$')


# ---------------------------------------------------------------- configuration and tools
def config():
    file = LOCAL / 'config.json'
    return json.loads(file.read_text(encoding='utf-8')) if file.exists() else {}


def setting(args, name, env, default=None):
    return getattr(args, name, None) or os.environ.get(env) or config().get(name) or default


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def windows_path(path):
    return subprocess.check_output(['wslpath', '-w', str(path)], text=True).strip()


def blender_command(args, script, files):
    """A Windows blender.exe called from WSL gets Windows paths; a Python with `bpy` runs the script directly."""
    engine = args.engine or ('blender' if setting(args, 'blender', 'GG_BLENDER') else 'bpy')
    if engine == 'bpy':
        python = setting(args, 'bpy', 'GG_BPY')
        if not python:
            raise SystemExit('Sin Blender: configura "blender" (ejecutable) o "bpy" (Python con el módulo bpy).')
        return [python, str(script), '--', *map(str, files)], engine
    exe = setting(args, 'blender', 'GG_BLENDER')
    win = exe.lower().endswith('.exe') and exe.startswith('/mnt/')
    conv = (lambda p: p if p == '-' else windows_path(p)) if win else str
    return [exe, '--background', '--factory-startup', '--python', conv(str(script)), '--', *[conv(str(f)) for f in files]], engine


def run(cmd, log):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    log.write_text(proc.stdout + '\n--- stderr ---\n' + proc.stderr, encoding='utf-8')
    if proc.returncode:
        raise SystemExit(f'Falló {Path(cmd[0]).name} (código {proc.returncode}); ver {log}')
    lines = [line for line in proc.stdout.splitlines() if line.startswith('{')]
    return json.loads(lines[-1]) if lines else {}


def new_run(kind, model):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = LOCAL / 'runs' / f'{stamp}-{kind}-{model}'
    path.mkdir(parents=True)
    return path


# ---------------------------------------------------------------- cotizador data modules
def cotizador_root(args):
    root = setting(args, 'cotizador', 'GG_COTIZADOR')
    if not root or not (Path(root) / 'asesor/lab/campus-people.js').exists():
        raise SystemExit('Indica el cotizador con --cotizador, GG_COTIZADOR o "cotizador" en .local/config.json')
    return Path(root)


def read_module(path):
    data = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        match = EXPORT.match(line)
        if match:
            data[match[1]] = json.loads(match[2])
    return data


def js(value):
    """JSON as JavaScript's JSON.stringify writes it (integral floats without '.0')."""
    def clean(v):
        if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
            return int(v)
        if isinstance(v, list):
            return [clean(x) for x in v]
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items()}
        return v
    return json.dumps(clean(value), ensure_ascii=False, separators=(',', ':'))


def write_module(path, header, exports):
    lines = [header] + [f'export const {name} = Object.freeze({js(value)});' for name, value in exports.items()]
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def models(root):
    found = {}
    for file in sorted((root / MODULES).glob('primaria-meshy*-data.js')):
        data = read_module(file)
        found[data['SOURCE'].get('model', 'nino')] = (file, data)
    return found


def person_height(root, level='prim'):
    match = re.search(rf'person: \{{[^}}]*\b{level}: ([\d.]+)', (root / 'asesor/lab/paper/kit.js').read_text(encoding='utf-8'))
    return float(match[1]) if match else .78


def sample_clips(args, root, out, mode):
    node = setting(args, 'node', 'GG_NODE', 'node')
    return run([node, str(HERE / 'node/sample_poses.mjs'), str(root), str(HERE / 'poses.json'), str(out), mode], out.with_suffix('.log'))


# ---------------------------------------------------------------- commands
def doctor(args):
    report = {'python': sys.version.split()[0]}
    exe = setting(args, 'blender', 'GG_BLENDER')
    if exe:
        try:
            out = subprocess.run([exe, '--version'], capture_output=True, text=True, timeout=120).stdout
            report['blender'] = {'path': exe, 'version': out.splitlines()[0] if out else None}
        except (OSError, subprocess.TimeoutExpired) as error:
            report['blender'] = {'path': exe, 'error': str(error)}
    python = setting(args, 'bpy', 'GG_BPY')
    if python:
        proc = subprocess.run([python, '-c', 'import bpy; print(bpy.app.version_string)'], capture_output=True, text=True, timeout=300)
        report['bpy'] = {'python': python, 'version': proc.stdout.strip().splitlines()[-1] if proc.returncode == 0 else None, 'error': proc.stderr[-300:] if proc.returncode else None}
    node = setting(args, 'node', 'GG_NODE', 'node')
    report['node'] = {'path': node, 'version': (subprocess.run([node, '--version'], capture_output=True, text=True).stdout.strip() if shutil.which(node) or Path(node).exists() else None)}
    try:
        root = cotizador_root(args)
        report['cotizador'] = {'path': str(root), 'models': {k: str(v[0].relative_to(root)) for k, v in models(root).items()}, 'clips': (root / CLIPS_MODULE).exists()}
    except SystemExit as error:
        report['cotizador'] = {'error': str(error)}
    report['status'] = 'passed' if (report.get('blender', {}).get('version') or report.get('bpy', {}).get('version')) and report['node']['version'] and 'models' in report['cotizador'] else 'failed'
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


def export(args):
    root = cotizador_root(args)
    found = models(root)
    if args.model not in found:
        raise SystemExit(f'Modelo {args.model} no existe; hay {sorted(found)}')
    file, data = found[args.model]
    out = new_run('export', args.model)
    model = {'model': args.model, 'module': str(file.relative_to(root)), 'H': person_height(root), 'classes': data['CLASSES'],
             'palette': {k: PALETTE.get(k, '#FF00FF') for k in data['CLASSES']}, 'rig': data['RIG_H'], 'landmarks': data['LANDMARKS_H'],
             'source': data['SOURCE'], 'variants': data['VARIANTS']}
    (out / 'model.json').write_text(json.dumps(model), encoding='utf-8')
    clips = '-'
    if not args.no_clips:
        sample_clips(args, root, out / 'clips.json', 'current')
        clips = out / 'clips.json'
    blend = out / f'{args.model}.blend'
    cmd, engine = blender_command(args, HERE / 'blender/build_blend.py', [out / 'model.json', clips, blend])
    result = run(cmd, out / 'blender.log')
    receipt = {'command': 'export', 'model': args.model, 'cotizador': str(root), 'module': model['module'], 'moduleSha256': sha256(file), 'engine': engine,
               'blender': result.get('blender'), 'blend': blend.name, 'blendSha256': sha256(blend), 'parts': result.get('parts'), 'actions': result.get('actions')}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps({**receipt, 'open': windows_path(blend) if shutil.which('wslpath') else str(blend)}, indent=2, ensure_ascii=False))
    return 0


def landmarks_from(old, rig, variants, gap):
    """Rig-derived landmarks follow the edited rig; face and silhouette ones are measured again."""
    L = dict(old)
    at = {k: b['at'] for k, b in rig.items()}
    L.update(hip=at['hips'][1], knee=at['shinL'][1], elbow=at['foreL'][1], shoulder=at['armL'][1], neckBase=at['head'][1], shoulderX=at['armL'][0], legX=at['legL'][0])
    parts = variants['bag']['parts']
    verts = [v for p in parts for v in p['vertices']]
    L['top'] = round(max(v[1] for v in verts), 4)
    eyes = [p for p in parts if p['id'].startswith('eye')]
    if eyes:
        L['eyeY'] = round(sum(sum(v[1] for v in p['vertices']) / len(p['vertices']) for p in eyes) / len(eyes), 4)
        L['faceZ'] = round(max(v[2] for p in eyes for v in p['vertices']) - gap, 4)
    head = next((p for p in parts if p['id'] == 'head'), None)
    if head:
        L['halfHead'] = round(max(abs(v[0]) for v in head['vertices'] if abs(v[1] - L['eyeY']) < .03), 4)
    torso = [abs(v[0]) for p in parts if p['bone'] == 'torso' for v in p['vertices'] if .5 < v[1] < .62]
    if torso:
        L['halfShoulders'] = round(max(torso), 4)
    return L


def close(a, b, tol=2e-4):
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    return a == b


def do_import(args):
    root = cotizador_root(args)
    found = models(root)
    if args.model not in found:
        raise SystemExit(f'Modelo {args.model} no existe; hay {sorted(found)}')
    file, data = found[args.model]
    blend = Path(args.blend).resolve()
    out = new_run('import', args.model)
    cmd, engine = blender_command(args, HERE / 'blender/read_blend.py', [blend, out / 'read.json'])
    run(cmd, out / 'blender.log')
    read = json.loads((out / 'read.json').read_text(encoding='utf-8'))
    if read['model'] != args.model:
        raise SystemExit(f"El .blend es del modelo {read['model']}, no de {args.model}")
    if read['errors']:
        raise SystemExit('El .blend no se puede importar:\n- ' + '\n- '.join(read['errors']))
    classes = data['CLASSES']
    # ---- model: parts in the order of the module, new parts after; classes back to indices
    variants, changes = {}, []
    for name, current in data['VARIANTS'].items():
        edited = {p['id']: p for p in read['variants'].get(name, {}).get('parts', [])}
        order = [p['id'] for p in current['parts'] if p['id'] in edited] + sorted(set(edited) - {p['id'] for p in current['parts']})
        parts = []
        for pid in order:
            p = edited[pid]
            unknown = sorted(set(p['classes']) - set(classes))
            if unknown:
                raise SystemExit(f"{name}.{pid}: clases desconocidas {unknown}; usa los materiales gg.<clase>")
            parts.append({'id': pid, 'bone': p['bone'], 'vertices': p['vertices'], 'faces': p['faces'], 'classes': [classes.index(c) for c in p['classes']], **({'vertexBones': p['vertexBones']} if 'vertexBones' in p else {})})
        old = {p['id']: p for p in current['parts']}
        for p in parts:
            o = old.get(p['id'])
            if not o or o['bone'] != p['bone'] or o['faces'] != p['faces'] or o['classes'] != p['classes'] or o.get('vertexBones') != p.get('vertexBones') or not close(o['vertices'], p['vertices']):
                changes.append(f"{name}.{p['id']}: {len(o['faces']) if o else 0} → {len(p['faces'])} triángulos")
        for pid in set(old) - set(edited):
            changes.append(f'{name}.{pid}: eliminada')
        meta = {k: v for k, v in current.items() if k != 'parts'}
        variants[name] = {**meta, 'parts': parts}
    rig = {k: {'parent': data['RIG_H'][k]['parent'], 'at': read['rig'][k]['at']} for k in data['RIG_H']}
    rig_changed = [k for k in rig if not close(rig[k]['at'], data['RIG_H'][k]['at'])]
    changes += [f'pivote {k}' for k in rig_changed]
    # ---- clips: those that differ from the pose functions
    sample_clips(args, root, out / 'original.json', 'original')
    original = json.loads((out / 'original.json').read_text(encoding='utf-8'))['clips']
    clips, clip_changes = {}, []
    for key, clip in read['clips'].items():
        ref = original.get(key)
        same = ref and len(ref['frames']) == len(clip['frames']) and all(close([f[k] for k in sorted(f)], [g[k] for k in sorted(g)], 2e-4) for f, g in zip(ref['frames'], clip['frames']))
        if not same:
            clips.setdefault(clip['name'], []).append(clip)
            clip_changes.append(key)
    current_clips = read_module(root / CLIPS_MODULE).get('CLIPS', {}) if (root / CLIPS_MODULE).exists() else {}
    receipt = {'command': 'import', 'model': args.model, 'cotizador': str(root), 'blend': str(blend), 'blendSha256': sha256(blend), 'engine': engine, 'blender': read['blender'],
               'modelChanges': changes, 'clipChanges': clip_changes, 'applied': bool(args.apply)}
    if args.apply:
        now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        if changes:
            source = {**data['SOURCE'], 'edited': {'tool': '3d-assets/procedural-web pw.py', 'blend': blend.name, 'sha256': receipt['blendSha256'], 'date': now, 'blender': read['blender']}}
            landmarks = landmarks_from(data['LANDMARKS_H'], rig, variants, data['SOURCE'].get('decalGap', .0075))
            write_module(file, f"// Retocado en Blender con 3d-assets/procedural-web sobre {data['SOURCE']['file']}. No editar a mano.",
                         {'SOURCE': source, 'CLASSES': classes, 'RIG_H': rig, 'LANDMARKS_H': landmarks, 'VARIANTS': variants})
            receipt['moduleSha256'] = sha256(file)
        if clip_changes or (current_clips and not clips):
            write_module(root / CLIPS_MODULE, '// Generado por 3d-assets/procedural-web (pw.py import) desde las acciones editadas en Blender. No editar.',
                         {'SOURCE': {'blend': blend.name, 'sha256': receipt['blendSha256'], 'date': now, 'clips': sorted(clip_changes)} if clips else None, 'CLIPS': clips})
            receipt['clipsSha256'] = sha256(root / CLIPS_MODULE)
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    if args.apply and (changes or clip_changes):
        print('\nSiguiente: en el cotizador, npm run build && npm run build:inspector && npm test (y check:people, check:paper).', file=sys.stderr)
    return 0


# ---------------------------------------------------------------- adopt a rigged character
# Colour prototypes per class (texture sRGB); several per class: models paint them in different shades
PROTO = {'skin': [(250, 190, 110), (240, 165, 60)], 'hair': [(64, 36, 96), (45, 8, 50)], 'vest': [(92, 16, 205), (45, 10, 125)], 'shirt': [(245, 250, 250)],
         'pants': [(32, 52, 128), (8, 22, 85)], 'bag': [(10, 210, 250), (10, 170, 210)], 'dark': [(20, 20, 40)]}
RIG_PARENTS = {'hips': 'root', 'torso': 'hips', 'head': 'torso', 'armL': 'torso', 'armR': 'torso', 'foreL': 'armL', 'foreR': 'armR', 'legL': 'hips', 'legR': 'hips', 'shinL': 'legL', 'shinR': 'legR'}
RIG_JOINTS = {'hips': 'mixamorig:Hips', 'torso': 'mixamorig:Spine', 'head': 'mixamorig:Neck', 'armL': 'mixamorig:LeftArm', 'armR': 'mixamorig:RightArm', 'foreL': 'mixamorig:LeftForeArm',
              'foreR': 'mixamorig:RightForeArm', 'legL': 'mixamorig:LeftUpLeg', 'legR': 'mixamorig:RightUpLeg', 'shinL': 'mixamorig:LeftLeg', 'shinR': 'mixamorig:RightLeg'}
DECAL_GAP, R4 = .0075, (lambda v: round(v, 4))


def sub3(a, b): return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def cross3(u, w): return [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]


def classify(rgb):
    dist = lambda p: (rgb[0] - p[0]) ** 2 * .3 + (rgb[1] - p[1]) ** 2 * .59 + (rgb[2] - p[2]) ** 2 * .11
    return min(PROTO, key=lambda k: min(dist(p) for p in PROTO[k]))


def ink_blobs(points, chin):
    """The painted eyes and smile: ink points of the face, grouped on a 0.004 H grid; the three biggest."""
    cells = {}
    for p in points:
        if chin < p[1] < .82 and abs(p[0]) < .1 and p[2] > .05:
            cells.setdefault((int(p[0] // .004), int(p[1] // .004)), []).append(p)
    seen, blobs = set(), []
    for start in cells:
        if start in seen:
            continue
        stack, b = [start], {'n': 0, 'x0': 9, 'x1': -9, 'y0': 9, 'y1': -9}
        seen.add(start)
        while stack:
            i, j = stack.pop()
            for p in cells[(i, j)]:
                b['n'] += 1; b['x0'] = min(b['x0'], p[0]); b['x1'] = max(b['x1'], p[0]); b['y0'] = min(b['y0'], p[1]); b['y1'] = max(b['y1'], p[1])
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    k = (i + di, j + dj)
                    if k in cells and k not in seen:
                        seen.add(k); stack.append(k)
        blobs.append(b)
    big = sorted(sorted(blobs, key=lambda b: -b['n'])[:3], key=lambda b: -b['y0'])
    if len(big) != 3:
        raise SystemExit(f'Se esperaban dos ojos y una sonrisa pintados en la cara; hay {len(big)} manchas')
    return big


def surface_at(verts, faces, px, py):
    """Front surface under (px, py): point z and the unit normal of its facet (the nearest front facet past the outline)."""
    best, near = None, None
    for f in faces:
        A, B, C = (verts[i] for i in f)
        n = cross3(sub3(B, A), sub3(C, A)); ln = sum(x * x for x in n) ** .5
        if n[2] <= 1e-12:
            continue
        d = (B[0] - A[0]) * (C[1] - A[1]) - (C[0] - A[0]) * (B[1] - A[1])
        u = ((px - A[0]) * (C[1] - A[1]) - (C[0] - A[0]) * (py - A[1])) / d
        v = ((B[0] - A[0]) * (py - A[1]) - (px - A[0]) * (B[1] - A[1])) / d
        nz = [x / ln for x in n]
        if u >= -1e-6 and v >= -1e-6 and u + v <= 1 + 1e-6:
            z = A[2] + u * (B[2] - A[2]) + v * (C[2] - A[2])
            if not best or z > best[0]:
                best = (z, nz)
        elif nz[2] > .5:
            d2 = ((A[0] + B[0] + C[0]) / 3 - px) ** 2 + ((A[1] + B[1] + C[1]) / 3 - py) ** 2
            if not near or d2 < near[0]:
                near = (d2, A[2] - (n[0] * (px - A[0]) + n[1] * (py - A[1])) / n[2], nz)
    return best or (near[1], near[2])


def separate_layers(V, F, classes, gap=.006):
    """Faces of different colour (or the same cloth back to back) lying parallel and closer than `gap` (H) along their normal (a sock over
    the leg, a strap on the vest) would flicker: the smaller face moves away from the other. Vertices
    move, triangles stay. Returns how many faces moved."""
    geo = []
    for f in F:
        A, B, C = (V[i] for i in f)
        n = cross3(sub3(B, A), sub3(C, A)); area = sum(x * x for x in n) ** .5
        geo.append((n, area))
    moved = 0
    for _ in range(6):
        changed = 0
        for i in range(len(F)):
            for k in range(i + 1, len(F)):
                if set(F[i]) & set(F[k]):
                    continue
                (na, aa), (nb, ab) = geo[i], geo[k]
                if not aa or not ab:
                    continue
                ua, ub = [x / aa for x in na], [x / ab for x in nb]
                dn = sum(x * y for x, y in zip(ua, ub))
                if abs(dn) < .98 or (classes[i] == classes[k] and dn > 0):  # same cloth back to back (a thin strap) also gets the gap
                    continue
                Pa, Pb = [V[j] for j in F[i]], [V[j] for j in F[k]]
                if any(max(p[j] for p in Pa) < min(p[j] for p in Pb) - gap or max(p[j] for p in Pb) < min(p[j] for p in Pa) - gap for j in range(3)):
                    continue
                ca, cb = [sum(p[j] for p in Pa) / 3 for j in range(3)], [sum(p[j] for p in Pb) / 3 for j in range(3)]
                d = abs(sum((cb[j] - ca[j]) * ua[j] for j in range(3)))
                if d >= gap:
                    continue
                m, un, cm, co = (i, ua, ca, cb) if aa <= ab else (k, ub, cb, ca)
                sgn = 1 if sum((cm[j] - co[j]) * un[j] for j in range(3)) >= 0 else -1
                for j in F[m]:
                    V[j] = [round(V[j][q] + un[q] * (gap - d + 1e-4) * sgn, 4) for q in range(3)]
                changed += 1
        moved += changed
        if not changed:
            break
    return moved


def adopt(args):
    root = cotizador_root(args)
    found = models(root)
    file = found[args.model][0] if args.model in found else root / MODULES / f'primaria-meshy-{args.model}-data.js'
    blend = Path(args.blend).resolve()
    out = new_run('adopt', args.model)
    shutil.copy2(blend, out / 'source.blend')  # the user's file is never opened in place
    cmd, engine = blender_command(args, HERE / 'blender/read_rigged.py', [out / 'source.blend', HERE / 'mixamo-map.json', out / 'rigged.json'])
    run(cmd, out / 'blender.log')
    r = json.loads((out / 'rigged.json').read_text(encoding='utf-8'))
    V, F = r['vertices'], r['faces']
    ys = [v[1] for v in V]
    y0, h = min(ys), max(ys) - min(ys)
    cx = (min(v[0] for v in V) + max(v[0] for v in V)) / 2
    legs = [v[2] for v in V if .1 < (v[1] - y0) / h < .3]
    cz = sum(legs) / len(legs)
    norm = lambda p: [(p[0] - cx) / h, (p[1] - y0) / h, (p[2] - cz) / h]
    V = [[R4(c) for c in norm(v)] for v in V]
    rig = {'root': {'parent': None, 'at': [0, 0, 0]}}
    for name, joint in RIG_JOINTS.items():
        rig[name] = {'parent': RIG_PARENTS[name], 'at': [R4(c) for c in norm(r['joints'][joint])]}
    # the campus seats people by the hips pivot: it goes to the thighs' joints (the hips bone only translates)
    rig['hips']['at'][1] = R4((rig['legL']['at'][1] + rig['legR']['at'][1]) / 2)
    # vertex bones: the heaviest of the 12; an unweighted vertex takes its neighbours' bone
    vb = [max(w, key=w.get) if w else None for w in r['weights']]
    for f in F:
        known = [vb[i] for i in f if vb[i]]
        for i in f:
            vb[i] = vb[i] or (known[0] if known else 'torso')
    # face classes from the texture, with position rules: shoes are the feet, the head holds skin, hair and ink
    # position rules: the dark feet are shoes; below the face, hair only hangs as pigtails beside the head
    ankle, chin0 = .1, .66
    classes = []
    for f, rgb in zip(F, r['colors']):
        c = classify(rgb) if rgb else 'shirt'
        x, y = (sum(V[i][k] for i in f) / 3 for k in (0, 1))
        if y < ankle and c in ('hair', 'dark', 'pants', 'vest'):
            c = 'shoe'
        elif c in ('hair', 'dark') and y < chin0 and not (abs(x) > .12 and y > .55):
            c = 'vest' if y > .4 else 'pants'
        elif c == 'dark':
            c = 'hair'
        elif c == 'pants' and y > .45:  # above the waist there is no skirt: the dark vest
            c = 'vest'
        classes.append(c)
    chin = min((sum(V[i][1] for i in f) / 3 for f, c in zip(F, classes) if c == 'skin' and all(vb[i] == 'head' for i in f) and sum(V[i][2] for i in f) > 0), default=.68)
    # the vest and the backpack follow the torso: at the armpit the sleeve stretches, not the vest
    for f, c in zip(F, classes):
        if c in ('vest', 'bag'):
            for i in f:
                if vb[i] in ('armL', 'armR'):
                    vb[i] = 'torso'
    shifted = separate_layers(V, F, classes)
    # rocker sole (as the R2 adaptation of P18): the sole rises 0.012 H toward the toe and 0.006 H toward
    # the heel, so a swinging foot stays on the floor
    for side in 'LR':
        feet = sorted({i for f, c in zip(F, classes) for i in f if c == 'shoe' and vb[i] == 'shin' + side})
        if feet:
            zh, zt = min(V[i][2] for i in feet), max(V[i][2] for i in feet)
            zc = (zh + zt) / 2
            for i in feet:
                if V[i][1] < ankle:
                    lift = .012 * (V[i][2] - zc) / (zt - zc) if V[i][2] > zc else .006 * (zc - V[i][2]) / (zc - zh)
                    V[i][1] = R4(V[i][1] + lift * (1 - V[i][1] / ankle))
    # parts: one per bone (the majority of its corners); corners on another bone keep it (a stretched seam)
    parts = {}
    for f, c in zip(F, classes):
        bones = [vb[i] for i in f]
        bone = max(bones, key=bones.count)  # ties: the first corner's bone (deterministic)
        p = parts.setdefault(bone, {'id': bone, 'bone': bone, 'vertices': [], 'faces': [], 'classes': [], 'vertexBones': [], '_map': {}})
        p['faces'].append([p['_map'].setdefault(i, (p['vertices'].append(V[i]), p['vertexBones'].append(vb[i]), len(p['vertices']) - 1)[2]) for i in f])
        p['classes'].append(c)
    for p in parts.values():
        del p['_map']
        if all(b == p['bone'] for b in p['vertexBones']):
            del p['vertexBones']
    ordered = [parts[k] for k in ['head', 'torso', 'hips', 'armL', 'armR', 'foreL', 'foreR', 'legL', 'legR', 'shinL', 'shinR'] if k in parts]
    # decals: the painted eyes and smile as flat appliqués on the face
    head = parts['head']
    e1, e2, mouth = ink_blobs([norm(p) for p in r['ink']], chin)
    def decal(pid, pts, faces):
        vs = []
        for px, py in pts:
            z, n = surface_at(head['vertices'], head['faces'], px, py)
            vs.append([R4(px + n[0] * DECAL_GAP), R4(py + n[1] * DECAL_GAP), R4(z + n[2] * DECAL_GAP)])
        return {'id': pid, 'bone': 'head', 'vertices': vs, 'faces': faces, 'classes': ['dark'] * len(faces)}
    decals = []
    for e in (e1, e2):
        cx2, cy, rx, ry = (e['x0'] + e['x1']) / 2, (e['y0'] + e['y1']) / 2, (e['x1'] - e['x0']) / 2 + .002, (e['y1'] - e['y0']) / 2 + .002
        decals.append(decal('eyeL' if cx2 > 0 else 'eyeR', [[cx2 - rx, cy], [cx2 - rx * .5, cy - ry], [cx2 + rx * .5, cy - ry], [cx2 + rx, cy], [cx2 + rx * .5, cy + ry], [cx2 - rx * .5, cy + ry]], [[0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 5]]))
    w, hh, cx2, top = (mouth['x1'] - mouth['x0']) / 2 + .002, max(.008, mouth['y1'] - mouth['y0']), (mouth['x0'] + mouth['x1']) / 2, mouth['y1'] + .002
    decals.append(decal('smile', [[cx2 - w, top], [cx2, top - hh * .38], [cx2 + w, top], [cx2 + w * .5, top - hh], [cx2 - w * .5, top - hh]], [[0, 4, 1], [1, 4, 3], [1, 3, 2]]))
    CL = ['skin', 'hair', 'vest', 'shirt', 'pants', 'shoe', 'bag', 'dark']
    variant = {'parts': [{**p, 'classes': [CL.index(c) for c in p['classes']]} for p in ordered + decals]}
    tris = sum(len(p['faces']) for p in variant['parts'])
    # kneelLift: hips height over the sole when kneeling (long shoes point their toe down)
    L = landmarks_from({'sole': 0, 'ankle': ankle, 'chin': R4(chin), 'top': 1, 'kneelLift': .095}, rig, {'bag': variant}, DECAL_GAP)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    source = {'model': args.model, 'file': str(blend), 'sha256': sha256(out / 'source.blend'), 'bytes': (out / 'source.blend').stat().st_size, 'triangles': len(F), 'vertices': len(r['vertices']),
              'texture': 'x'.join(map(str, next(iter(r['images'].values()), [0, 0]))), 'heightUnits': R4(h), 'target': len(F), 'decalGap': DECAL_GAP,
              'rig': f"{r['armature']} → 12 huesos (procedural-web/mixamo-map.json); cada vértice sigue a su hueso de más peso",
              'edited': {'tool': '3d-assets/procedural-web pw.py adopt', 'blend': blend.name, 'sha256': sha256(out / 'source.blend'), 'date': stamp, 'blender': r['blender']}}
    receipt = {'command': 'adopt', 'model': args.model, 'cotizador': str(root), 'module': str(file.relative_to(root)), 'blend': str(blend), 'blendSha256': source['sha256'], 'engine': engine,
               'blender': r['blender'], 'sourceTriangles': len(F), 'triangles': tris, 'parts': {p['id']: len(p['faces']) for p in variant['parts']},
               'layerShifts': shifted, 'seamVertices': sum(1 for p in ordered for b in p.get('vertexBones', []) if b != p['bone']), 'classes': {c: classes.count(c) for c in CL if classes.count(c)}, 'applied': bool(args.apply)}
    if args.apply:
        write_module(file, f'// Adoptado desde Blender con 3d-assets/procedural-web (pw.py adopt) sobre {blend.name}. No editar a mano.',
                     {'SOURCE': source, 'CLASSES': CL, 'RIG_H': rig, 'LANDMARKS_H': L, 'VARIANTS': {'bag': variant, 'plain': variant}})
        receipt['moduleSha256'] = sha256(file)
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--cotizador', help='raíz del cotizador (o GG_COTIZADOR)')
    parser.add_argument('--blender', help='ejecutable de Blender (o GG_BLENDER); en WSL vale un blender.exe de Windows')
    parser.add_argument('--bpy', help='Python con el módulo bpy (o GG_BPY), para pruebas sin interfaz')
    parser.add_argument('--engine', choices=['blender', 'bpy'], help='qué Blender usar (por defecto el ejecutable si está configurado)')
    parser.add_argument('--node', help='ejecutable de Node (o GG_NODE)')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor', help='comprueba Blender, Node y el cotizador')
    ex = sub.add_parser('export', help='modelo y poses del cotizador → .blend')
    ex.add_argument('--model', required=True)
    ex.add_argument('--no-clips', action='store_true', help='solo geometría y rig')
    im = sub.add_parser('import', help='.blend retocado → módulos del cotizador')
    im.add_argument('--model', required=True)
    im.add_argument('--blend', required=True)
    im.add_argument('--apply', action='store_true', help='escribe los módulos (sin esto solo informa)')
    ad = sub.add_parser('adopt', help='personaje riggeado (una malla, armature tipo Mixamo) → módulo del cotizador, conservando sus triángulos')
    ad.add_argument('--model', required=True)
    ad.add_argument('--blend', required=True)
    ad.add_argument('--apply', action='store_true', help='escribe el módulo (sin esto solo informa)')
    args = parser.parse_args(argv)
    return {'doctor': doctor, 'export': export, 'import': do_import, 'adopt': adopt}[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
