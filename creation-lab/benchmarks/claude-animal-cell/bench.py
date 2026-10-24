"""Coordinator tool for the isolated Claude animal-cell benchmark.

Wraps creation-lab/iterate.py (benchmark mode). It never writes condition
geometry, never calls a model API and never edits run evidence. Blind review
packets hide the author mapping; receipts read Claude Code runtime transcripts.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEFAULT_ROOT = REPO / 'creation-lab/.local/claude-animal-cell-20261023/batch'
spec = importlib.util.spec_from_file_location('iterate', REPO / 'creation-lab/iterate.py')
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)
read, write, digest, VIEWS = flow.read, flow.write, flow.digest, flow.VIEWS
FAMILIES, AUTHORINGS = ('haiku', 'sonnet', 'opus'), 3


def now():
    return datetime.now(timezone.utc).isoformat()


def update(path, change):
    """Coordinator registries are append/merge only; evidence files are never edited."""
    value = read(path) if path.exists() else {}
    change(value)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)
    return value


def profile():
    return read(HERE / 'profile.json')


def mapping(root):
    return read(root / 'coordinator/mapping.json')


def author_actor(root, replica):
    item = mapping(root)['replicas'][replica]
    agent = read(root / 'coordinator/agents.json').get('authors', {}).get(replica)
    flow.require(agent, 'Register the real author agent ID first')
    model = profile()['conditions'][item['condition']]['author']
    return {'actorId': agent, 'model': model['models'][0], 'reasoningEffort': model['efforts'][0]}


def setup(root, coordinator_id):
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    for name in ('coordinator', 'sessions', 'authors', 'blind'):
        (root / name).mkdir()
    conditions = [f for f in FAMILIES for _ in range(AUTHORINGS)]
    secrets.SystemRandom().shuffle(conditions)
    replicas = {}
    index = Counter()
    coord = profile()['roles']['coordinator']
    coordinator = {'actorId': coordinator_id, 'model': coord['models'][0], 'reasoningEffort': coord['efforts'][0]}
    for number, condition in enumerate(conditions, 1):
        replica = f'R{number}'
        index[condition] += 1
        session = flow.init_session(HERE / 'brief.json', root / 'sessions' / replica, 'benchmark', coordinator,
                                    2, HERE / 'profile.json', condition)
        (root / 'authors' / replica).mkdir()
        replicas[replica] = {'condition': condition, 'authoring': index[condition], 'session': str(session.relative_to(root))}
    write(root / 'coordinator/mapping.json', {'schemaVersion': 1, 'createdAt': now(), 'shuffle': 'secrets.SystemRandom',
                                              'note': 'Coordinator-only. Never give this file to reviewers.', 'replicas': replicas})
    write(root / 'coordinator/agents.json', {'authors': {}, 'reviewers': {}})
    return {'root': str(root), 'replicas': sorted(replicas)}


def register(root, replica, agent_id):
    flow.require(replica in mapping(root)['replicas'] and flow.nonempty(agent_id), 'Unknown replica or empty agent ID')
    def change(value):
        flow.require(replica not in value['authors'], 'Author already registered; a replica keeps one author context')
        value['authors'][replica] = agent_id
    update(root / 'coordinator/agents.json', change)
    return {'replica': replica, 'author': agent_id}


def run(root, replica, generator, stage, blender, timeout):
    author = author_actor(root, replica)
    session = root / mapping(root)['replicas'][replica]['session']
    generator = Path(generator).resolve(strict=True)
    flow.require(generator.is_relative_to((root / 'authors' / replica).resolve()), 'Generator must come from the replica workspace')
    command = [sys.executable, str(REPO / 'creation-lab/iterate.py'), 'run', '--session', str(session), '--generator', str(generator),
               '--stage', stage, '--blender', str(blender), '--timeout', str(timeout),
               '--actor-id', author['actorId'], '--model', author['model'], '--effort', author['reasoningEffort']]
    proc = subprocess.run(command, capture_output=True, text=True)
    result = json.loads(proc.stdout) if proc.stdout.strip().startswith('{') else {'error': proc.stderr.strip()}
    update(root / 'coordinator/runs.json', lambda value: value.setdefault(replica, []).append(
        {'at': now(), 'stage': stage, 'generator': str(generator), 'generatorSha256': digest(generator), **result}))
    return result


def latest_run(root, replica):
    session = root / mapping(root)['replicas'][replica]['session']
    runs = flow.load_runs(session)
    flow.require(runs, 'No runs yet')
    return session, runs[-1]


def packet(root, replica):
    session, (run_path, run) = latest_run(root, replica)
    flow.require(run['technical'] == 'PASS', 'Only technically passed runs with six renders go to visual review')
    template = flow.review_template(session, run['runId'])
    blind = secrets.token_hex(4)
    target = root / 'blind' / blind
    (target / 'renders').mkdir(parents=True)
    for view in VIEWS:
        shutil.copy2(run_path / 'renders' / (view + '.png'), target / 'renders' / (view + '.png'))
        flow.require(digest(target / 'renders' / (view + '.png')) == template['images'][view], 'Render copy differs')
    shutil.copy2(run_path / 'brief.json', target / 'brief.json')
    parts = read(run_path / 'parts.json')['parts']
    write(target / 'packet.json', {'blindId': blind, 'stage': run['stage'], 'reviewingSha256': digest(HERE / 'REVIEWING.md'),
                                   'checks': [c['check'] for c in template['checks']],
                                   'labels': [{'id': p['id'], 'label': p['label'], 'labelPositionBlender': p['positionBlender']} for p in parts]})
    update(root / 'coordinator/blind-map.json', lambda value: value.__setitem__(blind, {'replica': replica, 'runId': run['runId'], 'createdAt': now()}))
    return {'blindId': blind, 'packet': str(target), 'stage': run['stage']}


def ingest(root, blind, reviewer_id):
    entry = read(root / 'coordinator/blind-map.json')[blind]
    replica = entry['replica']
    session = root / mapping(root)['replicas'][replica]['session']
    run_path, run = flow.load_run(session, entry['runId'])
    raw = read(root / 'blind' / blind / 'review.json')
    flow.require(raw.get('blindId') == blind, 'Blind ID differs')
    template = flow.review_template(session, run['runId'])
    declared = raw.get('imageSha256', {})
    flow.require(declared == template['images'], 'Reviewer hashes differ from the run renders: ' + json.dumps(
        {v: (declared.get(v), template['images'][v]) for v in VIEWS if declared.get(v) != template['images'][v]}))
    review = {**template, 'reviewer': {**template['reviewer'], 'actorId': reviewer_id},
              'openedImages': raw.get('openedImages') is True, 'visual': raw['visual'], 'content': raw['content'],
              'parts': raw['parts'], 'checks': raw['checks'], 'defects': raw.get('defects', []),
              'scores': raw.get('scores'), 'blindId': blind, 'reviewerImageSha256': declared,
              'reviewPacketSha256': digest(root / 'blind' / blind / 'review.json')}
    if run['stage'] == 'detail':
        scores = review['scores']
        limits = {'biology': 30, 'readability': 25, 'composition': 15, 'shapeShading': 15, 'educationalUse': 15}
        flow.require(isinstance(scores, dict) and set(scores) == set(limits) and
                     all(type(scores[k]) in (int, float) and 0 <= scores[k] <= limits[k] for k in limits), 'Detail review needs rubric scores')
    result = flow.save_review(session, review)
    update(root / 'coordinator/agents.json', lambda value: value['reviewers'].__setitem__(blind, reviewer_id))
    return {**result, 'replica': replica, 'runId': run['runId'], 'status': flow.status(session)}


def lint_review(packet_dir):
    """Reviewer self-check using only the blind packet; mirrors iterate.py review rules."""
    packet_dir = Path(packet_dir).resolve(strict=True)
    info, review = read(packet_dir / 'packet.json'), read(packet_dir / 'review.json')
    errors = []
    def check(test, message):
        if not test:
            errors.append(message)
    check(review.get('blindId') == info['blindId'], 'blindId differs from packet.json')
    check(review.get('openedImages') is True, 'openedImages must be true after opening all six images')
    for view in VIEWS:
        image = packet_dir / 'renders' / (view + '.png')
        check(review.get('imageSha256', {}).get(view) == digest(image), 'imageSha256 differs for ' + view)
    for gate in ('visual', 'content'):
        item = review.get(gate, {})
        check(item.get('status') in flow.STATES and flow.nonempty(item.get('reason')), gate + ' needs status and reason')
    ids = [label['id'] for label in info['labels']]
    parts = review.get('parts', [])
    check([p.get('id') for p in parts] == ids or sorted(p.get('id') for p in parts) == sorted(ids), 'parts must list the 13 IDs once')
    for part in parts:
        check(part.get('visibility') in {'visible', 'hidden', 'unclear'} and flow.nonempty(part.get('reason')), 'visibility/reason for ' + str(part.get('id')))
        check(isinstance(part.get('views'), list) and part['views'] and set(part['views']) <= set(VIEWS), 'nonempty valid views for ' + str(part.get('id')))
    check([c.get('check') for c in review.get('checks', [])] == info['checks'], 'checks must match packet.json text and order')
    check(all(c.get('status') in flow.STATES and flow.nonempty(c.get('reason')) for c in review.get('checks', [])), 'each check needs status and reason')
    visible = all(p.get('visibility') == 'visible' for p in parts)
    if 'PASS' in (review.get('visual', {}).get('status'), review.get('content', {}).get('status')):
        check(visible, 'visual/content PASS requires all 13 parts visible')
    if review.get('content', {}).get('status') == 'PASS':
        check(all(c.get('status') == 'PASS' for c in review.get('checks', [])), 'content PASS requires every check PASS')
    defects = review.get('defects', [])
    check(all(d.get('view') in VIEWS and flow.nonempty(d.get('detail')) and flow.nonempty(d.get('requestedChange')) for d in defects), 'each defect needs view, detail, requestedChange')
    if any(review.get(g, {}).get('status') in {'FAIL', 'BLOCKED'} for g in ('visual', 'content')):
        check(bool(defects), 'FAIL/BLOCKED needs actionable defects')
    limits = {'biology': 30, 'readability': 25, 'composition': 15, 'shapeShading': 15, 'educationalUse': 15}
    scores = review.get('scores')
    if info['stage'] == 'detail':
        check(isinstance(scores, dict) and set(scores) == set(limits) and all(type(scores[k]) in (int, float) and 0 <= scores[k] <= limits[k] for k in limits), 'detail needs the five rubric scores within limits')
    else:
        check(scores is None, 'blockout uses scores null')
    return {'valid': not errors, 'errors': errors}


def feedback(root, replica):
    """Copy the replica's own renders and the observed defects/logs for its author."""
    session, (run_path, run) = latest_run(root, replica)
    target = root / 'authors' / replica / 'feedback' / run['runId']
    target.mkdir(parents=True, exist_ok=False)
    lines = [f'# Resultado de tu run {run["runId"]} ({run["stage"]})', '', f'Técnica: {run["technical"]}']
    if run.get('error'):
        lines.append(f'Error del runner: {run["error"]}')
    for step in ('build', 'reopen', 'reimport'):
        result = run_path / (step + '-result.json')
        if result.exists():
            value = read(result)
            failed = [c for c in value.get('checks', []) if c.get('pass') is False or c.get('status') == 'failed']
            lines.append(f'- {step}: {value["status"]}' + (f'; checks fallidos: {json.dumps(failed, ensure_ascii=False)[:1500]}' if failed else ''))
        elif (run_path / (step + '.log')).exists():
            tail = (run_path / (step + '.log')).read_text(encoding='utf-8', errors='replace').splitlines()[-25:]
            lines += [f'- {step}: sin resultado; final del log:', '```', *tail, '```']
    review = flow.get_review(session, read(session / 'session.json'), run_path, run)
    if review:
        lines += ['', f'Revisión visual: {review["visual"]["status"]} — {review["visual"]["reason"]}',
                  f'Revisión de contenido: {review["content"]["status"]} — {review["content"]["reason"]}', '', '## Partes no visibles o dudosas']
        lines += [f'- {p["id"]}: {p["visibility"]} ({", ".join(p["views"])}) — {p["reason"]}' for p in review['parts'] if p['visibility'] != 'visible'] or ['- ninguna']
        lines += ['', '## Checks']
        lines += [f'- [{c["status"]}] {c["check"]} — {c["reason"]}' for c in review['checks']]
        lines += ['', '## Defectos y cambios requeridos']
        lines += [f'- Vista `{d["view"]}`: {d["detail"]} → Cambio: {d["requestedChange"]}' for d in review['defects']] or ['- ninguno']
    if (run_path / 'renders').is_dir():
        (target / 'renders').mkdir()
        for image in sorted((run_path / 'renders').glob('*.png')):
            shutil.copy2(image, target / 'renders' / image.name)
        lines += ['', 'Tus renders están en `renders/` de esta carpeta.']
    lines += ['', 'Nota común del harness (enmienda v1.1, igual para todas las réplicas): la vista `wireframe` usa '
              'un alambre fijo del worker que apenas se ve a esta escala. No es un defecto tuyo ni puedes cambiarlo; '
              'ignora cualquier petición de rehacer esa vista.']
    lines += ['', f'Estado de la sesión: {json.dumps(flow.status(session), ensure_ascii=False)}']
    (target / 'FEEDBACK.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return {'feedback': str(target / 'FEEDBACK.md')}


# ---- runtime receipts -----------------------------------------------------

AUTHOR_READ = ('creation-lab/benchmarks/claude-animal-cell/AUTHORING.md', 'creation-lab/benchmarks/claude-animal-cell/brief.json',
               'creation-lab/components/', 'creation-lab/examples/component-demo.py',
               'creation-lab/scripts/iteration_worker.py', 'lab/scripts/creation_geometry.py')
FORBIDDEN_TOOLS = ('Agent', 'WebFetch', 'WebSearch', 'Skill')
FORBIDDEN_TEXT = ('animal-cell-20261022', '/sessions/', '/coordinator/', 'git log', 'git show', 'git diff', 'blender.exe', 'wsl-blender')


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def audit(calls, role, own, root):
    """Heuristic transcript audit; raw tool calls stay in the receipt for inspection."""
    flags = []
    local = str(root.resolve())
    allowed_dirs = [str(own.resolve())]
    if role == 'author':
        allowed_files = [str(REPO / p) for p in AUTHOR_READ]
    else:
        allowed_files = [str(HERE / 'REVIEWING.md'), str(HERE / 'bench.py')]
    for call in calls:
        name, inputs = call['tool'], call['input']
        text = ' '.join(strings(inputs))
        if name in FORBIDDEN_TOOLS or name.startswith('mcp__'):
            flags.append({'tool': name, 'reason': 'forbidden tool'})
        hits = [t for t in FORBIDDEN_TEXT if t in text]
        if role == 'reviewer':
            hits += [t for t in ('/authors/', '/blind/') if t in text and str(own.resolve()) not in text]
        if hits:
            flags.append({'tool': name, 'reason': 'forbidden reference ' + ','.join(hits), 'text': text[:300]})
        for path in re.findall(r'(/[\w./@+-]+)', text):
            if path.startswith(local) and not any(path.startswith(d) for d in allowed_dirs):
                flags.append({'tool': name, 'reason': 'path outside own workspace', 'path': path})
        if name in ('Read', 'Write', 'Edit') and isinstance(inputs.get('file_path'), str):
            path = str(Path(inputs['file_path']).resolve())
            if not any(path.startswith(d) for d in allowed_dirs) and not any(path.startswith(f) for f in allowed_files):
                flags.append({'tool': name, 'reason': 'file outside contract', 'path': path})
            if name != 'Read' and not any(path.startswith(d) for d in allowed_dirs):
                flags.append({'tool': name, 'reason': 'write outside workspace', 'path': path})
    return flags


def receipt(root, transcripts, agent_id, role, own, expected_model):
    base = Path(transcripts) / 'subagents'
    log, meta, prefix = (base / f'agent-{agent_id}{suffix}' for suffix in ('.jsonl', '.meta.json', '.prefix.json'))
    flow.require(log.is_file(), 'Transcript not found for ' + agent_id)
    models, efforts, usage, calls, times, messages = Counter(), Counter(), {}, [], [], {}
    segments, current = [], None
    for line in log.read_text(encoding='utf-8').splitlines():
        entry = json.loads(line)
        stamp = entry.get('timestamp')
        if entry.get('type') == 'user':
            content = entry.get('message', {}).get('content')
            is_result = isinstance(content, list) and any(isinstance(c, dict) and c.get('type') == 'tool_result' for c in content)
            if not is_result and not entry.get('isMeta'):
                current = {'start': stamp, 'end': stamp}
                segments.append(current)
        if entry.get('type') == 'assistant':
            message = entry['message']
            models[message.get('model')] += 1
            if entry.get('effort'):
                efforts[str(entry['effort'])] += 1
            key = message.get('id') or entry.get('requestId') or entry.get('uuid')
            messages[key] = message.get('model')
            if message.get('usage'):
                usage[key] = message['usage']
            for block in message.get('content', []):
                if block.get('type') == 'tool_use':
                    calls.append({'tool': block['name'], 'input': block.get('input', {}), 'at': stamp})
        if current and stamp:
            current['end'] = stamp
        if stamp:
            times.append(stamp)
    totals = Counter()
    for item in usage.values():
        for field in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens'):
            totals[field] += item.get(field) or 0
    def seconds(segment):
        return (datetime.fromisoformat(segment['end'].replace('Z', '+00:00')) - datetime.fromisoformat(segment['start'].replace('Z', '+00:00'))).total_seconds()
    flags = audit(calls, role, Path(own), root)
    resolved = set(messages.values())
    meta_value = read(meta) if meta.exists() else None
    prefix_value = read(prefix).get('state', {}) if prefix.exists() else {}
    contaminated = resolved != {expected_model} or prefix_value.get('model') not in (None, expected_model)
    return {'schemaVersion': 1, 'agentId': agent_id, 'role': role, 'expectedModel': expected_model,
            'requested': meta_value and {k: meta_value.get(k) for k in ('model', 'effort', 'agentType', 'description')},
            'runtimePrefix': {k: prefix_value.get(k) for k in ('model', 'effortValue', 'thinkingMode', 'buildVersion', 'fastMode')},
            'responseModels': dict(models), 'apiResponses': len(messages), 'entryEfforts': dict(efforts),
            'modelSwitchOrMismatch': contaminated, 'tokensObserved': dict(totals),
            'costObserved': 'NOT_AVAILABLE', 'activeSeconds': round(sum(seconds(s) for s in segments), 3),
            'segments': segments, 'toolCalls': len(calls), 'toolCounts': dict(Counter(c['tool'] for c in calls)),
            'auditFlags': flags, 'transcriptSha256': digest(log), 'generatedAt': now(),
            'evidence': 'Claude Code runtime transcript (message.model per API response, usage per response); coordinator-extracted'}


def receipts(root, transcripts):
    agents = read(root / 'coordinator/agents.json')
    reviewer = profile()['roles']['reviewer']['models'][0]
    out = root / 'coordinator/receipts'
    out.mkdir(exist_ok=True)
    result = {}
    for replica, agent in agents['authors'].items():
        condition = mapping(root)['replicas'][replica]['condition']
        model = profile()['conditions'][condition]['author']['models'][0]
        value = receipt(root, transcripts, agent, 'author', root / 'authors' / replica, model)
        result[agent] = {'role': 'author', 'replica': replica, 'flags': len(value['auditFlags']), 'contaminated': value['modelSwitchOrMismatch']}
        (out / f'author-{replica}.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for blind, agent in agents['reviewers'].items():
        value = receipt(root, transcripts, agent, 'reviewer', root / 'blind' / blind, reviewer)
        result[agent] = {'role': 'reviewer', 'blindId': blind, 'flags': len(value['auditFlags']), 'contaminated': value['modelSwitchOrMismatch']}
        (out / f'reviewer-{blind}.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('setup'); s.add_argument('--coordinator-id', required=True)
    s = sub.add_parser('register'); s.add_argument('--replica', required=True); s.add_argument('--agent-id', required=True)
    s = sub.add_parser('run'); s.add_argument('--replica', required=True); s.add_argument('--generator', required=True)
    s.add_argument('--stage', choices=['blockout', 'detail'], required=True); s.add_argument('--blender', required=True, type=Path)
    s.add_argument('--timeout', type=int, default=900)
    s = sub.add_parser('packet'); s.add_argument('--replica', required=True)
    s = sub.add_parser('ingest'); s.add_argument('--blind', required=True); s.add_argument('--reviewer-id', required=True)
    s = sub.add_parser('feedback'); s.add_argument('--replica', required=True)
    s = sub.add_parser('lint-review'); s.add_argument('--packet', required=True, type=Path)
    s = sub.add_parser('status')
    s = sub.add_parser('receipts'); s.add_argument('--transcripts', required=True, type=Path,
                                                  help='Claude Code session folder containing subagents/')
    args = p.parse_args(argv)
    root = args.root
    if args.command == 'setup':
        result = setup(root, args.coordinator_id)
    elif args.command == 'register':
        result = register(root, args.replica, args.agent_id)
    elif args.command == 'run':
        result = run(root, args.replica, args.generator, args.stage, args.blender, args.timeout)
    elif args.command == 'packet':
        result = packet(root, args.replica)
    elif args.command == 'ingest':
        result = ingest(root, args.blind, args.reviewer_id)
    elif args.command == 'feedback':
        result = feedback(root, args.replica)
    elif args.command == 'lint-review':
        result = lint_review(args.packet)
    elif args.command == 'receipts':
        result = receipts(root, args.transcripts)
    else:
        result = {r: flow.status(root / v['session']) for r, v in mapping(root)['replicas'].items()}
        for value in result.values():
            value.pop('session', None); value.pop('condition', None)  # keep status output blind-safe
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
