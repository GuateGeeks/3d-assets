"""Resolve the pinned upstream examples, verifying Git LFS object hashes when needed."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / 'lab/.local'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    profile = json.loads((ROOT / 'lab/envs/unirig.profile.json').read_text())
    repo = LOCAL / 'repos/UniRig'
    entries = []
    for source, name in [('examples/giraffe.glb', 'giraffe.glb'),
                         ('examples/skeleton/giraffe.fbx', 'giraffe-reviewed.fbx')]:
        path = repo / source
        target = LOCAL / 'examples/UniRig' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        head = path.read_bytes()[:1024]
        pointer = head.startswith(b'version https://git-lfs.github.com/spec/v1')
        if pointer:
            values = dict(line.split(' ', 1) for line in head.decode().strip().splitlines())
            expected = values['oid'].removeprefix('sha256:')
            expected_size = int(values['size'])
            url = f"https://media.githubusercontent.com/media/VAST-AI-Research/UniRig/{profile['commit']}/{source}"
            if not target.exists() or digest(target) != expected:
                partial = target.with_suffix(target.suffix + '.partial')
                with urllib.request.urlopen(url, timeout=120) as response, partial.open('wb') as output:
                    shutil.copyfileobj(response, output)
                if partial.stat().st_size != expected_size or digest(partial) != expected:
                    raise RuntimeError('LFS example checksum mismatch: ' + source)
                os.replace(partial, target)
        else:
            expected = digest(path)
            if not target.exists() or digest(target) != expected:
                shutil.copy2(path, target)
        entries.append({'source': source, 'file': str(target.relative_to(LOCAL)),
                        'sha256': digest(target), 'bytes': target.stat().st_size, 'gitLfs': pointer})
    report = {'repository': profile['repository'], 'commit': profile['commit'], 'files': entries, 'status': 'passed'}
    output = ROOT / 'lab/reports/unirig-examples.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print('Pinned giraffe examples available with verified hashes.')


if __name__ == '__main__':
    main()
