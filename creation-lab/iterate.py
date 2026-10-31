"""Local, evidence-bound Sol/Luna iterations. Does not invoke a model API.

Default modes accept only Sol/Luna. The explicit `claude` mode accepts only the
exact Claude IDs in CLAUDE_MODELS; it is an authoring choice, not a benchmark.
The explicit `benchmark` mode records an isolated, user-requested comparison
profile frozen inside the session.
"""
import argparse
import ast
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
SOL, LUNA = 'gpt-6.1-sol', 'gpt-6-luna'
STATES = {'PASS', 'FAIL', 'BLOCKED', 'NOT_RUN'}
EFFORTS = {'low', 'medium', 'high', 'xhigh', 'max'}
MODES = {'sol', 'mixed', 'luna', 'claude', 'benchmark'}
# Exact IDs only; aliases (sonnet, opus, ...) never match these sets.
CLAUDE_MODELS = {'coordinator': {'claude-sonnet-5-5', 'claude-opus-5-5'},
                 'author': {'claude-sonnet-5-5', 'claude-opus-5-5', 'claude-haiku-5-5'},
                 'reviewer': {'claude-opus-5-5', 'claude-sonnet-5-5'}}
CLAUDE_REVIEWER_DEFAULT = 'claude-opus-5-5'
# Aliases can move to another version; a profile must name exact model IDs.
MODEL_ALIASES = {'haiku', 'sonnet', 'opus', 'fable', 'opusplan', 'default', 'best', 'sol', 'luna'}
VIEWS = ('front', 'side', 'back', 'three-quarter', 'wireframe', 'reimport-three-quarter')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def require(test, message):
    if not test:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def slug(value):
    return nonempty(value) and len(value) <= 100 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in value)


def content_checks(brief, stage):
    if stage == 'blockout':
        return brief.get('blockoutChecks', ['Las partes tienen volúmenes distinguibles y relaciones espaciales coherentes con el brief; el detalle sigue pendiente.'])
    return brief.get('contentChecks', brief.get('biologicalChecks'))


def contained(root, name):
    require(nonempty(name) and '\\' not in name and ':' not in name, 'Invalid artifact path')
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts, 'Artifact escapes root')
    result = root / relative
    require(not any(p.is_symlink() for p in (result, *result.parents) if p != root.parent), 'Symlink artifact')
    result = result.resolve(strict=True)
    require(result.is_relative_to(root.resolve()) and result.is_file(), 'Artifact must be a contained file')
    return result


def validate_brief(brief):
    require(isinstance(brief, dict) and brief.get('schemaVersion') == 1, 'brief.schemaVersion must be 1')
    require(slug(brief.get('id')), 'brief.id must be a lowercase slug')
    require(nonempty(brief.get('purpose')), 'brief.purpose is required')
    parts = brief.get('parts')
    require(isinstance(parts, list) and parts, 'brief.parts must be nonempty')
    ids = []
    for part in parts:
        require(isinstance(part, dict) and slug(part.get('id')) and nonempty(part.get('label')), 'Each part needs id and label')
        ids.append(part['id'])
    require(len(ids) == len(set(ids)), 'Part IDs must be unique')
    scale = brief.get('displayScale', {})
    require(scale.get('units') == 'm', 'Use displayScale.units=m')
    for field, upper in [('longestDimension', 100), ('tolerance', .1)]:
        value = scale.get(field)
        require(type(value) in (int, float) and math.isfinite(value) and 0 < value <= upper, 'Invalid displayScale.' + field)
    budgets = brief.get('budgets', {})
    for field in ('triangles', 'materials', 'meshObjects', 'glbBytes'):
        require(type(budgets.get(field)) is int and budgets[field] > 0, 'Positive integer budget required: ' + field)
    require(type(brief.get('seed')) is int, 'Integer seed is required')
    provenance = brief.get('provenance', {})
    require(all(nonempty(provenance.get(k)) for k in ('author', 'origin', 'license')), 'Provenance author/origin/license required')
    checks = brief.get('contentChecks', brief.get('biologicalChecks'))
    require(isinstance(checks, list) and checks and all(nonempty(c) for c in checks), 'contentChecks (or biologicalChecks) required')
    require(len(checks) == len(set(checks)), 'Content checks must be unique')
    blockout = content_checks(brief, 'blockout')
    require(isinstance(blockout, list) and blockout and all(nonempty(c) for c in blockout) and len(blockout) == len(set(blockout)), 'Invalid blockoutChecks')
    return brief


def validate_profile(profile):
    """Isolated benchmark profile: exact model IDs and efforts per role."""
    require(isinstance(profile, dict) and profile.get('schemaVersion') == 1, 'profile.schemaVersion must be 1')
    require(slug(profile.get('id')), 'profile.id must be a lowercase slug')
    def role(item, name):
        require(isinstance(item, dict), 'Profile role required: ' + name)
        models, efforts = item.get('models'), item.get('efforts')
        require(isinstance(models, list) and models and all(nonempty(m) for m in models), 'Profile models required: ' + name)
        require(all(m.strip() == m and m.lower() not in MODEL_ALIASES and '-' in m for m in models), 'Profile must name exact model IDs, not aliases: ' + name)
        require(isinstance(efforts, list) and efforts and set(efforts) <= EFFORTS, 'Profile efforts invalid: ' + name)
    roles = profile.get('roles', {})
    for name in ('coordinator', 'reviewer'):
        role(roles.get(name), name)
    conditions = profile.get('conditions')
    require(isinstance(conditions, dict) and conditions, 'Profile conditions required')
    for name, item in conditions.items():
        require(slug(name) and isinstance(item, dict), 'Invalid profile condition')
        role(item.get('author'), name + '/author')
    return profile


def allowed(mode, role, benchmark=None):
    """(models, efforts) for a role. Defaults stay Sol/Luna-only; `claude` is an explicit extra mode."""
    if mode == 'benchmark':
        require(isinstance(benchmark, dict), 'Benchmark mode requires a frozen profile')
        profile, condition = benchmark['profile'], benchmark['condition']
        item = profile['conditions'][condition]['author'] if role == 'author' else profile['roles'][role]
        return set(item['models']), set(item['efforts'])
    if mode == 'claude':
        require(role in CLAUDE_MODELS, 'Invalid role')
        return set(CLAUDE_MODELS[role]), EFFORTS
    require(mode in {'sol', 'mixed', 'luna'}, 'Invalid mode')
    models = {SOL} if mode == 'sol' or (mode == 'mixed' and role in ('coordinator', 'reviewer')) else {LUNA} if mode == 'luna' else {SOL, LUNA}
    return models, EFFORTS


def actor(value, mode, role, benchmark=None):
    require(isinstance(value, dict) and nonempty(value.get('actorId')), 'An actual agent/context identifier is required')
    models, efforts = allowed(mode, role, benchmark)
    require(value.get('model') in models, 'Model not allowed for ' + mode + '/' + role)
    require(value.get('reasoningEffort') in efforts, 'Unsupported reasoning effort for ' + mode + '/' + role)
    return value


def session_actor(value, session, role):
    return actor(value, session['mode'], role, session.get('benchmark'))


def actor_args(args):
    return {'actorId': args.actor_id, 'model': args.model, 'reasoningEffort': args.effort}


def init_session(brief_path, output, mode, coordinator, max_corrections=2, profile_path=None, condition=None):
    brief = validate_brief(read(brief_path))
    require(mode in MODES, 'Invalid mode')
    benchmark = None
    if mode == 'benchmark':
        require(profile_path is not None and nonempty(condition), 'Benchmark mode requires --profile and --condition')
        profile = validate_profile(read(profile_path))
        require(condition in profile['conditions'], 'Condition is not defined by the profile')
        benchmark = {'profile': profile, 'profileSha256': digest(profile_path), 'condition': condition}
    else:
        require(profile_path is None and condition is None, '--profile/--condition apply only to benchmark mode')
    actor(coordinator, mode, 'coordinator', benchmark)
    require(type(max_corrections) is int and 0 <= max_corrections <= 10, 'max-corrections must be 0..10')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'brief.json', brief)
    session = {'schemaVersion': 1, 'sessionId': uuid.uuid4().hex, 'mode': mode,
               'coordinator': coordinator, 'maxCorrections': max_corrections,
               'briefSha256': digest(output / 'brief.json'),
               **({'benchmark': benchmark} if benchmark else {}),
               'modelEvidence': 'Coordinator-declared execution settings; not backend attestation',
               'createdAt': datetime.now(timezone.utc).isoformat()}
    write(output / 'session.json', session)
    (output / 'COMPLETE').write_text(digest(output / 'session.json') + '\n', encoding='ascii')
    (output / 'runs').mkdir()
    (output / 'reviews').mkdir()
    return output


def load_session(path):
    path = Path(path).resolve(strict=True)
    session = read(contained(path, 'session.json'))
    require(contained(path, 'COMPLETE').read_text().strip() == digest(path / 'session.json'), 'Session seal differs')
    require(session.get('schemaVersion') == 1 and session.get('mode') in MODES, 'Invalid session')
    require((session['mode'] == 'benchmark') == ('benchmark' in session), 'Benchmark profile and mode differ')
    if session['mode'] == 'benchmark':
        validate_profile(session['benchmark'].get('profile'))
        require(session['benchmark'].get('condition') in session['benchmark']['profile']['conditions'], 'Invalid benchmark condition')
    require(digest(contained(path, 'brief.json')) == session['briefSha256'], 'Brief changed after initialization')
    validate_brief(read(path / 'brief.json'))
    session_actor(session['coordinator'], session, 'coordinator')
    return path, session


@contextmanager
def session_lock(path):
    lock = path / '.writer.lock'
    try:
        stream = lock.open('x', encoding='utf-8')
    except FileExistsError:
        raise ValueError('Session already has a writer; inspect its process before removing a stale .writer.lock')
    try:
        with stream:
            stream.write(datetime.now(timezone.utc).isoformat())
        yield
    finally:
        lock.unlink()


def load_run(session_path, run_id):
    require(slug(run_id), 'Invalid run ID')
    path = session_path / 'runs' / run_id
    manifest = read(contained(path, 'manifest.json'))
    require(contained(path, 'COMPLETE').read_text().strip() == digest(path / 'manifest.json'), 'Incomplete or changed run')
    require(manifest.get('runId') == run_id, 'Run identity differs')
    session = read(session_path / 'session.json')
    require(manifest.get('sessionSha256') == digest(session_path / 'session.json'), 'Run belongs to another session')
    require(manifest.get('schemaVersion') == 1 and manifest.get('stage') in {'blockout', 'detail'} and manifest.get('technical') in STATES, 'Invalid run schema')
    session_actor(manifest.get('author'), session, 'author')
    require(digest(contained(path, 'brief.json')) == session['briefSha256'], 'Run brief differs from session')
    for name, checksum in manifest['artifacts'].items():
        require(digest(contained(path, name)) == checksum, 'Changed artifact: ' + name)
    return path, manifest


def load_runs(path):
    runs = []
    for item in sorted((path / 'runs').iterdir()):
        require(item.is_dir() and not item.is_symlink(), 'Unexpected item in runs')
        require((item / 'COMPLETE').is_file(), 'Pending run ' + item.name + '; inspect process, then use recover --stopped if interrupted')
        runs.append(load_run(path, item.name))
    for index, (_, run) in enumerate(runs):
        require(run['sequence'] == index + 1, 'Run sequence broken')
        previous = runs[index - 1][1]['runId'] if index else None
        require(run['parentRunId'] == previous, 'Run lineage broken')
    return runs


def validate_review(path, session, run_path, run, review):
    require(review.get('schemaVersion') == 1 and review.get('runId') == run['runId'], 'Review identity differs')
    require(review.get('manifestSha256') == digest(run_path / 'manifest.json'), 'Review belongs to another manifest')
    reviewer = session_actor(review.get('reviewer'), session, 'reviewer')
    authors = {r['author']['actorId'] for _, r in load_runs(path)}
    require(reviewer['actorId'] not in authors, 'Reviewer must use a context independent of every author in this session')
    require(review.get('openedImages') is True, 'Open the actual images before reviewing')
    expected = {view: run['artifacts'].get('renders/' + view + '.png') for view in VIEWS}
    require(all(expected.values()) and review.get('images') == expected, 'Review must bind all six actual image hashes')
    for view, checksum in expected.items():
        require(digest(contained(run_path, 'renders/' + view + '.png')) == checksum, 'Image changed')
    for gate in ('visual', 'content'):
        item = review.get(gate, {})
        require(item.get('status') in STATES and nonempty(item.get('reason')), 'Review gate requires status and reason: ' + gate)
    brief = read(path / 'brief.json')
    observations = review.get('parts')
    require(isinstance(observations, list), 'Part observations required')
    ids = [p.get('id') for p in observations]
    require(len(ids) == len(set(ids)) and set(ids) == {p['id'] for p in brief['parts']}, 'Observe every required part exactly once')
    for item in observations:
        require(item.get('visibility') in {'visible', 'hidden', 'unclear'} and nonempty(item.get('reason')), 'Part visibility and reason required')
        require(isinstance(item.get('views'), list) and item['views'] and set(item['views']) <= set(VIEWS), 'Evidence views required per part')
    checks = content_checks(brief, run['stage'])
    observed = review.get('checks')
    require(isinstance(observed, list) and [c.get('check') for c in observed] == checks, 'Review every content check in brief order')
    for check in observed:
        require(check.get('status') in STATES and nonempty(check.get('reason')), 'Content check status and reason required')
    if review['visual']['status'] == 'PASS' or review['content']['status'] == 'PASS':
        require(all(p['visibility'] == 'visible' for p in observations), 'Hidden/unclear required parts cannot receive PASS')
    if review['content']['status'] == 'PASS':
        require(all(c['status'] == 'PASS' for c in observed), 'Failed/unobserved content check cannot receive PASS')
    defects = review.get('defects')
    require(isinstance(defects, list), 'defects must be a list')
    for defect in defects:
        require(defect.get('view') in VIEWS and nonempty(defect.get('detail')) and nonempty(defect.get('requestedChange')), 'Each defect needs view, detail and requestedChange')
    if any(review[g]['status'] in {'FAIL', 'BLOCKED'} for g in ('visual', 'content')):
        require(bool(defects), 'Failed review needs actionable defects')
    return review


def get_review(path, session, run_path, run):
    target = path / 'reviews' / (run['runId'] + '.json')
    return validate_review(path, session, run_path, run, read(target)) if target.exists() else None


def passed(run, review):
    return run['technical'] == 'PASS' and review and all(review[g]['status'] == 'PASS' for g in ('visual', 'content'))


def status(path):
    path, session = load_session(path)
    pending = sorted(p.name for p in (path / 'runs').iterdir() if p.is_dir() and not (p / 'COMPLETE').exists())
    if pending:
        return {'session': str(path), 'mode': session['mode'], 'status': 'BLOCKED', 'next': 'inspect-pending-run', 'pendingRuns': pending}
    runs = load_runs(path)
    used = len(runs) - len({run['stage'] for _, run in runs})
    result = {'session': str(path), 'mode': session['mode'], 'correctionsUsed': used,
              **({'condition': session['benchmark']['condition']} if session['mode'] == 'benchmark' else {}),
              'correctionsRemaining': session['maxCorrections'] - used, 'status': 'NOT_RUN', 'next': 'blockout'}
    if runs:
        run_path, run = runs[-1]
        review = get_review(path, session, run_path, run)
        result.update(runId=run['runId'], stage=run['stage'], technical=run['technical'],
                      visual=review['visual']['status'] if review else 'NOT_RUN',
                      content=review['content']['status'] if review else 'NOT_RUN')
        if passed(run, review):
            result.update(status='PASS' if run['stage'] == 'detail' else 'READY_FOR_DETAIL', next='handoff' if run['stage'] == 'detail' else 'detail')
        elif run['technical'] == 'PASS' and not review:
            result.update(status='BLOCKED', next='review')
        else:
            result.update(status='FAIL' if used < session['maxCorrections'] else 'BLOCKED',
                          next='correct-' + run['stage'] if used < session['maxCorrections'] else 'stop-budget-exhausted')
    return result


def preflight(path, session, stage, author):
    session_actor(author, session, 'author')
    runs = load_runs(path)
    for rp, run in runs:
        review = get_review(path, session, rp, run)
        require(not review or review['reviewer']['actorId'] != author['actorId'], 'A reviewer context cannot become an author in this session')
    if not runs:
        require(stage == 'blockout', 'Start with blockout')
        return runs
    rp, last = runs[-1]
    review = get_review(path, session, rp, last)
    if stage != last['stage']:
        require(last['stage'] == 'blockout' and stage == 'detail' and passed(last, review), 'Detail requires approved latest blockout')
    else:
        require(last['technical'] != 'PASS' or review is not None, 'Review rendered output before a visual correction')
        used = len(runs) - len({r['stage'] for _, r in runs})
        require(used < session['maxCorrections'], 'Correction budget exhausted; stop and report remaining defects')
    return runs


def check_generator(path):
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    allowed = {'bpy', 'math', 'random', 'mathutils', 'components'}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            require(all(n.name.split('.')[0] in allowed for n in node.names), 'Unexpected generator import')
        if isinstance(node, ast.ImportFrom):
            require((node.module or '').split('.')[0] in allowed and not node.level, 'Unexpected generator import')
    # This is a contract check for trusted local code, not a Python security sandbox.


def run_generator(args):
    path, session = load_session(args.session)
    author = actor_args(args)
    blender = Path(args.blender).resolve(strict=True)
    require(blender.is_file(), 'Blender executable required')
    generator = Path(args.generator).resolve(strict=True)
    check_generator(generator)
    require(args.timeout > 0, 'timeout must be positive')
    with session_lock(path):
        runs = preflight(path, session, args.stage, author)
        rid = f'{len(runs)+1:03d}-' + uuid.uuid4().hex[:12]
        target = path / 'runs' / rid
        manifest = {'schemaVersion': 1, 'runId': rid, 'sequence': len(runs)+1, 'stage': args.stage,
                    'parentRunId': runs[-1][1]['runId'] if runs else None,
                    'sessionSha256': digest(path / 'session.json'), 'author': author,
                    'technical': 'NOT_RUN', 'modelUsage': None, 'stages': [], 'artifacts': {}}
        target.mkdir()
        write(target / 'request.json', manifest)
        shutil.copy2(path / 'brief.json', target / 'brief.json')
        try:
            import os
            import time
            (target / 'code').mkdir()
            shutil.copy2(generator, target / 'generator.py')
            shutil.copy2(__file__, target / 'code/iterate.py')
            shutil.copy2(BASE / 'scripts/iteration_worker.py', target / 'code/worker.py')
            shutil.copy2(ROOT / 'lab/scripts/creation_geometry.py', target / 'code/geometry_qa.py')
            shutil.copytree(BASE / 'components', target / 'code/components', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            for step in ('build', 'reopen', 'reimport'):
                command = [str(blender), '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
                           '--python', str(target / 'code/worker.py'), '--', step, str(target)]
                started = time.monotonic()
                with (target / (step + '.log')).open('x', encoding='utf-8') as log:
                    proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout,
                                          env={**os.environ, 'CUDA_VISIBLE_DEVICES': '', 'OMP_NUM_THREADS': '2', 'PYTHONDONTWRITEBYTECODE': '1'})
                manifest['stages'].append({'step': step, 'command': command, 'seconds': round(time.monotonic()-started, 3), 'returncode': proc.returncode})
                require(proc.returncode == 0, step + ' failed; inspect ' + step + '.log')
            manifest['technical'] = 'PASS' if all(read(target / (step + '-result.json'))['status'] == 'PASS' for step in ('build', 'reopen', 'reimport')) else 'FAIL'
            require((target / 'asset.glb').stat().st_size <= read(path / 'brief.json')['budgets']['glbBytes'], 'GLB byte budget exceeded')
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            manifest.update(technical='FAIL', error=str(exc))
        manifest['artifacts'] = {p.relative_to(target).as_posix(): digest(p) for p in sorted(target.rglob('*')) if p.is_file()}
        write(target / 'manifest.json', manifest)
        (target / 'COMPLETE').write_text(digest(target / 'manifest.json') + '\n', encoding='ascii')
    return {'run': str(target), 'runId': rid, 'technical': manifest['technical'], 'visual': 'NOT_RUN', 'content': 'NOT_RUN'}


def recover(path, run_id, reason, stopped):
    path, session = load_session(path)
    require(stopped and nonempty(reason), 'Inspect and stop the old process first; --stopped and a reason are required')
    require(slug(run_id), 'Invalid run ID')
    pending = [p for p in (path / 'runs').iterdir() if p.is_dir() and not (p / 'COMPLETE').exists()]
    require(len(pending) == 1 and pending[0].name == run_id, 'Recover the single pending run only')
    target = pending[0]
    manifest = read(contained(target, 'request.json'))
    require(manifest.get('sessionSha256') == digest(path / 'session.json') and manifest.get('runId') == run_id, 'Pending request belongs to another session')
    session_actor(manifest.get('author'), session, 'author')
    # Explicit operator attestation; no process is killed by this command.
    if (path / '.writer.lock').exists():
        lock_evidence = target / 'interrupted-writer.lock'
        if lock_evidence.exists():
            lock_evidence = target / ('interrupted-writer-' + uuid.uuid4().hex + '.lock')
        (path / '.writer.lock').rename(lock_evidence)
    with session_lock(path):
        if (target / 'manifest.json').exists():
            unsealed = target / 'unsealed-manifest.json'
            if unsealed.exists():
                unsealed = target / ('unsealed-manifest-' + uuid.uuid4().hex + '.json')
            (target / 'manifest.json').rename(unsealed)
        if not (target / 'brief.json').exists():
            shutil.copy2(path / 'brief.json', target / 'brief.json')
        manifest.update(technical='FAIL', error='Interrupted run recovered as FAIL',
                        recovery={'reason': reason, 'operatorConfirmedStopped': True, 'at': datetime.now(timezone.utc).isoformat()})
        manifest['artifacts'] = {p.relative_to(target).as_posix(): digest(p) for p in sorted(target.rglob('*')) if p.is_file()}
        write(target / 'manifest.json', manifest)
        (target / 'COMPLETE').write_text(digest(target / 'manifest.json') + '\n', encoding='ascii')
    return {'runId': run_id, 'technical': 'FAIL', 'recovered': True, 'next': 'inspect-diagnostics-before-correction'}


def review_template(path, run_id):
    path, session = load_session(path)
    run_path, run = load_run(path, run_id)
    brief = read(path / 'brief.json')
    if session['mode'] == 'benchmark':
        reviewer = session['benchmark']['profile']['roles']['reviewer']
        model, effort = reviewer['models'][0], reviewer['efforts'][0]
    elif session['mode'] == 'claude':
        model, effort = CLAUDE_REVIEWER_DEFAULT, 'medium'
    else:
        model, effort = LUNA if session['mode'] == 'luna' else SOL, 'medium'
    return {'schemaVersion': 1, 'runId': run_id, 'manifestSha256': digest(run_path / 'manifest.json'),
            'reviewer': {'actorId': '', 'model': model, 'reasoningEffort': effort},
            'openedImages': False, 'images': {v: run['artifacts'].get('renders/' + v + '.png') for v in VIEWS},
            'visual': {'status': 'NOT_RUN', 'reason': ''}, 'content': {'status': 'NOT_RUN', 'reason': ''},
            'parts': [{'id': p['id'], 'visibility': 'unclear', 'views': [], 'reason': ''} for p in brief['parts']],
            'checks': [{'check': c, 'status': 'NOT_RUN', 'reason': ''} for c in content_checks(brief, run['stage'])],
            'defects': []}


def save_review(path, value):
    path, session = load_session(path)
    with session_lock(path):
        rp, run = load_run(path, value.get('runId'))
        validate_review(path, session, rp, run, value)
        output = path / 'reviews' / (run['runId'] + '.json')
        write(output, value)
    return {'review': str(output), 'visual': value['visual']['status'], 'content': value['content']['status']}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    def add_actor(item):
        item.add_argument('--actor-id', required=True, help='Actual agent/context ID; recorded, not inferred')
        # Validated against the session mode/profile: Sol/Luna unless claude or benchmark.
        item.add_argument('--model', required=True, help=f'Exact model ID; {SOL} or {LUNA} in sol/mixed/luna; claude-* IDs in claude mode; profile IDs in benchmark mode')
        item.add_argument('--effort', default='medium', choices=sorted(EFFORTS))
    init = sub.add_parser('init'); init.add_argument('--brief', required=True, type=Path)
    init.add_argument('--output', type=Path); init.add_argument('--mode', choices=['sol', 'mixed', 'luna', 'claude', 'benchmark'], default='mixed')
    init.add_argument('--profile', type=Path, help='Benchmark mode only: frozen model profile JSON')
    init.add_argument('--condition', help='Benchmark mode only: condition defined by the profile')
    init.add_argument('--max-corrections', type=int, default=2); add_actor(init)
    run = sub.add_parser('run'); run.add_argument('--session', required=True, type=Path)
    run.add_argument('--generator', required=True, type=Path); run.add_argument('--stage', choices=['blockout', 'detail'], required=True)
    run.add_argument('--blender', required=True, type=Path); run.add_argument('--timeout', type=int, default=600); add_actor(run)
    template = sub.add_parser('review-template'); template.add_argument('--session', required=True, type=Path)
    template.add_argument('--run', required=True); template.add_argument('--output', required=True, type=Path)
    review = sub.add_parser('review'); review.add_argument('--session', required=True, type=Path); review.add_argument('--input', required=True, type=Path)
    recovery = sub.add_parser('recover'); recovery.add_argument('--session', required=True, type=Path)
    recovery.add_argument('--run', required=True); recovery.add_argument('--reason', required=True); recovery.add_argument('--stopped', action='store_true')
    state = sub.add_parser('status'); state.add_argument('--session', required=True, type=Path)
    return p


def main(argv=None):
    p = parser(); args = p.parse_args(argv)
    try:
        if args.command == 'init':
            output = args.output or BASE / '.local/iterations' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
            result = {'session': str(init_session(args.brief, output, args.mode, actor_args(args), args.max_corrections, args.profile, args.condition))}
        elif args.command == 'run':
            result = run_generator(args)
        elif args.command == 'review-template':
            write(args.output, review_template(args.session, args.run)); result = {'template': str(args.output)}
        elif args.command == 'review':
            result = save_review(args.session, read(args.input))
        elif args.command == 'recover':
            result = recover(args.session, args.run, args.reason, args.stopped)
        else:
            result = status(args.session)
        print(json.dumps(result, ensure_ascii=False))
        return 1 if result.get('technical') == 'FAIL' or result.get('status') in {'FAIL', 'BLOCKED'} else 0
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        p.error(str(exc))


if __name__ == '__main__':
    raise SystemExit(main())
