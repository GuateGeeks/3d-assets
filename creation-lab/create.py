"""Additive, stdlib-only asset creation workflow. Never imports the rigging lab."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
import uuid

HOME = Path(__file__).resolve().parent
DEFAULT_RUNS = HOME / '.local' / 'runs'
VIEWS = ('front', 'side', 'back', 'three-quarter', 'wireframe', 'reimport-three-quarter')
STATES = {'PASS', 'FAIL', 'BLOCKED', 'NOT_RUN'}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, data):
    # Exclusive creation: an existing artifact is never replaced.
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def read_json(path):
    with Path(path).open(encoding='utf-8') as stream:
        return json.load(stream)


def resolve_file(path):
    path = Path(path).expanduser()
    if path.is_symlink():
        raise ValueError('Symlink inputs are not accepted: ' + str(path))
    path = path.resolve(strict=True)
    if not path.is_file():
        raise ValueError('Expected regular file: ' + str(path))
    return path


def artifact(run, relative):
    if not isinstance(relative, str) or Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Artifact path must stay within its run')
    result = resolve_file(run / relative)
    if not result.is_relative_to(run.resolve()):
        raise ValueError('Artifact escapes its run')
    return result


def validate_brief(data):
    if not isinstance(data, dict) or data.get('schemaVersion') != 1:
        raise ValueError('brief.schemaVersion must be 1')
    if not isinstance(data.get('assetId'), str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', data['assetId']):
        raise ValueError('assetId must be a safe lowercase slug (1-64 characters)')
    if not isinstance(data.get('description'), str) or not data['description'].strip():
        raise ValueError('description is required')
    if data.get('profile', 'lowpoly-canary') != 'lowpoly-canary':
        raise ValueError('Only profile=lowpoly-canary is implemented; highdetail workflows remain planned')
    data['profile'] = 'lowpoly-canary'
    dims = data.get('dimensionsM')
    if not isinstance(dims, list) or len(dims) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 or v > 100 for v in dims):
        raise ValueError('dimensionsM must contain three finite positive meters, at most 100')
    budgets = data.get('budgets', {})
    if not isinstance(budgets, dict):
        raise ValueError('budgets must be a JSON object')
    for key, default in [('triangles', 6000), ('materials', 2), ('textureSize', 2048)]:
        value = budgets.get(key, default)
        if type(value) is not int or value <= 0 or value > default:
            raise ValueError(f'budgets.{key} must be an integer from 1 to {default}')
        budgets[key] = value
    data['budgets'] = budgets
    if data.get('units', 'm') != 'm':
        raise ValueError('Only meters (units=m) are supported')
    data['units'] = 'm'
    provider = data.get('provider', {'mode': 'manual'})
    if not isinstance(provider, dict) or provider.get('mode') not in ('manual', 'configured'):
        raise ValueError('provider.mode must be manual or configured; no provider calls are implemented')
    # Only persist non-secret configuration, never a provider API key or arbitrary headers.
    if set(provider) - {'mode', 'name', 'model', 'endpoint', 'credentialEnv'}:
        raise ValueError('Unknown provider fields; credentials must be environment variable names')
    if 'credentialEnv' in provider and not re.fullmatch(r'[A-Z_][A-Z0-9_]*', provider['credentialEnv']):
        raise ValueError('credentialEnv must be an environment variable name')
    if 'endpoint' in provider and ('@' in provider['endpoint'] or '?' in provider['endpoint']):
        raise ValueError('Provider endpoint must not embed credentials or a query')
    data['provider'] = provider
    provenance = data.get('provenance')
    if not isinstance(provenance, dict) or not all(isinstance(provenance.get(k), str) and provenance[k].strip() for k in ('author', 'origin', 'license')):
        raise ValueError('provenance requires author, origin and license')
    if type(data.get('seed', 17)) is not int:
        raise ValueError('seed must be an integer')
    data.setdefault('seed', 17)
    return data


def new_run(root, command):
    root = Path(root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex[:10]
    path = root / run_id
    path.mkdir(exist_ok=False)
    return path, {'schemaVersion': 1, 'runId': run_id, 'command': command,
                  'createdAt': datetime.now(timezone.utc).isoformat(),
                  'technical': 'NOT_RUN', 'visual': 'NOT_RUN', 'rights': 'NOT_RUN',
                  'status': 'NOT_RUN', 'artifacts': {}, 'checks': [],
                  'tool': {'scriptSha256': digest(__file__), 'python': sys.version,
                           'host': platform.platform()}}


def finish(run, manifest):
    for path in sorted(run.rglob('*')):
        if path.is_file():
            manifest['artifacts'][path.relative_to(run).as_posix()] = digest(path)
    values = [manifest[k] for k in ('technical', 'visual', 'rights')]
    manifest['status'] = ('FAIL' if 'FAIL' in values else 'PASS' if all(x == 'PASS' for x in values)
                          else 'BLOCKED' if 'BLOCKED' in values or manifest['technical'] == 'PASS' else 'NOT_RUN')
    write_json(run / 'manifest.json', manifest)
    # Completion marker is a checksum of the immutable manifest, not a mutable status.
    (run / 'COMPLETE').write_text(digest(run / 'manifest.json') + '\n', encoding='ascii')
    print(json.dumps({'run': str(run), 'technical': manifest['technical'], 'visual': manifest['visual'],
                      'rights': manifest['rights'], 'status': manifest['status']}, ensure_ascii=False))
    return 1 if manifest['technical'] == 'FAIL' or manifest['status'] == 'FAIL' else 2 if manifest['technical'] == 'BLOCKED' else 0


def load_run(value):
    run = Path(value).expanduser().resolve(strict=True)
    if not run.is_dir():
        raise ValueError('Expected a run directory')
    manifest_path = artifact(run, 'manifest.json')
    marker = artifact(run, 'COMPLETE').read_text(encoding='ascii').strip()
    if digest(manifest_path) != marker:
        raise ValueError('Run manifest hash differs from COMPLETE')
    data = read_json(manifest_path)
    if data.get('schemaVersion') != 1 or any(data.get(k) not in STATES for k in ('technical', 'visual', 'rights', 'status')):
        raise ValueError('Unsupported run manifest')
    for name, expected in data['artifacts'].items():
        if digest(artifact(run, name)) != expected:
            raise ValueError('Artifact hash mismatch: ' + name)
    return run, data


def parent_ref(run):
    return {'path': str(run), 'manifestSha256': digest(run / 'manifest.json')}


def execute(command, timeout=30):
    try:
        proc = subprocess.run(command, capture_output=True, text=True, errors='replace', timeout=timeout,
                              env={**os.environ, 'CUDA_VISIBLE_DEVICES': '', 'OMP_NUM_THREADS': '2',
                                   'OPENBLAS_NUM_THREADS': '2', 'PYTHONDONTWRITEBYTECODE': '1'})
        return {'command': command, 'returncode': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'command': command, 'returncode': None, 'stdout': '', 'stderr': str(exc)}


def backend(args):
    if args.bpy_python:
        return 'bpy-python', str(resolve_file(args.bpy_python))
    selected = args.blender or shutil.which('blender')
    if not selected and platform.system() == 'Windows':
        candidates = [Path('D:/SteamLibrary/steamapps/common/Blender/blender.exe'),
                      Path('C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe')]
        foundation = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Blender Foundation'
        if foundation.exists():
            candidates.extend(sorted(foundation.glob('Blender */blender.exe'), reverse=True))
        selected = next((path for path in candidates if path.is_file()), None)
    return ('blender', str(resolve_file(selected))) if selected else (None, None)


def backend_command(kind, exe, script, arguments):
    if kind == 'blender':
        return [exe, '--background', '--factory-startup', '--disable-autoexec', '--threads', '2',
                '--python', str(script), '--', *map(str, arguments)]
    return [exe, str(script), *map(str, arguments)]


def probe(kind, exe, script=None):
    if not kind:
        return {'status': 'BLOCKED', 'reason': 'No Blender executable detected; supply --blender or --bpy-python explicitly'}
    result = execute(backend_command(kind, exe, script or HOME / 'scripts' / 'blender_worker.py', ['probe']))
    for line in reversed(result['stdout'].splitlines()):
        if line.startswith('CREATION_BACKEND='):
            try:
                info = json.loads(line.split('=', 1)[1])
                return {**result, **info, 'kind': kind, 'executable': exe,
                        'status': 'PASS' if result['returncode'] == 0 else 'BLOCKED'}
            except ValueError:
                break
    return {**result, 'kind': kind, 'executable': exe, 'status': 'BLOCKED', 'reason': 'Backend did not return a real bpy version'}


def doctor(args):
    run, data = new_run(args.runs_root, 'doctor')
    info = probe(*backend(args))
    write_json(run / 'doctor.json', {'host': platform.platform(), 'pythonExecutable': sys.executable,
                                    'cpuOnly': True, 'backend': info})
    data['technical'] = info['status']
    data['backend'] = {key: info[key] for key in ('kind', 'executable', 'version') if key in info}
    return finish(run, data)


def brief(args):
    original = resolve_file(args.input)
    value = validate_brief(read_json(original))
    run, data = new_run(args.runs_root, 'brief')
    write_json(run / 'brief.json', value)
    data.update(technical='PASS', rights='PASS' if value['provenance']['license'] == 'CC0-1.0' and value['provenance']['origin'] == 'original' else 'BLOCKED')
    data['input'] = {'path': str(original), 'sha256': digest(original)}
    data['providerExecution'] = 'NOT_RUN'
    return finish(run, data)


def invariant_checks(before, after, label):
    """Compare persisted/exported state; budget compliance alone is insufficient."""
    checks = []
    def check(name, passed, actual):
        checks.append({'name': label + '.' + name, 'status': 'PASS' if passed else 'FAIL', 'actual': actual})
    check('triangles', before['triangles'] == after['triangles'], [before['triangles'], after['triangles']])
    check('materials', before['materialCount'] == after['materialCount'], [before['materialCount'], after['materialCount']])
    check('bounds', all(abs(a-b) < 0.0001 for a,b in zip(before['bboxMinM'] + before['bboxMaxM'], after['bboxMinM'] + after['bboxMaxM'])), [before['bboxMinM'], after['bboxMinM']])
    check('transformsApplied', before['transformsApplied'] and after['transformsApplied'], [before['transformsApplied'], after['transformsApplied']])
    check('orientationGeometry', before['geometrySignature'] == after['geometrySignature'], [before['geometrySignature'], after['geometrySignature']])
    check('orientedMaterialSurface', before['surfaceSignature'] == after['surfaceSignature'], [before['surfaceSignature'], after['surfaceSignature']])
    left, right = before['materialValues'], after['materialValues']
    appearance_equal = len(left) == len(right)
    for a, b in zip(left, right):
        appearance_equal = appearance_equal and a['name'] == b['name'] and all(abs(x-y) < 0.0001 for x,y in zip(a['baseColor'], b['baseColor'])) and abs(a['roughness']-b['roughness']) < 0.0001 and abs(a['metallic']-b['metallic']) < 0.0001
    check('materialAppearance', appearance_equal, [left, right])
    return checks


def checks_for(run, brief_value):
    metrics = read_json(artifact(run, 'metrics.json'))
    before, reopened, after = metrics['source'], metrics['reopened'], metrics['imported']
    budgets = brief_value['budgets']
    checks = []
    def check(name, passed, actual):
        checks.append({'name': name, 'status': 'PASS' if passed else 'FAIL', 'actual': actual})
    for label, m in [('source', before), ('reopened', reopened), ('imported', after)]:
        check(label + '.mesh', m['meshCount'] > 0, m['meshCount'])
        check(label + '.triangles', 0 < m['triangles'] <= budgets['triangles'], m['triangles'])
        check(label + '.materials', 0 < m['materialCount'] <= budgets['materials'], m['materialCount'])
        check(label + '.textures', m['maxTextureSize'] <= budgets['textureSize'] and not m['missingImages'], m['maxTextureSize'])
        check(label + '.finiteGeometry', m['finite'] and m['nonManifoldEdges'] == 0, {'finite': m['finite'], 'nonManifoldEdges': m['nonManifoldEdges']})
        check(label + '.dimensionsM', all(abs(a-b) <= max(0.0001, b*0.01) for a,b in zip(m['dimensionsM'], brief_value['dimensionsM'])), m['dimensionsM'])
    checks.extend(invariant_checks(before, reopened, 'reopen'))
    checks.extend(invariant_checks(before, after, 'roundtrip'))
    provenance = read_json(artifact(run, 'render-provenance.json'))
    check('render.reopenedSource', provenance['stage'] == 'reopen' and provenance['sourceBlendSha256'] == digest(artifact(run, 'source.blend')), provenance)
    for view in VIEWS:
        file = artifact(run, 'renders/' + view + '.png')
        with file.open('rb') as stream:
            signature = stream.read(24)
        check('render.' + view, signature[:8] == b'\x89PNG\r\n\x1a\n' and int.from_bytes(signature[16:20], 'big') >= 64, file.stat().st_size)
    check('source.blend', artifact(run, 'source.blend').stat().st_size > 0, True)
    with artifact(run, 'asset.glb').open('rb') as stream:
        header = stream.read(12)
    check('export.glb', header[:4] == b'glTF' and int.from_bytes(header[4:8], 'little') == 2, len(header))
    glb = artifact(run, 'asset.glb').read_bytes()
    if len(glb) < 20 or len(glb) != struct.unpack_from('<I', glb, 8)[0]:
        raise ValueError('Invalid GLB length')
    length, kind = struct.unpack_from('<II', glb, 12)
    if kind != 0x4E4F534A:
        raise ValueError('GLB JSON chunk is missing')
    gltf = json.loads(glb[20:20+length])
    resources = gltf.get('buffers', []) + gltf.get('images', [])
    check('export.selfContained', all('uri' not in item for item in resources), len(resources))
    check('export.gltfVersion', gltf.get('asset', {}).get('version') == '2.0', gltf.get('asset'))
    return checks


def canary(args):
    brief_path = resolve_file(args.brief)
    value = validate_brief(read_json(brief_path))
    run, data = new_run(args.runs_root, 'canary')
    write_json(run / 'brief.json', value)
    data['input'] = {'path': str(brief_path), 'sha256': digest(brief_path)}
    (run / 'code' / 'scripts').mkdir(parents=True)
    for original, snapshot in ((Path(__file__), run / 'code' / 'create.py'),
                               (HOME / 'scripts' / 'blender_worker.py', run / 'code' / 'scripts' / 'blender_worker.py')):
        with snapshot.open('xb') as output:
            output.write(original.read_bytes())
    worker_snapshot = run / 'code' / 'scripts' / 'blender_worker.py'
    data['rights'] = 'PASS' if value['provenance']['license'] == 'CC0-1.0' and value['provenance']['origin'] == 'original' else 'BLOCKED'
    data['visual'] = 'NOT_RUN'
    kind, exe = backend(args)
    info = probe(kind, exe, worker_snapshot)
    write_json(run / 'backend.json', info)
    data['workerSha256'] = digest(worker_snapshot)
    if info['status'] != 'PASS':
        data['technical'] = 'BLOCKED'
        return finish(run, data)
    data['backend'] = {key: info[key] for key in ('kind', 'executable', 'version')}
    results = []
    for stage in ('build', 'reopen', 'import'):
        command = backend_command(kind, exe, worker_snapshot, [stage, run])
        result = execute(command, timeout=args.timeout)
        results.append({'stage': stage, **result})
        if result['returncode'] != 0:
            write_json(run / 'execution.json', results)
            data.update(technical='FAIL', error='Blender ' + stage + ' failed; see execution.json')
            return finish(run, data)
    write_json(run / 'execution.json', results)
    write_json(run / 'metrics.json', {'source': read_json(run / 'source-metrics.json'),
                                      'reopened': read_json(run / 'reopened-metrics.json'),
                                      'imported': read_json(run / 'imported-metrics.json')})
    try:
        data['checks'] = checks_for(run, value)
        data['technical'] = 'PASS' if all(c['status'] == 'PASS' for c in data['checks']) else 'FAIL'
    except (ValueError, OSError, KeyError, TypeError) as exc:
        data.update(technical='FAIL', error=str(exc))
    return finish(run, data)


def source_run(run, data):
    # Follow only hash-bound parents; never accept a mutable pointer as evidence.
    seen = set()
    while 'metrics.json' not in data['artifacts']:
        if str(run) in seen or 'parent' not in data:
            raise ValueError('No canary source in this run lineage')
        seen.add(str(run))
        parent = data['parent']
        run, data = load_run(parent['path'])
        if digest(run / 'manifest.json') != parent['manifestSha256']:
            raise ValueError('Parent hash mismatch')
    return run, data


def derived(args):
    parent, previous = load_run(args.run)
    source, original = source_run(parent, previous)
    value = validate_brief(read_json(artifact(source, 'brief.json')))
    run, data = new_run(args.runs_root, args.command)
    data.update(technical=previous['technical'], visual=previous['visual'], rights=previous['rights'], parent=parent_ref(parent))
    data['sourceRun'] = parent_ref(source)
    data['checks'] = checks_for(source, value)
    data['technical'] = 'PASS' if all(c['status'] == 'PASS' for c in data['checks']) else 'FAIL'
    if args.command == 'review':
        expected = {view: digest(artifact(source, 'renders/' + view + '.png')) for view in VIEWS}
        evidence = {}
        for entry in args.evidence:
            key, separator, sha = entry.partition('=')
            if not separator or key in evidence:
                raise ValueError('Evidence must be unique view=sha256 pairs')
            evidence[key] = sha
        if evidence != expected:
            raise ValueError('Review must attest all six exact image hashes: ' + json.dumps(expected))
        if not args.opened_images:
            raise ValueError('Review requires --opened-images attestation after opening every image')
        data['visual'] = args.decision
        write_json(run / 'review.json', {'decision': args.decision, 'reviewer': args.reviewer,
                                        'notes': args.notes, 'openedImages': True, 'evidence': evidence,
                                        'sourceRun': parent_ref(source)})
    if args.command == 'handoff':
        metrics = read_json(artifact(source, 'metrics.json'))['source']
        candidate = {'schemaVersion': 1, 'kind': 'creation-candidate', 'assetId': value['assetId'],
                     'sourceRun': parent_ref(source), 'reviewRun': parent_ref(parent),
                     'asset': {'path': str(artifact(source, 'asset.glb')), 'sha256': original['artifacts']['asset.glb']},
                     'editable': {'path': str(artifact(source, 'source.blend')), 'sha256': original['artifacts']['source.blend']},
                     'units': 'm', 'dimensionsM': metrics['dimensionsM'],
                     'bboxM': {'min': metrics['bboxMinM'], 'max': metrics['bboxMaxM']},
                     'axes': {'blender': {'up': '+Z', 'front': '-Y'}, 'gltf': {'up': '+Y', 'front': '+Z'},
                              'conversion': 'Blender glTF exporter export_yup=True; importer restores Blender axes'},
                     'provenance': value['provenance'], 'seed': value['seed'], 'budgets': value['budgets'],
                     'tool': original['tool'], 'backend': original.get('backend'), 'workerSha256': original.get('workerSha256'),
                     'qa': {k: data[k] for k in ('technical', 'visual', 'rights')},
                     'eligibleForPromotion': all(data[k] == 'PASS' for k in ('technical', 'visual', 'rights')),
                     'catalog': {'status': 'NOT_RUN', 'action': 'Explicit adapter/review required; original index accepts models/ only'},
                     'rigging': {'status': 'NOT_RUN', 'adapter': 'lab/lab.py ingest --candidate <candidate.json>',
                                 'transformPolicy': 'Explicit normalization of longest dimension to 2 m; restore source coordinates after rigging',
                                 'reviewPolicy': 'New rig remains a candidate pending deformation review'},
                     'promotion': 'NOT_RUN'}
        write_json(run / 'candidate.json', candidate)
    report = ['# Creation run report', '', f"Technical: {data['technical']}", f"Visual: {data['visual']}", f"Rights: {data['rights']}",
              '', 'Source: ' + str(source), '', 'Visual review requires opening all five source images plus reimport comparison and recording their hashes.']
    report.extend(f"- {check['status']}: {check['name']} = {check['actual']}" for check in data['checks'])
    (run / 'report.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
    return finish(run, data)


def parser():
    top = argparse.ArgumentParser(description=__doc__)
    subs = top.add_subparsers(dest='command', required=True)
    for name in ('doctor', 'brief', 'canary', 'validate', 'report', 'review', 'handoff'):
        cmd = subs.add_parser(name)
        cmd.add_argument('--runs-root', default=str(DEFAULT_RUNS))
        if name in ('doctor', 'canary'):
            group = cmd.add_mutually_exclusive_group()
            group.add_argument('--blender')
            group.add_argument('--bpy-python')
        if name == 'brief':
            cmd.add_argument('--input', required=True)
        if name == 'canary':
            cmd.add_argument('--brief', required=True)
            cmd.add_argument('--timeout', type=int, default=300)
        if name in ('validate', 'report', 'review', 'handoff'):
            cmd.add_argument('run')
        if name == 'review':
            cmd.add_argument('--decision', choices=['PASS', 'FAIL'], required=True)
            cmd.add_argument('--reviewer', required=True)
            cmd.add_argument('--notes', required=True)
            cmd.add_argument('--opened-images', action='store_true')
            cmd.add_argument('--evidence', action='append', default=[], metavar='VIEW=SHA256')
    return top


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return {'doctor': doctor, 'brief': brief, 'canary': canary}.get(args.command, derived)(args)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('creation-lab: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
