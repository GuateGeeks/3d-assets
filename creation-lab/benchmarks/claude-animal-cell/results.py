"""Collect results.json for the Claude animal-cell benchmark from sealed evidence.

Reads iterate.py sessions (validated through iterate.load_runs), coordinator
registries and receipts-v2. Writes nothing into runs. The family mapping is
revealed here only after every review has been stored.
Usage: results.py --root BATCH --output results.json
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('bench', HERE / 'bench.py')
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)
flow, read = bench.flow, bench.read
SCORES = ('biology', 'readability', 'composition', 'shapeShading', 'educationalUse')


def run_record(session, run_path, run, review, blind_by_run, reviewers, authored):
    checks = {c['name']: c for c in read(run_path / 'build-checks.json')['checks']} if (run_path / 'build-checks.json').exists() else {}
    glb = run_path / 'asset.glb'
    blind = blind_by_run.get(run['runId'])
    scores = review.get('scores') if review else None
    return {'runId': run['runId'], 'stage': run['stage'], 'sequence': run['sequence'],
            'authorFile': authored.get(run['runId']),
            'generatorSha256': run['artifacts'].get('generator.py'), 'technical': run['technical'],
            'visual': review['visual']['status'] if review else 'NOT_RUN', 'content': review['content']['status'] if review else 'NOT_RUN',
            'partsNotVisible': [p['id'] for p in review['parts'] if p['visibility'] != 'visible'] if review else None,
            'checks': {c['check'][:60]: c['status'] for c in review['checks']} if review else None,
            'defects': len(review['defects']) if review else None,
            'scores': scores, 'scoreTotal': sum(scores[k] for k in SCORES) if scores else None,
            'triangles': checks.get('triangle-budget', {}).get('actual'), 'materials': checks.get('material-budget', {}).get('actual'),
            'meshObjects': checks.get('object-budget', {}).get('actual'), 'dimensionsM': checks.get('display-size', {}).get('actual'),
            'glbBytes': glb.stat().st_size if glb.exists() else None, 'glbSha256': run['artifacts'].get('asset.glb'),
            'blenderSeconds': round(sum(s['seconds'] for s in run['stages']), 3), 'blenderStages': {s['step']: s['seconds'] for s in run['stages']},
            'blindId': blind, 'reviewer': reviewers.get(blind), 'manifestSha256': flow.digest(run_path / 'manifest.json'),
            'reviewSha256': flow.digest(session / 'reviews' / (run['runId'] + '.json')) if review else None}


def summary(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return {'n': len(values), 'mean': round(statistics.mean(values), 2), 'min': min(values), 'max': max(values),
            'sd': round(statistics.stdev(values), 2) if len(values) > 1 else None}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=bench.DEFAULT_ROOT)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    root = args.root
    mapping = bench.mapping(root)['replicas']
    agents = read(root / 'coordinator/agents.json')
    blind_map = read(root / 'coordinator/blind-map.json')
    blind_by_run = {v['runId']: k for k, v in blind_map.items() if (root / 'blind' / k / 'review.json').exists()}
    receipts = root / 'coordinator/receipts-v2'
    authored = {x['runId']: Path(x['generator']).name for v in read(root / 'coordinator/runs.json').values() for x in v if x.get('runId')}
    replicas, families = {}, defaultdict(list)
    for replica, info in sorted(mapping.items()):
        session = root / info['session']
        state = flow.status(session)
        session_value = read(session / 'session.json')
        runs = []
        for run_path, run in flow.load_runs(session):
            review = flow.get_review(session, session_value, run_path, run)
            runs.append(run_record(session, run_path, run, review, blind_by_run, agents['reviewers'], authored))
        blockouts = [r for r in runs if r['stage'] == 'blockout']
        details = [r for r in runs if r['stage'] == 'detail']
        passed = lambda r: r['technical'] == 'PASS' and r['visual'] == 'PASS' and r['content'] == 'PASS'
        receipt_file = receipts / f'author-{replica}.json'
        receipt = read(receipt_file) if receipt_file.exists() else {}
        final = runs[-1] if runs else None
        record = {'replica': replica, 'family': info['condition'], 'authoring': info['authoring'],
                  'authorAgent': agents['authors'].get(replica), 'finalStatus': state['status'], 'next': state['next'],
                  'correctionsUsed': state.get('correctionsUsed'), 'runs': runs,
                  'firstBlockoutAccepted': passed(blockouts[0]) if blockouts else None,
                  'blockoutAttempts': len(blockouts), 'firstDetailAccepted': passed(details[0]) if details else None,
                  'detailAttempts': len(details), 'finalScore': final['scoreTotal'] if final and state['status'] == 'PASS' else None,
                  'lastDetailScore': details[-1]['scoreTotal'] if details else None,
                  'finalAsset': {k: final[k] for k in ('triangles', 'materials', 'meshObjects', 'glbBytes', 'dimensionsM')} if final else None,
                  'blenderSecondsTotal': round(sum(r['blenderSeconds'] for r in runs), 3),
                  'author': {'responseModels': receipt.get('responseModels'), 'modelSwitchOrMismatch': receipt.get('modelSwitchOrMismatch'),
                             'effort': (receipt.get('runtimePrefix') or {}).get('effortValue'), 'requested': receipt.get('requested'),
                             'activeSeconds': receipt.get('activeSecondsV2'), 'apiMessages': receipt.get('apiMessages'),
                             'tokensMaxPerMessage': receipt.get('tokensMaxPerMessage'), 'outputTokensLowerBound': receipt.get('outputTokensLowerBound'),
                             'auditFlags': len(receipt.get('auditFlags', [])), 'scratchpadReferences': len(receipt.get('scratchpadReferences', [])),
                             'costObserved': 'NOT_AVAILABLE'}}
        replicas[replica] = record
        families[info['condition']].append(record)
    aggregates = {}
    for family, items in sorted(families.items()):
        aggregates[family] = {
            'replicas': [r['replica'] for r in items],
            'finalPass': sum(r['finalStatus'] == 'PASS' for r in items),
            'firstBlockoutAccepted': sum(bool(r['firstBlockoutAccepted']) for r in items),
            'reachedDetail': sum(r['detailAttempts'] > 0 for r in items),
            'firstDetailAccepted': sum(bool(r['firstDetailAccepted']) for r in items),
            'correctionsUsed': summary([r['correctionsUsed'] for r in items]),
            'finalScore': summary([r['finalScore'] for r in items]),
            'lastDetailScore': summary([r['lastDetailScore'] for r in items]),
            'finalTriangles': summary([(r['finalAsset'] or {}).get('triangles') for r in items]),
            'finalGlbBytes': summary([(r['finalAsset'] or {}).get('glbBytes') for r in items]),
            'authorActiveSeconds': summary([r['author']['activeSeconds'] for r in items]),
            'authorOutputTokensLowerBound': summary([r['author']['outputTokensLowerBound'] for r in items]),
            'blenderSeconds': summary([r['blenderSecondsTotal'] for r in items])}
    reviewer_receipts = [read(f) for f in sorted(receipts.glob('reviewer-*.json'))]
    result = {'schemaVersion': 1, 'protocol': 'claude-animal-cell-v1', 'generatedAt': datetime.now(timezone.utc).isoformat(),
              'protocolSha256': flow.digest(HERE / 'protocol.json'), 'replicas': replicas, 'families': aggregates,
              'review': {'reviews': len(reviewer_receipts), 'models': sorted({m for r in reviewer_receipts for m in r['responseModels']}),
                         'activeSeconds': summary([r.get('activeSecondsV2') for r in reviewer_receipts]),
                         'outputTokensLowerBound': summary([r.get('outputTokensLowerBound') for r in reviewer_receipts]),
                         'auditFlags': sum(len(r['auditFlags']) for r in reviewer_receipts),
                         'modelSwitchOrMismatch': sum(bool(r['modelSwitchOrMismatch']) for r in reviewer_receipts)},
              'coordination': {'model': 'claude-opus-5-5', 'effort': 'high', 'tokens': 'NOT_AVAILABLE separately (main session transcript mixes setup, tooling and coordination)'},
              'telemetry': {'cost': 'NOT_AVAILABLE', 'tokens': 'lower bounds from transcripts (amendment 1.5)',
                            'blenderSeconds': 'build+reopen(render)+reimport per run; not model latency'}}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(aggregates, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
