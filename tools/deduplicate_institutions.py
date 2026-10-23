"""Compare selected native GLBs against every catalog asset, including Draco."""
import argparse
import json
import subprocess
from pathlib import Path

from acquire_institutions import ROOT, read, save, sha
from geometry_fingerprint import document, fingerprint


def compare(run, node):
    baseline = read(run / 'baseline-index.json')['models']
    cache = {}
    previous = ROOT / 'enrichment/staging/polyhaven-20261022/baseline-fingerprints.json'
    if previous.exists():
        cache.update(read(previous))
    current = run / 'geometry-cache.json'
    if current.exists():
        cache.update(read(current))

    def native(path, digest):
        if digest not in cache:
            raw = path.read_bytes()
            doc, _ = document(raw)
            compressed = 'KHR_draco_mesh_compression' in doc.get('extensionsUsed', [])
            decoded = None
            if compressed:
                result = subprocess.run([node, str(ROOT / 'tools/decode_geometry.cjs'), str(path)],
                                        capture_output=True, check=True, text=True)
                decoded = json.loads(result.stdout)
            cache[digest] = fingerprint(raw, decoded)
            save(current, cache)
        return cache[digest]

    for model in baseline:
        native(ROOT / model['file'], model['sha256'])
    rows = []
    for item in read(run / 'acquisition.json')['items']:
        path = run / 'prepared' / item['id'] / 'model.glb'
        digest = sha(path)
        value = native(path, digest)
        rows.append({'id': item['id'], 'sha256': digest, 'geometryFingerprint': value,
                     'exactMatches': [m['id'] for m in baseline if m['sha256'] == digest],
                     'geometryMatches': [m['id'] for m in baseline if cache[m['sha256']]['sha256'] == value['sha256']]})
        print('COMPARED', item['id'], value['triangles'], flush=True)
    for row in rows:
        row['exactPeerMatches'] = [other['id'] for other in rows if other['id'] != row['id'] and other['sha256'] == row['sha256']]
        row['geometryPeerMatches'] = [other['id'] for other in rows if other['id'] != row['id'] and other['geometryFingerprint']['sha256'] == row['geometryFingerprint']['sha256']]
    save(run / 'deduplication.json', {'baselineModels': len(baseline), 'baselineFingerprintCount': len(baseline),
         'comparisons': rows, 'unsupported': [],
         'methodNote': 'Native GLB SHA-256 plus triangle-edge-distribution-v1; Draco decoded locally with Google Draco 1.5.6 without modifying source bytes. Geometry matches need individual review; nonmatches do not exclude semantic variants.'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--node', required=True)
    args = parser.parse_args()
    compare(args.run, args.node)
