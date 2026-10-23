"""Collect verified immutable runs and separate human-readable benchmark evidence."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from benchmark_io import contained_file, new_report_dir, write_new_json, review_matches_run

BASE = Path(__file__).resolve().parent
OUTPUT = BASE.parents[1] / '.local/benchmarks/animal-cell-20261022'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def status(value):
    return value.get('status','NOT_RUN') if isinstance(value,dict) else value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=Path, default=OUTPUT)
    parser.add_argument('--report-dir', type=Path, default=None, help='New report folder; existing report files are never overwritten')
    parser.add_argument('--format-report', type=Path, default=BASE/'format-validation.json')
    parser.add_argument('--reviews', type=Path, default=BASE/'reviews-blind', help='Per-condition reviews; apply only to the exact reviewed run')
    args = parser.parse_args(argv)
    output = args.runs.resolve()
    report_dir = args.report_dir or new_report_dir()
    if any((report_dir/name).exists() for name in ('results.json', 'reviews.json')):
        parser.error('Report files already exist; choose a new --report-dir')
    protocol = read(BASE / 'protocol.json')
    formats = read(args.format_report)['entries'] if args.format_report.exists() else []
    entries, history, reviews = [], [], []
    for condition in protocol['conditions']:
        ident = condition['id']
        runs = sorted((output / ident).glob('*/manifest.json'))
        selected = None
        for manifest_path in runs:
            run = manifest_path.parent
            if not (run/'COMPLETE').is_file():
                continue  # A running or interrupted process is not a completed result.
            manifest = read(manifest_path)
            integrity = (run / 'COMPLETE').read_text().strip() == sha(manifest_path)
            issues = []
            for name, expected in manifest['artifacts'].items():
                try:
                    file = contained_file(run, name)
                except ValueError:
                    issues.append(name)
                    continue
                if sha(file) != expected:
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
        review_path = args.reviews / (ident + '.json')
        review = read(review_path) if review_path.exists() else None
        if not review_matches_run(run, review, manifest):
            review = None  # Absent, stale or incomplete reviews never become current scores.
        if review:
            reviews.append({**review, 'visual':status(review['visual']),
                            'biological':status(review['biological']),
                            'visualDetail':review['visual'], 'biologicalDetail':review['biological']})
        glb_sha = sha(run/'asset.glb')
        fmt = next((v for v in formats if v['id']==ident and v['runId']==run.name and v.get('sha256')==glb_sha), None)
        entry = {**condition, 'runId':run.name, 'attempt':manifest['attempt'],
                 'generatorSha256':manifest['generatorSha256'], 'manifestSha256':sha(run/'manifest.json'),
                 'technical':manifest['technical'], 'seconds':manifest['seconds'],
                 'triangles':metrics['triangles'], 'meshObjects':metrics['meshes'],
                 'materials':len(metrics['materials']), 'dimensionsM':metrics['dimensionsM'],
                 'glbBytes':(run/'asset.glb').stat().st_size, 'glbSha256':glb_sha,
                 'format':{'status':fmt['status'], 'errors':fmt['report']['issues']['numErrors'],
                           'warnings':fmt['report']['issues']['numWarnings']} if fmt else {'status':'NOT_RUN'},
                 'visual':status(review['visual']) if review else 'NOT_RUN',
                 'biological':status(review['biological']) if review else 'NOT_RUN',
                 'score':review['score'] if review else None,
                 'artifactDirectory':str(run.relative_to(BASE.parents[2])).replace('\\','/') if run.is_relative_to(BASE.parents[2]) else str(run),
                 'runDirectory':run.relative_to(output).as_posix()}
        entries.append(entry)
    result = {'schemaVersion':1,'recordedAt':datetime.now(timezone.utc).isoformat(),
              'scope':'single-brief pilot, n=1 per condition; no statistical inference',
              'entries':entries, 'executionHistory':history}
    write_new_json(report_dir / 'results.json', result)
    write_new_json(report_dir / 'reviews.json', {'schemaVersion':1, 'entries':reviews})
    print(json.dumps({'reportDirectory':str(report_dir.resolve()),'entries':entries}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
