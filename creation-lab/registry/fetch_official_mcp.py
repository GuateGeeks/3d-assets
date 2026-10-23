"""Fetch official pinned MCP source and release archives for review, without execution."""
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'creation-lab/registry'
BASE = 'https://projects.blender.org/api/v1/repos/lab/blender_mcp'
COMMIT = '2cea8d566dde07fbac28a61d698909d69724e853'

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'GuateGeeks-static-source-audit'})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()

def main():
    ref = json.loads(fetch(BASE + '/git/refs/tags/v1.0.3'))
    if isinstance(ref, list):
        ref = next(item for item in ref if item['ref'] == 'refs/tags/v1.0.3')
    if ref['object']['sha'] != COMMIT or ref['object']['type'] != 'commit':
        raise ValueError('Official release tag changed')
    files = []
    def descend(path):
        entries = json.loads(fetch(BASE + '/contents/' + path + '?ref=' + COMMIT))
        if isinstance(entries, dict):
            entries = [entries]
        for entry in entries:
            name = entry['path']
            if entry['type'] == 'dir':
                if name in {'mcp/blmcp/data'}:
                    continue
                descend(name)
            elif name.endswith(('.py', '.toml', '.txt', '.md', '.json', '.rst')):
                blob = json.loads(fetch(BASE + '/git/blobs/' + entry['sha']))
                data = base64.b64decode(blob['content'])
                digest = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
                if digest != entry['sha'] or len(data) > 500000:
                    raise ValueError('Unexpected source bytes: ' + name)
                target = ROOT / 'creation-lab/vendor/blender-lab-mcp/source' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                files.append({'file': target.relative_to(ROOT).as_posix(), 'upstreamPath': name,
                              'sha256': hashlib.sha256(data).hexdigest(), 'gitBlob': digest,
                              'bytes': len(data), 'url': entry['download_url']})
    for path in ['readme.md', 'mcp', 'addon']:
        descend(path)
    release = json.loads(fetch(BASE + '/releases/tags/v1.0.3'))
    archives = []
    for asset in release['assets']:
        if asset['name'] not in {'blender-1.0.3.mcpb', 'mcp-1.0.3.zip'}:
            continue
        if asset['size'] > 6000000:
            raise ValueError('Unexpectedly large release archive')
        data = fetch(asset['browser_download_url'])
        if len(data) != asset['size']:
            raise ValueError('Release size mismatch')
        target = ROOT / 'creation-lab/vendor/blender-lab-mcp/packages' / asset['name']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        entries = []
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.infolist():
                path = PurePosixPath(member.filename)
                if path.is_absolute() or '..' in path.parts or (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('Unsafe archive entry')
                if not member.is_dir():
                    contents = archive.read(member)
                    entries.append({'path': member.filename, 'bytes': len(contents), 'sha256': hashlib.sha256(contents).hexdigest()})
            for name in ['manifest.json', 'blender_manifest.toml']:
                if name in archive.namelist():
                    (REGISTRY / ('official-' + asset['name'] + '-' + name)).write_bytes(archive.read(name))
        archives.append({'file': target.relative_to(ROOT).as_posix(), 'url': asset['browser_download_url'],
                         'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'entries': entries})
    manifest = {'id': 'blender-lab-mcp', 'repository': 'https://projects.blender.org/lab/blender_mcp',
                'tag': 'v1.0.3', 'commit': COMMIT, 'files': files, 'archives': archives,
                'scope': 'source code excluding generated API/manual data; release ZIP inventories and hashes; no execution'}
    (REGISTRY / 'blender-lab-mcp.source.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'sourceFiles': len(files), 'archives': len(archives), 'commit': COMMIT}))

if __name__ == '__main__':
    main()
