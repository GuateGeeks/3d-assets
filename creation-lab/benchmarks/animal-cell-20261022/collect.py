"""Collect verified immutable runs and separate human-readable benchmark evidence."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUTPUT = BASE.parents[1] / '.local/benchmarks/animal-cell-20261022'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def status(value):
    return value.get('status','NOT_RUN') if isinstance(value,dict) else value


def main():
    protocol = read(BASE / 'protocol.json')
    formats = read(BASE / 'format-validation.json')['entries'] if (BASE / 'format-validation.json').exists() else []
    entries, history, reviews = [], [], []
    for condition in protocol['conditions']:
        ident = condition['id']
        runs = sorted((OUTPUT / ident).glob('*/manifest.json'))
        selected = None
        for manifest_path in runs:
            run = manifest_path.parent
            manifest = read(manifest_path)
            integrity = (run / 'COMPLETE').read_text().strip() == sha(manifest_path)
            issues = []
            for name, expected in manifest['artifacts'].items():
                file = run / name
                if not file.is_file() or sha(file) != expected:
                    issues.append(name)
            integrity = integrity and not issues
            if not integrity:
                raise ValueError(f'Changed run evidence: {run}: {issues}')
            history.append({'id':ident, 'runId':run.name, 'attempt':manifest['attempt'],
                            'technical':manifest['technical'], 'seconds':manifest['seconds'],
                            'integrity':'PASS', 'error':manifest.get('error'),
                            'generatorSha256':manifest['generatorSha256']})
            if (run / 'asset.glb').exists() and (run / 'parts.json').exists():
                selected = (run, manifest)
        if selected is None:
            entries.append({**condition, 'technical':'BLOCKED', 'reason':'No complete asset'})
            continue
        run, manifest = selected
        checks = read(run / 'build-checks.json')
        metrics = checks['metrics']
        review_path = BASE / 'reviews-blind' / (ident + '.json')
        review = read(review_path) if review_path.exists() else None
        if review and review['runId'] != run.name:
            raise ValueError(f'Review run differs for {ident}')
        if review:
            for image in review['imageEvidence']:
                if sha(run / 'renders' / (image['view']+'.png')) != image['sha256']:
                    raise ValueError(f'Reviewed image changed for {ident}: {image["view"]}')
            reviews.append({**review, 'visual':status(review['visual']),
                            'biological':status(review['biological']),
                            'visualDetail':review['visual'], 'biologicalDetail':review['biological']})
        fmt = next((v for v in formats if v['id']==ident and v['runId']==run.name), None)
        entry = {**condition, 'runId':run.name, 'attempt':manifest['attempt'],
                 'generatorSha256':manifest['generatorSha256'], 'manifestSha256':sha(run/'manifest.json'),
                 'technical':manifest['technical'], 'seconds':manifest['seconds'],
                 'triangles':metrics['triangles'], 'meshObjects':metrics['meshes'],
                 'materials':len(metrics['materials']), 'dimensionsM':metrics['dimensionsM'],
                 'glbBytes':(run/'asset.glb').stat().st_size, 'glbSha256':sha(run/'asset.glb'),
                 'format':{'status':fmt['status'], 'errors':fmt['report']['issues']['numErrors'],
                           'warnings':fmt['report']['issues']['numWarnings']} if fmt else {'status':'NOT_RUN'},
                 'visual':status(review['visual']) if review else 'NOT_RUN',
                 'biological':status(review['biological']) if review else 'NOT_RUN',
                 'score':review['score'] if review else None,
                 'artifactDirectory':str(run.relative_to(BASE.parents[2])).replace('\\','/')}
        entries.append(entry)
    result = {'schemaVersion':1,'recordedAt':datetime.now(timezone.utc).isoformat(),
              'scope':'single-brief pilot, n=1 per condition; no statistical inference',
              'entries':entries, 'executionHistory':history}
    save(BASE / 'results.json', result)
    save(BASE / 'reviews.json', {'schemaVersion':1, 'entries':reviews})
    print(json.dumps(entries, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
