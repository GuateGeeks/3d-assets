"""Capture immutable historical runs into deterministic, verified ZIP fixtures."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import stat
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from restore import DEFAULT_OUTPUT, RUN_ID, safe_name, sha256, verify_archive


def capture(source: Path, destination: Path) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    entries = []
    for condition in 'ABCDEF':
        for run in sorted((source / condition).iterdir()):
            if not run.is_dir() or not RUN_ID.fullmatch(run.name):
                continue
            if run.is_symlink():
                raise ValueError(f'Symlink run: {run}')
            manifest_path = run / 'manifest.json'
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            buffer = io.BytesIO()
            total_size = 0
            count = 0
            with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for path in sorted(run.rglob('*')):
                    if path.is_symlink():
                        raise ValueError(f'Symlink source: {path}')
                    if not path.is_file():
                        continue
                    name = path.relative_to(run).as_posix()
                    safe_name(name)
                    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.create_system = 3
                    info.external_attr = (stat.S_IFREG | 0o644) << 16
                    data = path.read_bytes()
                    archive.writestr(info, data, compresslevel=6)
                    total_size += len(data)
                    count += 1
            data = buffer.getvalue()
            if len(data) >= 100 * 1024 * 1024:
                raise ValueError(f'Fixture exceeds GitHub file limit: {run}')
            entry = {'condition': condition, 'runId': run.name,
                     'file': f'{condition}-{run.name}.zip', 'sha256': hashlib.sha256(data).hexdigest(),
                     'bytes': len(data), 'uncompressedBytes': total_size, 'fileCount': count,
                     'manifestSha256': sha256(manifest_path), 'complete': (run / 'COMPLETE').is_file(),
                     'historicalStatus': manifest.get('status'), 'historicalTechnical': manifest.get('technical')}
            output = destination / entry['file']
            if output.exists():
                if sha256(output) != entry['sha256']:
                    raise ValueError(f'Refusing to replace different fixture: {output}')
            else:
                with output.open('xb') as stream:
                    stream.write(data)
            verify_archive(destination, entry)
            entries.append(entry)
    if not entries:
        raise ValueError('No historical runs found')
    index = {'schemaVersion': 1, 'benchmarkId': 'animal-cell-20261022',
             'description': 'Original run evidence, including failed initial attempts; no regeneration or promotion.',
             'runs': entries}
    encoded = (json.dumps(index, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    index_path = destination / 'index.json'
    if index_path.exists():
        if index_path.read_bytes() != encoded:
            raise ValueError('Refusing to replace a different fixture index')
    else:
        with index_path.open('xb') as stream:
            stream.write(encoded)
    return {'status': 'PASS', 'runs': len(entries), 'files': sum(e['fileCount'] for e in entries),
            'compressedBytes': sum(e['bytes'] for e in entries),
            'uncompressedBytes': sum(e['uncompressedBytes'] for e in entries),
            'largestArchiveBytes': max(e['bytes'] for e in entries), 'indexSha256': sha256(index_path)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(capture(args.source, args.output), indent=2))
