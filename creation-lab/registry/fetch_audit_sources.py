"""Download pinned public text for static review; never execute upstream."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'creation-lab/registry'
SKILLS = ['blender-setup', 'blender-create-greybox', 'blender-create-model', 'blender-materials', 'blender-light-camera', 'blender-render', 'blender-game-export', 'blender-review-optimize', 'blender-uv-bake']
SOURCES = [
    ('rivello', 'SamuelAsherRivello/ai-skills-blender', '54b4f26b7c0e530b7158244f397b34e6c16d7b76'),
    ('lpm', 'ozanzeng/blender-LPM-skill', '687d0a46f1280bc7d11dbf83539840100ec909dc'),
    ('mcp-fallback', 'ahujasid/mcp-for-blender', '5a3618fccb2d982d0dd61e7a1879912c3100073b'),
    ('hermes-reference', 'theheavenlyd3mon/hermes-profiles', '848635cc85293d0f30027d2f4c261aa095b2d51f'),
]

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'GuateGeeks-static-source-audit'})
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read()

def selected(source, path):
    if source == 'rivello':
        return path in {'LICENSE', 'README.md', '.codex/INSTALL.md'} or any(path.startswith('.codex/skills/' + skill + '/') for skill in SKILLS)
    if source == 'lpm':
        return path in {'LICENSE', 'README.md'} or path.startswith('skills/blender-lpm-skill/')
    if source == 'mcp-fallback':
        return path in {'LICENSE', 'README.md', 'pyproject.toml', 'addon.py', 'src/blender_mcp/server.py', 'src/blender_mcp/addon_manager.py'}
    return path == 'profiles/creative/skills/creative/blender-automation/SKILL.md'

def main():
    summary = []
    for source, repo, commit in SOURCES:
        tree = json.loads(fetch(f'https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1'))
        if tree.get('truncated') or tree['sha'] != commit:
            raise ValueError('Incomplete or unexpected source tree')
        entries = [x for x in tree['tree'] if x['type'] == 'blob' and selected(source, x['path'])]
        manifest = {'id': source, 'repository': 'https://github.com/' + repo, 'commit': commit,
                    'rootLicensePaths': [x['path'] for x in tree['tree'] if x['type'] == 'blob' and '/' not in x['path'] and x['path'].lower().startswith(('license', 'copying'))],
                    'reviewType': 'static-source-only', 'files': []}
        for entry in entries:
            path = entry['path']
            if entry.get('size', 0) > 400000 or entry.get('mode') == '120000':
                raise ValueError('Oversized file or symlink: ' + path)
            url = f'https://raw.githubusercontent.com/{repo}/{commit}/{path}'
            data = fetch(url)
            git_hash = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
            if git_hash != entry['sha']:
                raise ValueError('Git object mismatch: ' + path)
            item = {'upstreamPath': path, 'url': url, 'gitBlob': git_hash, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
            if source != 'hermes-reference':
                target = REGISTRY / 'audit-input' / source / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                item['file'] = target.relative_to(ROOT).as_posix()
            else:
                item['frontmatterLicenseClaim'] = 'MIT' if 'license: MIT' in data.decode() else None
                item['redistributed'] = False
            manifest['files'].append(item)
        output = REGISTRY / (source + '.source.json')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        summary.append({'id': source, 'files': len(entries), 'bytes': sum(x['bytes'] for x in manifest['files'])})
    print(json.dumps(summary))

if __name__ == '__main__':
    main()
