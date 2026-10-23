"""Strict, stdlib-only bridge from reviewed creation evidence to isolated rigging.

Creation gates keep their uppercase vocabulary; rigging receipts use existing
lowercase states. No catalog, corpus pointer or gallery file is changed here.
"""
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil

VIEWS = ('front', 'side', 'back', 'three-quarter', 'wireframe', 'reimport-three-quarter')
HEX = re.compile(r'[0-9a-f]{64}')


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as output:
        json.dump(value, output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write('\n')


def relative_name(value):
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value:
        raise ValueError('Expected canonical relative artifact path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ('..', '.') for part in value.split('/')) or ':' in value:
        raise ValueError('Unsafe relative artifact path: ' + value)
    return path


def safe_path(path, boundary, directory=False):
    """Reject symlinks at every component before following any filesystem path."""
    path, boundary = Path(path).absolute(), Path(boundary).absolute()
    try:
        relative = path.relative_to(boundary)
    except ValueError as exc:
        raise ValueError('Path escapes allowed boundary: ' + str(path)) from exc
    current = boundary
    if current.is_symlink():
        raise ValueError('Symlink boundary is forbidden')
    for part in relative.parts:
        if part in ('.', '..'):
            raise ValueError('Path traversal is forbidden')
        current /= part
        if current.is_symlink():
            raise ValueError('Symlink input is forbidden: ' + str(current))
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(boundary.resolve(strict=True)):
        raise ValueError('Resolved path escapes allowed boundary')
    if (not resolved.is_dir()) if directory else (not resolved.is_file()):
        raise ValueError('Expected ' + ('directory' if directory else 'file') + ': ' + str(path))
    return resolved


def canonical_reference(value, root):
    """Map only full repository paths, including this distro's WSL UNC form.

    This is a lexical mapping. Actual references are checked against either the
    repository boundary or an explicit copied-evidence map before they are read.
    No basename search, shell invocation or fallback to a different distro.
    """
    if not isinstance(value, str) or not value or '\x00' in value:
        raise ValueError('Invalid reference path')
    root = Path(root).absolute()
    if '\\' in value:
        win = PureWindowsPath(value)
        if not win.is_absolute() or '..' in win.parts:
            raise ValueError('Invalid Windows reference path')
        drive = win.drive.replace('\\', '/').split('/')
        if len(drive) != 4 or drive[2].lower() not in ('wsl.localhost', 'wsl$'):
            # Windows native drive paths are supported only when they belong to
            # the actual Windows repository root, never remapped into Linux.
            if os.name != 'nt':
                raise ValueError('Only current-distro WSL UNC references can map into Linux')
            actual = Path(value).absolute()
        elif os.name == 'nt':
            actual = Path(value).absolute()
        else:
            expected_distro = os.environ.get('WSL_DISTRO_NAME', 'Ubuntu')
            if drive[3].casefold() != expected_distro.casefold():
                raise ValueError('Reference belongs to a different WSL distro')
            actual = Path('/').joinpath(*win.parts[1:])
    elif value.startswith('/') and os.name == 'nt' and root.drive.startswith('\\\\'):
        win_root = PureWindowsPath(str(root))
        linux_root = PurePosixPath('/').joinpath(*win_root.parts[1:])
        try:
            suffix = PurePosixPath(value).relative_to(linux_root)
        except ValueError as exc:
            raise ValueError('Linux reference does not match this WSL repository') from exc
        actual = root.joinpath(*suffix.parts)
    else:
        path = Path(value)
        if '..' in path.parts:
            raise ValueError('Reference traversal is forbidden')
        actual = path if path.is_absolute() else root / path
    try:
        relative = actual.absolute().relative_to(root)
    except ValueError as exc:
        raise ValueError('Reference is outside this repository') from exc
    return relative_name(relative.as_posix()).as_posix()


def resolver(root, copies=None):
    root = Path(root).absolute()
    def resolve(raw, directory=False):
        canonical = canonical_reference(raw, root)
        if copies is None:
            return safe_path(root / canonical, root, directory)
        matches = [key for key in copies if canonical == key or canonical.startswith(key + '/')]
        if len(matches) != 1:
            raise ValueError('Reference is not part of the copied immutable chain: ' + canonical)
        key = matches[0]
        suffix = PurePosixPath(canonical).relative_to(PurePosixPath(key))
        base = Path(copies[key])
        return safe_path(base.joinpath(*suffix.parts), base, directory)
    return resolve


def verify_creation_run(run, boundary):
    run = safe_path(run, boundary, directory=True)
    manifest = safe_path(run / 'manifest.json', run)
    complete = safe_path(run / 'COMPLETE', run).read_text(encoding='ascii').strip()
    if not HEX.fullmatch(complete) or sha256(manifest) != complete:
        raise ValueError('Creation manifest does not match its COMPLETE checksum')
    data = read_json(manifest)
    if data.get('schemaVersion') != 1 or not isinstance(data.get('artifacts'), dict):
        raise ValueError('Unsupported creation manifest')
    expected = {'manifest.json', 'COMPLETE'}
    for name, expected_hash in data['artifacts'].items():
        relative_name(name)
        if not isinstance(expected_hash, str) or not HEX.fullmatch(expected_hash):
            raise ValueError('Invalid artifact checksum')
        file = safe_path(run / name, run)
        if sha256(file) != expected_hash:
            raise ValueError('Creation artifact checksum mismatch: ' + name)
        expected.add(name)
    actual = set()
    for file in run.rglob('*'):
        if file.is_symlink():
            raise ValueError('Symlink in creation evidence')
        if file.is_file():
            actual.add(file.relative_to(run).as_posix())
    if actual != expected:
        raise ValueError('Unmanifested or missing creation evidence')
    return data


def require_gates(data, label, visual=True):
    keys = ('technical', 'visual', 'rights') if visual else ('technical', 'rights')
    if any(data.get(key) != 'PASS' for key in keys):
        raise ValueError(label + ' is not approved in required gates')


def verify_candidate(candidate_path, root, copies=None, original_candidate=None):
    resolve = resolver(root, copies)
    canonical_candidate = original_candidate or canonical_reference(str(Path(candidate_path).absolute()), root)
    candidate_file = resolve(canonical_candidate)
    current = str(PurePosixPath(canonical_candidate).parent)
    chain, seen = {}, set()
    while True:
        if current in seen or len(seen) >= 64:
            raise ValueError('Creation parent chain is cyclic or too long')
        seen.add(current)
        run = resolve(current, directory=True)
        data = verify_creation_run(run, run)
        chain[current] = {'path': run, 'manifest': data, 'sha256': sha256(run / 'manifest.json')}
        parent = data.get('parent')
        if not parent:
            break
        if not isinstance(parent, dict):
            raise ValueError('Invalid parent reference')
        next_name = canonical_reference(parent['path'], root)
        next_run = resolve(next_name, directory=True)
        if sha256(safe_path(next_run / 'manifest.json', next_run)) != parent['manifestSha256']:
            raise ValueError('Parent manifest hash mismatch')
        current = next_name
    handoff_name = str(PurePosixPath(canonical_candidate).parent)
    handoff = chain[handoff_name]['manifest']
    if handoff.get('command') != 'handoff' or handoff['artifacts'].get('candidate.json') != sha256(candidate_file):
        raise ValueError('Candidate is not authenticated by a closed handoff run')
    require_gates(handoff, 'Handoff')
    candidate = read_json(candidate_file)
    if candidate.get('schemaVersion') != 1 or candidate.get('kind') != 'creation-candidate':
        raise ValueError('Unsupported candidate schema')
    require_gates(candidate.get('qa', {}), 'Candidate')
    if candidate.get('eligibleForPromotion') is not True or candidate.get('units') != 'm':
        raise ValueError('Candidate must be eligible and declare meters')
    asset_id = candidate.get('assetId')
    if not isinstance(asset_id, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', asset_id):
        raise ValueError('Invalid candidate assetId')
    refs = {}
    for label in ('sourceRun', 'reviewRun'):
        ref = candidate[label]
        name = canonical_reference(ref['path'], root)
        if name not in chain or chain[name]['sha256'] != ref['manifestSha256']:
            raise ValueError(label + ' is not hash-bound to handoff ancestry')
        refs[label] = chain[name]
    source, review = refs['sourceRun'], refs['reviewRun']
    require_gates(source['manifest'], 'Source', visual=False)
    require_gates(review['manifest'], 'Review')
    while review['manifest'].get('command') != 'review':
        pointer = review['manifest'].get('parent')
        if not pointer:
            raise ValueError('No explicit visual review in approved ancestry')
        review = chain[canonical_reference(pointer['path'], root)]
        require_gates(review['manifest'], 'Review ancestry')
    if source['manifest'].get('command') != 'canary':
        raise ValueError('Expected a supported canary source with measured original geometry')
    review_doc = read_json(safe_path(review['path'] / 'review.json', review['path']))
    expected_views = {view: source['manifest']['artifacts']['renders/' + view + '.png'] for view in VIEWS}
    source_name = canonical_reference(candidate['sourceRun']['path'], root)
    review_source = review_doc.get('sourceRun', {})
    if (review_doc.get('decision') != 'PASS' or review_doc.get('openedImages') is not True
            or not isinstance(review_doc.get('reviewer'), str) or not review_doc['reviewer'].strip()
            or review_doc.get('evidence') != expected_views
            or canonical_reference(review_source.get('path'), root) != source_name
            or review_source.get('manifestSha256') != source['sha256']):
        raise ValueError('Visual review does not attest this source and its six exact renders')
    for item in chain.values():
        pointer = item['manifest'].get('sourceRun')
        if pointer and (canonical_reference(pointer['path'], root) != source_name or pointer['manifestSha256'] != source['sha256']):
            raise ValueError('Mixed creation source ancestry')
    brief = read_json(safe_path(source['path'] / 'brief.json', source['path']))
    metrics = read_json(safe_path(source['path'] / 'metrics.json', source['path']))['source']
    for label, file_name in (('asset', 'asset.glb'), ('editable', 'source.blend')):
        ref = candidate[label]
        expected_name = source_name + '/' + file_name
        if canonical_reference(ref['path'], root) != expected_name or ref['sha256'] != source['manifest']['artifacts'][file_name]:
            raise ValueError('Candidate source file is not bound to approved source run')
        if sha256(resolve(ref['path'])) != ref['sha256']:
            raise ValueError('Candidate source file checksum mismatch')
    if (candidate['assetId'] != brief['assetId'] or candidate['provenance'] != brief['provenance']
            or candidate['budgets'] != brief['budgets'] or candidate['dimensionsM'] != metrics['dimensionsM']
            or candidate['bboxM'] != {'min': metrics['bboxMinM'], 'max': metrics['bboxMaxM']}):
        raise ValueError('Candidate provenance, budgets or physical dimensions differ from source')
    if candidate.get('axes', {}).get('blender') != {'up': '+Z', 'front': '-Y'} or candidate.get('axes', {}).get('gltf') != {'up': '+Y', 'front': '+Z'}:
        raise ValueError('Unsupported source axis convention')
    if not isinstance(candidate['provenance'].get('license'), str) or not candidate['provenance']['license'].strip():
        raise ValueError('Candidate license is missing')
    return {'candidate': candidate, 'canonicalCandidate': canonical_candidate, 'chain': chain,
            'source': source, 'review': review}


def copy_candidate(candidate_path, root, run):
    verified = verify_candidate(candidate_path, root)
    destination = Path(run) / 'creation-input'
    destination.mkdir(exist_ok=False)
    evidence = []
    copies = {}
    for index, (canonical, item) in enumerate(sorted(verified['chain'].items())):
        target = destination / ('evidence-' + str(index))
        shutil.copytree(item['path'], target, symlinks=False)
        verify_creation_run(target, target)
        if sha256(target / 'manifest.json') != item['sha256']:
            raise ValueError('Copied evidence manifest changed')
        copies[canonical] = target
        evidence.append({'original': canonical, 'copied': target.relative_to(run).as_posix(),
                         'manifestSha256': item['sha256']})
    copied = verify_candidate(None, root, copies=copies, original_candidate=verified['canonicalCandidate'])
    candidate = copied['candidate']
    resolve = resolver(root, copies)
    return {'schemaVersion': 1, 'kind': 'creation-prepared', 'assetId': candidate['assetId'],
            'candidateOriginal': verified['canonicalCandidate'], 'evidence': evidence,
            'candidate': {'file': resolve(verified['canonicalCandidate']).relative_to(run).as_posix(),
                          'sha256': sha256(resolve(verified['canonicalCandidate']))},
            'sourceOriginal': {'file': resolve(candidate['asset']['path']).relative_to(run).as_posix(), 'sha256': candidate['asset']['sha256']},
            'editableOriginal': {'file': resolve(candidate['editable']['path']).relative_to(run).as_posix(), 'sha256': candidate['editable']['sha256']},
            'provenance': candidate['provenance'], 'axes': candidate['axes'], 'units': 'm',
            'dimensionsM': candidate['dimensionsM'], 'bboxM': candidate['bboxM'], 'inputQa': candidate['qa'],
            'transformPolicy': 'uniform longest dimension to 2m, XY center and ground Z; inverse required on all rig hierarchy roots',
            'visual': 'NOT_RUN'}


def snapshot_code(run, root):
    destination = Path(run) / 'adapter-code'
    destination.mkdir(exist_ok=False)
    for name in ('lab.py', 'creation_adapter.py', 'scripts/creation_geometry.py'):
        source = safe_path(Path(root) / 'lab' / name, Path(root))
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as output:
            output.write(source.read_bytes())
    return destination / 'scripts/creation_geometry.py'


def validate_normalization(normalization, candidate):
    matrix, inverse = normalization['matrix'], normalization['inverse']
    if any(not isinstance(rows, list) or len(rows) != 4 or any(not isinstance(row, list) or len(row) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in row) for row in rows) for rows in (matrix, inverse)):
        raise ValueError('Normalization must contain finite 4x4 matrix and inverse')
    for i in range(4):
        for j in range(4):
            if abs(sum(matrix[i][k] * inverse[k][j] for k in range(4)) - (1 if i == j else 0)) > 1e-6:
                raise ValueError('Normalization inverse does not invert matrix')
    dimensions = candidate['dimensionsM']
    if len(dimensions) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in dimensions):
        raise ValueError('Invalid candidate dimensions')
    scale = 2.0 / max(dimensions)
    bounds = candidate['bboxM']
    center = [(bounds['min'][i] + bounds['max'][i])/2 for i in range(2)] + [bounds['min'][2]]
    expected = [[scale if i == j else 0 for j in range(4)] for i in range(4)]
    expected[3][3] = 1
    for i in range(3):
        expected[i][3] = -center[i] * scale
    if any(abs(matrix[i][j] - expected[i][j]) > 1e-5 for i in range(4) for j in range(4)):
        raise ValueError('Normalization differs from explicit 2m policy')


def passed_checks(data):
    checks = data.get('checks')
    return isinstance(checks, list) and bool(checks) and all(isinstance(check, dict) and check.get('status') == 'passed' for check in checks)


def verify_geometry(run, receipt, geometry):
    if (geometry.get('schemaVersion') != 1 or geometry.get('kind') != 'creation-geometry'
            or geometry.get('status') != 'passed' or not passed_checks(geometry)):
        raise ValueError('Geometry preparation did not pass all checks')
    if geometry.get('sourceSha256') != receipt['sourceOriginal']['sha256']:
        raise ValueError('Geometry preparation is bound to a different source GLB')
    worker = safe_path(run / 'adapter-code/scripts/creation_geometry.py', run)
    if geometry.get('workerSha256') != sha256(worker):
        raise ValueError('Geometry worker hash differs from snapshotted worker')
    for name in ('prepared.glb', 'control.glb'):
        item = geometry.get('files', {}).get(name, {})
        if item.get('file') != name or item.get('sha256') != sha256(safe_path(run / 'prepared' / name, run)):
            raise ValueError('Geometry file receipt differs from actual output: ' + name)
    validate_normalization(geometry['normalization'], receipt)


def seal_prepared(run, receipt):
    run = Path(run)
    geometry_file = safe_path(run / 'prepared/geometry.json', run)
    geometry = read_json(geometry_file)
    verify_geometry(run, receipt, geometry)
    for label, name in (('prepared', 'prepared/prepared.glb'), ('control', 'prepared/control.glb'), ('geometry', 'prepared/geometry.json')):
        path = safe_path(run / name, run)
        receipt[label] = {'file': name, 'sha256': sha256(path)}
    if receipt['control']['sha256'] != receipt['sourceOriginal']['sha256']:
        raise ValueError('Control must be a byte-exact copy of original GLB')
    receipt['normalization'] = geometry['normalization']
    receipt['status'] = 'passed'
    receipt['artifacts'] = {}
    for folder in ('creation-input', 'prepared', 'adapter-code'):
        for path in sorted((run / folder).rglob('*')):
            if path.is_symlink():
                raise ValueError('Symlink in immutable adapter output')
            if path.is_file():
                receipt['artifacts'][path.relative_to(run).as_posix()] = sha256(path)
    write_json(run / 'creation-prepared.json', receipt)
    (run / 'creation-prepared.COMPLETE').write_text(sha256(run / 'creation-prepared.json') + '\n', encoding='ascii')
    return receipt


def load_prepared(manifest_path, root):
    manifest = safe_path(Path(manifest_path).absolute(), Path(root))
    run = manifest.parent
    marker = safe_path(run / 'creation-prepared.COMPLETE', run).read_text(encoding='ascii').strip()
    if sha256(manifest) != marker:
        raise ValueError('Prepared manifest does not match COMPLETE')
    receipt = read_json(manifest)
    if receipt.get('schemaVersion') != 1 or receipt.get('kind') != 'creation-prepared' or receipt.get('status') != 'passed':
        raise ValueError('Unsupported or unapproved prepared candidate')
    for name, expected in receipt['artifacts'].items():
        relative_name(name)
        if sha256(safe_path(run / name, run)) != expected:
            raise ValueError('Prepared artifact checksum mismatch: ' + name)
    copies = {}
    for item in receipt['evidence']:
        canonical = canonical_reference(item['original'], root)
        if canonical in copies:
            raise ValueError('Duplicate evidence mapping')
        copied = safe_path(run / relative_name(item['copied']), run, directory=True)
        if sha256(safe_path(copied / 'manifest.json', copied)) != item['manifestSha256']:
            raise ValueError('Copied manifest reference changed')
        copies[canonical] = copied
    verified = verify_candidate(None, root, copies=copies, original_candidate=receipt['candidateOriginal'])
    authoritative = verified['candidate']
    for key in ('assetId', 'provenance', 'axes', 'units', 'dimensionsM', 'bboxM'):
        if receipt.get(key) != authoritative.get(key):
            raise ValueError('Prepared metadata differs from candidate: ' + key)
    if receipt.get('inputQa') != authoritative['qa']:
        raise ValueError('Prepared approval gates differ from candidate')
    resolve = resolver(root, copies)
    for label, raw, expected_hash in (
            ('candidate', receipt['candidateOriginal'], sha256(resolve(receipt['candidateOriginal']))),
            ('sourceOriginal', authoritative['asset']['path'], authoritative['asset']['sha256']),
            ('editableOriginal', authoritative['editable']['path'], authoritative['editable']['sha256'])):
        expected = {'file': resolve(raw).relative_to(run).as_posix(), 'sha256': expected_hash}
        if receipt.get(label) != expected:
            raise ValueError('Prepared source reference differs from approved evidence: ' + label)
    for label in ('candidate', 'sourceOriginal', 'editableOriginal', 'prepared', 'control', 'geometry'):
        ref = receipt[label]
        relative_name(ref['file'])
        if receipt['artifacts'].get(ref['file']) != ref['sha256']:
            raise ValueError('Prepared file reference is not authenticated: ' + label)
    for label, expected_file in (('prepared', 'prepared/prepared.glb'), ('control', 'prepared/control.glb'), ('geometry', 'prepared/geometry.json')):
        if receipt[label]['file'] != expected_file:
            raise ValueError('Prepared output must use its canonical path: ' + label)
    if receipt['control']['sha256'] != receipt['sourceOriginal']['sha256']:
        raise ValueError('Prepared control no longer matches original GLB')
    geometry = read_json(safe_path(run / receipt['geometry']['file'], run))
    if geometry.get('status') != 'passed' or geometry['normalization'] != receipt['normalization']:
        raise ValueError('Prepared geometry receipt differs from sealed normalization')
    verify_geometry(run, receipt, geometry)
    validate_normalization(receipt['normalization'], verified['candidate'])
    return run, receipt


def verify_restoration(report, output_dir, merged, geometry_file, worker, normalization):
    data = read_json(report)
    if (data.get('schemaVersion') != 1 or data.get('kind') != 'creation-restoration'
            or data.get('status') != 'passed' or not passed_checks(data)):
        raise ValueError('Restoration did not pass every geometry/material/weight check')
    if (data.get('geometrySha256') != sha256(geometry_file) or data.get('inputSha256') != sha256(merged)
            or data.get('workerSha256') != sha256(worker) or data.get('normalization') != normalization):
        raise ValueError('Restoration receipt is bound to different inputs, transform or worker')
    output = safe_path(Path(output_dir) / 'restored.glb', output_dir)
    expected = data.get('files', {}).get('restored.glb', {})
    if expected.get('file') != 'restored.glb' or expected.get('sha256') != sha256(output):
        raise ValueError('Restored output differs from restoration receipt')
    return data


def copy_prepared(manifest_path, root, run):
    source, receipt = load_prepared(manifest_path, root)
    target = Path(run) / 'candidate-input'
    target.mkdir(exist_ok=False)
    # Copy only the sealed inventory, not transient workspaces or live run logs.
    for name in [*receipt['artifacts'], 'creation-prepared.json', 'creation-prepared.COMPLETE']:
        path = safe_path(source / name, source)
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as output:
            output.write(path.read_bytes())
        if sha256(destination) != sha256(path):
            raise ValueError('Prepared copy checksum mismatch')
    _, copied = load_prepared(target / 'creation-prepared.json', root)
    return target, copied
