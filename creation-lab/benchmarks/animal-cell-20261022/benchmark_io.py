"""Portable paths and immutable-report helpers for this benchmark."""
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
RUNS = ROOT / 'creation-lab' / '.local' / 'benchmarks' / BASE.name
REVIEW_VIEWS = {'front', 'side', 'back', 'three-quarter', 'wireframe', 'reimport-three-quarter'}


def new_report_dir():
    return RUNS / 'reports' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])


def contained_file(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f'Missing or unsafe artifact: {relative}')
    return path


def read_complete_manifest(run):
    """Check completion identity, not the contents of every large artifact."""
    try:
        manifest = contained_file(run, 'manifest.json')
        marker = contained_file(run, 'COMPLETE').read_text(encoding='utf-8').strip()
        if marker != hashlib.sha256(manifest.read_bytes()).hexdigest():
            return None
        value = json.loads(manifest.read_text(encoding='utf-8-sig'))
        if value.get('status') == 'RUNNING' or value.get('runId') != Path(run).name:
            return None
        return value
    except (OSError, ValueError, TypeError):
        return None


def write_new_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def review_matches_run(run, review, manifest=None):
    """A score belongs to one completed artifact and six unchanged reviewed views."""
    if not isinstance(review, dict) or review.get('runId') != Path(run).name:
        return False
    evidence = review.get('imageEvidence')
    if not isinstance(evidence, list) or len(evidence) != len(REVIEW_VIEWS):
        return False
    if not all(isinstance(item, dict) and isinstance(item.get('view'), str) for item in evidence):
        return False
    if {item.get('view') for item in evidence} != REVIEW_VIEWS:
        return False
    manifest = manifest or read_complete_manifest(run)
    if not isinstance(manifest, dict) or not isinstance(manifest.get('artifacts'), dict):
        return False
    try:
        for image in evidence:
            name = f'renders/{image["view"]}.png'
            expected = image.get('sha256')
            if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
                return False
            if manifest['artifacts'].get(name) != expected:
                return False
            if hashlib.sha256(contained_file(run, name).read_bytes()).hexdigest() != expected:
                return False
        # Do not display an image review beside a substituted GLB or part labels.
        for name in ('asset.glb', 'parts.json'):
            if hashlib.sha256(contained_file(run, name).read_bytes()).hexdigest() != manifest['artifacts'].get(name):
                return False
    except (OSError, ValueError, TypeError):
        return False
    return True
