"""Acquire a reviewed Poly Haven selection, preserve source bytes, and package glTF.

The gallery never calls the API. Acquisition uses an identifying User-Agent,
cached metadata, sequential requests, checksums and bounded retries. Promotion
is offline and requires technical, visual and duplicate-review evidence.
"""
import argparse
import base64
import copy
import hashlib
import json
import mimetypes
import shutil
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from catalog import inspect, license_info
from geometry_fingerprint import document, fingerprint

ROOT = Path(__file__).resolve().parents[1]
AGENT = 'GuateGeeks-3D-Assets/1.0 (https://guategeeks.com/3d-assets/)'
LICENSE_URL = 'https://creativecommons.org/publicdomain/zero/1.0/'
MAX_BYTES = 25 * 1024 ** 2


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(root, relative):
    relative = urllib.parse.unquote(relative)
    path = PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or '\\' in relative or ':' in relative:
        raise ValueError('Unsafe component path: ' + relative)
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('Component outside source folder')
    return target


def download(url, target, expected=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in {
        'api.polyhaven.com', 'dl.polyhaven.org', 'polyhaven.com', 'raw.githubusercontent.com'
    }:
        raise ValueError('Unexpected acquisition host')
    if target.exists():
        raw = target.read_bytes()
    else:
        for attempt in range(6):
            try:
                request = urllib.request.Request(url, headers={
                    'User-Agent': AGENT, 'Referer': 'https://guategeeks.com/3d-assets/'
                })
                with urllib.request.urlopen(request, timeout=90) as response:
                    raw = response.read(64 * 1024 ** 2 + 1)
                if len(raw) > 64 * 1024 ** 2:
                    raise ValueError('Source component exceeds acquisition budget')
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + '.part')
                temporary.write_bytes(raw)
                temporary.replace(target)
                break
            except urllib.error.HTTPError as error:
                if error.code not in {429, 500, 502, 503, 504} or attempt == 5:
                    raise
                delay = error.headers.get('Retry-After', '')
                time.sleep(min(30, int(delay)) if delay.isdigit() else min(30, 2 ** attempt))
            except urllib.error.URLError:
                if attempt == 5:
                    raise
                time.sleep(min(30, 2 ** attempt))
        time.sleep(.15)
    if expected and (len(raw) != expected['size'] or hashlib.md5(raw).hexdigest() != expected['md5']):
        raise ValueError('API size/MD5 mismatch: ' + target.name)
    return raw


def acquire(run):
    run.mkdir(parents=True, exist_ok=True)
    selection = read(ROOT / 'enrichment/polyhaven-selection.json')
    if not (run / 'baseline-index.json').exists():
        shutil.copyfile(ROOT / 'index.json', run / 'baseline-index.json')
        save(run / 'original-inventory.json', {
            p.relative_to(ROOT).as_posix(): sha(p)
            for p in (ROOT / 'models').rglob('*') if p.is_file()
        })
        before = run / 'before'
        for name in ['README.md', 'LICENSE.md', 'COVERAGE.md', 'coverage.json', 'gallery.html',
                     'gallery/app.js', 'tools/reindex.py', 'tools/build_site.py', 'tools/check_site.py',
                     'enrichment/providers.json', 'enrichment/README.md']:
            target = before / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
    assets = json.loads(download('https://api.polyhaven.com/assets?type=models', run / 'assets.json'))
    items, held = [], []
    for proposal in selection['items']:
        asset = proposal['asset']
        meta = assets[asset]
        manifest = json.loads(download('https://api.polyhaven.com/files/' + asset, run / ('files-' + asset + '.json')))
        formats = manifest.get('gltf', {})
        if not formats:
            held.append({'asset': asset, 'reason': 'No native glTF package'})
            continue
        resolution = '1k' if '1k' in formats else min(formats, key=lambda x: int(x[:-1]))
        package = formats[resolution]['gltf']
        entries = {PurePosixPath(urllib.parse.urlsplit(package['url']).path).name: package,
                   **package.get('include', {})}
        total = sum(entry['size'] for entry in entries.values())
        if total > MAX_BYTES - 65536:
            held.append({'asset': asset, 'reason': 'Native package exceeds 25 MiB web budget', 'bytes': total})
            continue
        original = run / 'downloads' / asset
        files = []
        for relative, entry in entries.items():
            target = safe_path(original, relative)
            download(entry['url'], target, entry)
            files.append({'file': relative, 'url': entry['url'], 'bytes': target.stat().st_size,
                          'md5': entry['md5'], 'sha256': sha(target)})
        entry_name = next(iter(entries))
        source_doc = read(original / entry_name)
        for group in ['buffers', 'images']:
            for component in source_doc.get(group, []):
                uri = component.get('uri')
                if uri and not uri.startswith('data:') and not safe_path(original, uri).is_file():
                    raise ValueError('Unresolved native dependency: ' + asset + '/' + uri)
        item = {**proposal, 'id': 'polyhaven-' + asset.lower().replace('_', '-'),
                'resolution': resolution, 'metadata': meta, 'files': files,
                'input': str(original / entry_name), 'entryFile': entry_name,
                'retrievedAt': datetime.now(timezone.utc).isoformat()}
        items.append(item)
        save(run / 'acquisition.json', {'provider': 'Poly Haven', 'agent': AGENT, 'items': items, 'held': held})
        print('ACQUIRED', asset, resolution, round(total / 1024 ** 2, 2), 'MiB', flush=True)


def pack(run):
    for item in read(run / 'acquisition.json')['items']:
        folder = run / 'downloads' / item['asset']
        source = read(folder / item['entryFile'])
        doc = copy.deepcopy(source)
        blob = bytearray()
        offsets = []
        def append(raw):
            blob.extend(b'\0' * (-len(blob) % 4))
            offset = len(blob)
            blob.extend(raw)
            return offset
        def component(uri):
            if uri.startswith('data:'):
                return base64.b64decode(uri.split(',', 1)[1])
            return safe_path(folder, uri).read_bytes()
        for buffer in source['buffers']:
            raw = component(buffer['uri'])
            if len(raw) < buffer['byteLength']:
                raise ValueError('Truncated source buffer')
            offsets.append(append(raw))
        for view in doc.get('bufferViews', []):
            view['byteOffset'] = offsets[view.get('buffer', 0)] + view.get('byteOffset', 0)
            view['buffer'] = 0
        for image in doc.get('images', []):
            if 'uri' not in image:
                continue
            uri = image.pop('uri')
            raw = component(uri)
            offset = append(raw)
            view_id = len(doc.setdefault('bufferViews', []))
            doc['bufferViews'].append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(raw)})
            image['bufferView'] = view_id
            image['mimeType'] = 'image/png' if raw.startswith(b'\x89PNG') else 'image/jpeg' if raw.startswith(b'\xff\xd8') else mimetypes.guess_type(uri)[0]
            if image['mimeType'] not in {'image/png', 'image/jpeg'}:
                raise ValueError('Unsupported image type')
        doc['buffers'] = [{'byteLength': len(blob)}]
        encoded = json.dumps(doc, ensure_ascii=False, separators=(',', ':')).encode()
        encoded += b' ' * (-len(encoded) % 4)
        blob.extend(b'\0' * (-len(blob) % 4))
        result = struct.pack('<III', 0x46546c67, 2, 28 + len(encoded) + len(blob))
        result += struct.pack('<II', len(encoded), 0x4e4f534a) + encoded
        result += struct.pack('<II', len(blob), 0x004e4942) + blob
        if len(result) > MAX_BYTES or not inspect(result)['selfContained']:
            raise ValueError('Prepared GLB exceeds web budget or has dependencies')
        # Byte-for-byte comparison of every source geometry view, not a visual approximation.
        for old, new in zip(source.get('bufferViews', []), doc.get('bufferViews', [])):
            raw = component(source['buffers'][old.get('buffer', 0)]['uri'])
            start = old.get('byteOffset', 0)
            assert raw[start:start + old['byteLength']] == blob[new['byteOffset']:new['byteOffset'] + new['byteLength']]
        for key in ['meshes', 'nodes', 'scenes', 'scene', 'accessors', 'materials', 'textures', 'samplers', 'skins', 'animations']:
            assert source.get(key) == doc.get(key), 'Source structure changed: ' + key
        output = run / 'prepared' / item['id']
        output.mkdir(parents=True, exist_ok=True)
        if (output / 'model.glb').exists() and (output / 'model.glb').read_bytes() != result:
            raise ValueError('Prepared model changed; use a new run for corrected evidence')
        (output / 'model.glb').write_bytes(result)
        save(output / 'preparation.json', {'id': item['id'], 'glbSha256': sha(output / 'model.glb'),
             'sourceGeometryViewsByteIdentical': True, 'sourceSceneAndMaterialsUnchanged': True,
             'scaleChange': False, 'geometryFingerprint': fingerprint(result)})
        print('PACKED', item['id'], len(result), flush=True)


def deduplicate(run):
    baseline = read(run / 'baseline-index.json')['models']
    cache = run / 'baseline-fingerprints.json'
    values = read(cache) if cache.exists() else {}
    for model in baseline:
        if model['sha256'] not in values:
            values[model['sha256']] = fingerprint((ROOT / model['file']).read_bytes())
    save(cache, values)
    comparisons = []
    for item in read(run / 'acquisition.json')['items']:
        glb = run / 'prepared' / item['id'] / 'model.glb'
        digest = sha(glb)
        value = fingerprint(glb.read_bytes())
        comparisons.append({'id': item['id'], 'sha256': digest, 'geometryFingerprint': value,
            'exactMatches': [m['id'] for m in baseline if m['sha256'] == digest],
            'geometryMatches': [m['id'] for m in baseline if values[m['sha256']]['sha256'] == value['sha256']]})
    peers = {}
    for row in comparisons:
        row['exactPeerMatches'] = peers.get(row['sha256'], []).copy()
        peers.setdefault(row['sha256'], []).append(row['id'])
        row['geometryPeerMatches'] = [other['id'] for other in comparisons if other['id'] != row['id'] and other['geometryFingerprint']['sha256'] == row['geometryFingerprint']['sha256']]
    save(run / 'deduplication.json', {'baselineModels': len(baseline), 'baselineFingerprintCount': len(baseline),
         'unsupported': [], 'comparisons': comparisons, 'methodNote': 'An invariant geometry match is a candidate; different fingerprints do not rule out semantic variants.'})
    print('DEDUPLICATED', len(comparisons), 'against', len(baseline), flush=True)


def promote(run):
    from PIL import Image
    acquired = read(run / 'acquisition.json')
    dedup = read(run / 'deduplication.json')
    visual = read(run / 'visual-review.json')
    if visual['result'] != 'PASS' or dedup['baselineFingerprintCount'] != dedup['baselineModels']:
        raise ValueError('Review incomplete')
    for relative, digest in visual['images'].items():
        if sha(run / relative) != digest:
            raise ValueError('Reviewed image changed')
    for relative, digest in read(run / 'original-inventory.json').items():
        if sha(ROOT / relative) != digest:
            raise ValueError('Baseline asset changed: ' + relative)
    # Reject a repeat before writing any shared evidence or touching model folders.
    for row in dedup['comparisons']:
        if not row['exactMatches'] and not row['exactPeerMatches'] and (ROOT / 'models' / row['id']).exists():
            raise ValueError('Model already promoted; use a new acquisition run')
    selection = read(ROOT / 'enrichment/polyhaven-selection.json')
    area_plan = read(ROOT / 'selection.json')
    dependencies = read(ROOT / 'gallery/dependencies.json')
    source_root = ROOT / 'sources/external/polyhaven' / run.name
    source_root.mkdir(parents=True, exist_ok=False)
    # Full website capture stays private. Public evidence records the declaration and its hash.
    save(source_root / 'license-evidence.json', {
        'license': 'CC0 1.0', 'licenseUrl': LICENSE_URL, 'sourceUrl': 'https://polyhaven.com/license',
        'retrievedAt': datetime.now(timezone.utc).isoformat(), 'pageSha256': sha(run / 'license-page.html'),
        'declarationExcerpt': 'Our assets are all licensed as CC0',
        'apiTermsUrl': 'https://github.com/Poly-Haven/Public-API/blob/master/ToS.md',
        'apiTermsSha256': sha(run / 'api-terms.txt'), 'previewPolicy': 'Own renders; website example images are not included.'})
    save(source_root / 'deduplication.json', dedup)
    public_images = {}
    for relative, digest in visual['images'].items():
        target = source_root / 'review' / Path(relative).name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(run / relative, target)
        public_images[target.relative_to(ROOT).as_posix()] = digest
    save(source_root / 'visual-review.json', {**visual, 'images': public_images})
    groups, aliases, added = {}, [], []
    for item in acquired['items']:
        mid = item['id']
        prepared = run / 'prepared' / mid
        result = run / 'review-v3' / mid if (run / 'review-v3' / mid / 'review.json').exists() else prepared
        assessment = read(result / 'review-v2.json' if (result / 'review-v2.json').exists() else result / 'review.json')
        preparation = read(prepared / 'preparation.json')
        comparison = next(c for c in dedup['comparisons'] if c['id'] == mid)
        digest = sha(prepared / 'model.glb')
        if assessment['technical'] != 'PASS' or any(digest != v for v in [assessment['glbSha256'], preparation['glbSha256'], comparison['sha256']]):
            raise ValueError('Technical/preparation evidence changed: ' + mid)
        exact = comparison['exactMatches'] + comparison['exactPeerMatches']
        canonical = exact[0] if exact else mid
        family = item['family']
        group = groups.setdefault(family, {'id': family, 'title': selection.get('familyTitles', {}).get(family, item['title']), 'modelIds': [], 'relation': 'functional-family-or-variant'})
        if canonical not in group['modelIds']:
            group['modelIds'].append(canonical)
        if exact:
            aliases.append({'id': mid, 'canonicalId': canonical, 'reason': 'Same GLB SHA-256', 'sourceUrl': 'https://polyhaven.com/a/' + item['asset']})
            continue
        if comparison['geometryMatches']:
            raise ValueError('Geometry match needs explicit review: ' + mid)
        folder = ROOT / 'models' / mid
        if folder.exists():
            raise ValueError('Refusing to replace existing model: ' + mid)
        folder.mkdir()
        source_url = 'https://polyhaven.com/a/' + item['asset']
        authors = ', '.join(item['metadata']['authors'])
        changes = 'glTF ' + item['resolution'] + ' empaquetado en GLB; búferes geométricos e imágenes conservados byte a byte; escenas, materiales, UV, ejes y escala sin cambios. Sin decimación ni redimensionado de texturas.'
        credit = '"' + item['metadata']['name'] + '", por ' + authors + ' / Poly Haven. ' + source_url + '. CC0 1.0 ' + LICENSE_URL + '. Empaquetado GLB y miniatura: GuateGeeks.'
        shutil.copyfile(prepared / 'model.glb', folder / 'model.glb')
        originals = []
        for entry in item['files']:
            source = safe_path(run / 'downloads' / item['asset'], entry['file'])
            target = safe_path(folder / 'original', entry['file'])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            originals.append({**entry, 'file': target.relative_to(ROOT).as_posix()})
        (folder / 'LICENSE.txt').write_text(credit + '\n\nCambios: ' + changes + '\nEvidencia: https://polyhaven.com/license\n', encoding='utf-8')
        with zipfile.ZipFile(folder / 'originals.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for entry in originals:
                target = ROOT / entry['file']
                archive.write(target, target.relative_to(folder).as_posix())
            archive.write(folder / 'LICENSE.txt', 'LICENSE.txt')
        asset_evidence = source_root / item['asset']
        asset_evidence.mkdir()
        save(asset_evidence / 'metadata.json', item['metadata'])
        shutil.copyfile(run / ('files-' + item['asset'] + '.json'), asset_evidence / 'files.json')
        render_evidence = {}
        for name, image_hash in assessment['images'].items():
            target = asset_evidence / 'renders' / name
            target.parent.mkdir(exist_ok=True)
            if sha(result / name) != image_hash:
                raise ValueError('Technical review image changed')
            shutil.copyfile(result / name, target)
            render_evidence[target.relative_to(ROOT).as_posix()] = image_hash
        save(asset_evidence / 'technical-review.json', {**assessment, 'sourceFile': item['entryFile'], 'images': render_evidence})
        raw = (prepared / 'model.glb').read_bytes()
        metadata = {
            'id': mid, 'assetId': 'polyhaven:' + item['asset'], 'providerId': 'polyhaven', 'provider': 'Poly Haven',
            'title': item['title'], 'titleOriginal': item['metadata']['name'], 'author': authors, 'authorUrl': source_url,
            'sourceUrl': source_url, 'metadataUrl': 'https://api.polyhaven.com/info/' + item['asset'],
            'downloadUrl': next(f['url'] for f in item['files'] if f['file'] == item['entryFile']),
            'thumbnailUrl': None, 'description': 'Modelo detallado de Poly Haven. Escala y uso curricular pendientes de revisión docente.',
            'category': item['metadata'].get('category', 'Objects'), 'tags': item['metadata'].get('tags', []) + [item['metadata']['name'], family],
            'areas': item['areas'], 'queries': [], 'products': ['code-studio', 'socrates'],
            'subjects': sorted({s for a in area_plan['areas'] if a['id'] in item['areas'] for s in a['subjects']}),
            'licenseRaw': 'CC0 1.0', 'license': license_info('CC0 1.0'), 'attribution': credit, 'modifications': changes,
            'file': 'models/' + mid + '/model.glb', 'sourceMetadataFile': (asset_evidence / 'metadata.json').relative_to(ROOT).as_posix(),
            'originalDownload': 'models/' + mid + '/originals.zip', 'bytes': len(raw), 'sha256': digest,
            'apiTriangleCount': None, 'apiAnimated': None, 'gltf': inspect(raw),
            'retrievedAt': item['retrievedAt'], 'reviewStatus': 'pending', 'educationalReview': 'Uso curricular concreto pendiente.',
            'reviewFlags': ['detailed-reference-review'] + (['regional-label-review'] if item['asset'] == 'korean_fire_extinguisher_01' else []),
            'unfulfilledQueries': [],
            'provenance': {'pack': 'Poly Haven native glTF ' + item['resolution'], 'sourceMember': item['entryFile'],
                'originalFiles': originals, 'originalDownloadSha256': sha(folder / 'originals.zip'),
                'licenseEvidence': (source_root / 'license-evidence.json').relative_to(ROOT).as_posix(),
                'licenseEvidenceSha256': sha(source_root / 'license-evidence.json'),
                'metadataEvidence': (asset_evidence / 'metadata.json').relative_to(ROOT).as_posix(),
                'metadataEvidenceSha256': sha(asset_evidence / 'metadata.json'),
                'fileManifestEvidence': (asset_evidence / 'files.json').relative_to(ROOT).as_posix(),
                'fileManifestEvidenceSha256': sha(asset_evidence / 'files.json'),
                'technicalReviewEvidence': (asset_evidence / 'technical-review.json').relative_to(ROOT).as_posix(),
                'technicalReviewEvidenceSha256': sha(asset_evidence / 'technical-review.json'),
                'providerReportedPolycount': item['metadata'].get('polycount'),
                'conversionTool': 'GuateGeeks glTF container packer v1', 'renderTool': 'Blender ' + assessment['blenderVersion'],
                'dimensionsBlender': assessment['dimensionsBlender'], 'reimportDimensionsBlender': assessment['reimport']['dimensionsBlender'],
                'scaleChange': False, 'geometryFingerprint': preparation['geometryFingerprint'],
                'sourceGeometryViewsByteIdentical': True, 'sourceSceneAndMaterialsUnchanged': True},
            'qa': {'rights': 'PASS', 'technical': 'PASS', 'visual': 'PASS', 'educational': 'NOT_RUN',
                   'reviewEvidence': (source_root / 'visual-review.json').relative_to(ROOT).as_posix()}
        }
        save(folder / 'metadata.json', metadata)
        save(folder / 'source.json', {'Licence': 'CC0 1.0', 'Attribution': credit, 'Creator': {'Username': authors},
             'Title': item['metadata']['name'], 'sourceUrl': source_url, 'assetId': item['asset'],
             'originalFiles': originals, 'licenseEvidence': metadata['provenance']['licenseEvidence']})
        thumb = ROOT / 'gallery/thumbnails' / (mid + '.webp')
        Image.open(result / 'reimport-three-quarter.png').convert('RGB').save(thumb, 'WEBP', quality=88)
        dependencies['thumbnails'].append({'id': mid, 'file': thumb.relative_to(ROOT).as_posix(), 'url': None,
            'generatedFrom': digest, 'sha256': sha(thumb), 'modelLicense': 'CC0 1.0',
            'method': 'Own Blender CPU render', 'attribution': credit})
        added.append(mid)
    for family, ids in selection['existingFamilyMembers'].items():
        if family in groups:
            groups[family]['modelIds'] = ids + [mid for mid in groups[family]['modelIds'] if mid not in ids]
    group_file = ROOT / 'groups/polyhaven.json'
    previous = read(group_file) if group_file.exists() else {'groups': [], 'aliases': []}
    for group in previous['groups']:
        if group['id'] in groups:
            groups[group['id']]['modelIds'] = list(dict.fromkeys(group['modelIds'] + groups[group['id']]['modelIds']))
        else:
            groups[group['id']] = group
    save(group_file, {'schemaVersion': 1, 'groups': list(groups.values()), 'aliases': previous['aliases'] + aliases,
         'grouping': selection['groupingNote']})
    save(ROOT / 'gallery/dependencies.json', dependencies)
    save(ROOT / 'enrichment/reports' / (run.name + '.json'), {
        'provider': 'Poly Haven', 'added': len(added), 'modelIds': added, 'aliases': aliases, 'held': acquired['held'],
        'baselineModels': dedup['baselineModels'], 'selection': 'enrichment/polyhaven-selection.json',
        'rights': 'CC0 1.0', 'licenseUrl': 'https://polyhaven.com/license',
        'webPreparation': 'Native glTF components preserved inside GLB; no remeshing, decimation or scale normalization.',
        'renderQA': 'Source multi-view and clean GLB reimport; own thumbnails. Educational review pending.'})
    print(json.dumps({'added': len(added), 'aliases': len(aliases), 'held': len(acquired['held'])}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['acquire', 'pack', 'deduplicate', 'promote'])
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    globals()[args.command](args.run.resolve())
