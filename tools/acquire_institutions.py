"""Acquire explicitly selected native GLBs; credentials stay in process memory.

Download caches are private staging, not publication inventory. Promotion is a
separate offline step after rights, integrity, duplicate and visual review.
"""
import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from catalog import inspect

ROOT = Path(__file__).resolve().parents[1]
AGENT = 'GuateGeeks-3D-Assets/1.0 (https://guategeeks.com/3d-assets/)'
LIMIT = 25 * 1024 ** 2


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fetch(url, target=None, token=None, limit=LIMIT):
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or ''
    if parsed.scheme != 'https' or not (
        host in {'api.sketchfab.com', 'api.si.edu', '3d-api.si.edu', 'assets.science.nasa.gov', 'science.nasa.gov'}
        or host.endswith('.s3.amazonaws.com') or host.endswith('.s3.us-east-1.amazonaws.com')
    ):
        raise ValueError('Unapproved acquisition host: ' + host)
    if token and host != 'api.sketchfab.com':
        raise ValueError('Credential must only reach Sketchfab API')
    if target and target.is_file():
        return target.read_bytes()
    for attempt in range(3):
        try:
            headers = {'User-Agent': AGENT}
            if token:
                headers['Authorization'] = 'Token ' + token
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
                if int(response.headers.get('Content-Length', '0')) > limit:
                    raise ValueError('Download exceeds declared acquisition limit')
                raw = response.read(limit + 1)
            if len(raw) > limit:
                raise ValueError('Download exceeds acquisition limit')
            if target:
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix(target.suffix + '.part')
                temporary.write_bytes(raw)
                temporary.replace(target)
            time.sleep(.2)
            return raw
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
            wait = error.headers.get('Retry-After', '')
            if wait.isdigit() and int(wait) > 30:
                raise
            time.sleep(int(wait) if wait.isdigit() else 2 ** attempt)


def sketchfab_license(url):
    url = url.replace('http://', 'https://')
    if url == 'https://creativecommons.org/publicdomain/zero/1.0/':
        return 'CC0 1.0'
    match = re.fullmatch(r'https://creativecommons.org/licenses/(by(?:-nc)?(?:-sa)?)/(\d\.\d)/', url)
    if not match:
        raise ValueError('License needs individual review')
    return 'CC-' + match[1].upper() + ' ' + match[2]


def acquire(run, selection):
    if not (run / 'baseline-index.json').exists():
        save(run / 'baseline-index.json', read(ROOT / 'index.json'))
        save(run / 'baseline-model-files.json', {
            p.relative_to(ROOT).as_posix(): sha(p)
            for p in (ROOT / 'models').rglob('*') if p.is_file()
        })
    rows, held = [], []
    token = os.environ.get('SKETCHFAB_TOKEN')
    for proposal in read(selection)['items']:
        mid = proposal['id']
        if not re.fullmatch('[a-z0-9-]+', mid):
            raise ValueError('Unsafe ID')
        folder = run / 'downloads' / mid
        folder.mkdir(parents=True, exist_ok=True)
        try:
            row = dict(proposal)
            if proposal['providerId'] == 'sketchfab':
                if not token:
                    raise ValueError('Sketchfab token missing in this process')
                uid = proposal['asset']
                endpoint = 'https://api.sketchfab.com/v3/models/' + uid
                meta = json.loads(fetch(endpoint, folder / 'metadata.json', token))
                if not meta.get('isDownloadable') or meta.get('isAgeRestricted'):
                    raise ValueError('Not downloadable or age restricted')
                license_url = meta['license']['url'].replace('http://', 'https://')
                row.update(licenseRaw=sketchfab_license(license_url),
                           licenseUrl=license_url, titleOriginal=meta['name'],
                           author=meta['user']['displayName'], authorUrl=meta['user']['profileUrl'])
                url = proposal.get('downloadUrl')
                if not (folder / 'model.glb').exists():
                    # Signed URLs are intentionally never written into public metadata.
                    downloads = json.loads(fetch(endpoint + '/download', token=token))
                    if not downloads.get('glb'):
                        raise ValueError('No official native GLB download')
                    url = downloads['glb']['url']
                    if downloads['glb'].get('size', 0) > LIMIT:
                        raise ValueError('Native GLB exceeds 25 MiB budget')
                    raw = fetch(url, folder / 'model.glb')
                else:
                    raw = (folder / 'model.glb').read_bytes()
                row['downloadUrl'] = endpoint + '/download'
                row['sourceMetadata'] = str(folder / 'metadata.json')
            else:
                captured = json.loads(fetch(proposal['metadataUrl'], folder / 'metadata.json'))
                if proposal['providerId'] == 'smithsonian':
                    media = [medium for record in captured['response']['rows']
                             for medium in record['content']['descriptiveNonRepeating'].get('online_media', {}).get('media', [])
                             if medium.get('id') == proposal['asset'] and medium.get('usage', {}).get('access') == 'CC0']
                    if not any(resource.get('url') == proposal['downloadUrl'] for medium in media for resource in medium.get('resources', [])):
                        raise ValueError('Selected Smithsonian medium/file no longer has matching CC0 evidence')
                elif proposal['downloadUrl'] not in captured['content']['rendered']:
                    raise ValueError('Selected NASA file no longer appears in its source record')
                row['sourceMetadata'] = str(folder / 'metadata.json')
                raw = fetch(proposal['downloadUrl'], folder / 'model.glb')
            gltf = inspect(raw)
            if not gltf['selfContained']:
                raise ValueError('Native GLB has unresolved dependencies')
            row.update(input=str(folder / 'model.glb'), entryFile='model.glb',
                       sha256=sha(folder / 'model.glb'), bytes=len(raw), gltf=gltf,
                       retrievedAt=datetime.now(timezone.utc).isoformat())
            prepared = run / 'prepared' / mid / 'model.glb'
            prepared.parent.mkdir(parents=True, exist_ok=True)
            if prepared.exists() and prepared.read_bytes() != raw:
                raise ValueError('Prepared evidence already exists with different bytes')
            prepared.write_bytes(raw)
            rows.append(row)
            print('ACQUIRED', mid, round(len(raw) / 1048576, 2), 'MiB', flush=True)
        except Exception as error:
            # Error text never contains signed download links or request headers.
            held.append({'id': mid, 'providerId': proposal['providerId'],
                         'sourceUrl': proposal['sourceUrl'], 'reason': type(error).__name__,
                         'httpStatus': error.code if isinstance(error, urllib.error.HTTPError) else None,
                         'detail': str(error) if isinstance(error, ValueError) else 'Acquisition failed; inspect private local logs'})
            print('HELD', mid, held[-1]['detail'], flush=True)
        save(run / 'acquisition.json', {'items': rows, 'held': held, 'agent': AGENT})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--selection', type=Path, required=True)
    args = parser.parse_args()
    args.run.mkdir(parents=True, exist_ok=True)
    acquire(args.run, args.selection)
