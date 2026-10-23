"""Read-only verification of locked prepared sources; no imports of upstream modules."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def verify(item):
    path = (ROOT / item['file']).resolve()
    if not path.is_relative_to(ROOT.resolve()) or path.is_symlink():
        raise ValueError('Source path outside repository or symlink')
    data = path.read_bytes()
    if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
        raise ValueError('Integrity mismatch: ' + item['file'])

def main():
    lock = json.loads((ROOT / 'creation-lab/sources.lock.json').read_text())
    count = 0
    for source in lock['sources']:
        verify(source['sourceManifest']); count += 1
        manifest = json.loads((ROOT / source['sourceManifest']['file']).read_text())
        for item in manifest.get('files', []) + manifest.get('archives', []):
            if 'file' in item:
                verify(item); count += 1
        for item in source.get('installedFiles', []):
            verify(item); count += 1
        for evidence in ['registrationEvidence', 'launcherProbeEvidence']:
            if source.get(evidence):
                verify(source[evidence]); count += 1
    for item in lock['licenses'] + lock['adapters'] + lock.get('installedAdapters', []) + lock.get('projectRuntimeFiles', []) + [lock['runtimeLock'], lock['runtimeRequirements']]:
        verify(item); count += 1
    print(json.dumps({'status': 'PASS', 'filesVerified': count, 'runtimeExecuted': False}))

if __name__ == '__main__': main()
