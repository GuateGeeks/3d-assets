"""Record prepared source integrity and resolved local runtime; no downloads or execution."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / 'creation-lab'
REGISTRY = LAB / 'registry'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, data): path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
def receipt(path): return {'file': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}

def main():
    sources = []
    for key, license_id, selection in [('rivello', 'MIT', 'selected-codex-recipes'), ('lpm', 'MIT', 'adapted-lowpoly-recipes'), ('mcp-fallback', 'MIT', 'fallback-only-not-activated'), ('hermes-reference', None, 'reference-only-not-redistributed')]:
        manifest_path = REGISTRY / (key + '.source.json')
        manifest = json.loads(manifest_path.read_text())
        installed = []
        for item in manifest['files']:
            if not item.get('file'):
                continue
            original = ROOT / item['file']
            if sha(original) != item['sha256']:
                raise ValueError('Changed source: ' + str(original))
            path = item['upstreamPath']
            dest = None
            if key == 'rivello' and path.startswith('.codex/skills/'):
                dest = LAB / 'vendor/rivello' / path.removeprefix('.codex/skills/')
            elif key == 'lpm' and path.startswith('skills/'):
                dest = LAB / 'vendor/lpm' / path.removeprefix('skills/')
            if dest is not None:
                if sha(dest) != item['sha256']:
                    if dest.read_bytes().replace(b'\r\n', b'\n') != original.read_bytes().replace(b'\r\n', b'\n'):
                        raise ValueError('Installed source mismatch: ' + str(dest))
                    dest.write_bytes(original.read_bytes())
                installed.append(receipt(dest))
        sources.append({'id': key, 'repository': manifest['repository'], 'commit': manifest['commit'], 'license': license_id,
                        'selection': selection, 'sourceManifest': receipt(manifest_path), 'installedFiles': installed,
                        'runtimeStatus': 'NOT_RUN', 'auditScope': 'targeted static review; file hashes and syntax for prepared Python; no execution endorsement'})
    official_path = REGISTRY / 'blender-lab-mcp.source.json'
    official = json.loads(official_path.read_text())
    prompt = LAB / 'vendor/blender-lab-mcp/source/mcp/blmcp/data/prompts.yml'
    if prompt.exists() and not any(x.get('upstreamPath') == 'mcp/blmcp/data/prompts.yml' for x in official['files']):
        official['files'].append({**receipt(prompt), 'upstreamPath': 'mcp/blmcp/data/prompts.yml', 'sourceArchive': official['archives'][0]['file']})
        save(official_path, official)
    runs = [json.loads(path.read_text()) for path in sorted(REGISTRY.glob('mcp-probe-*/report.json'))]
    latest = runs[-1] if runs else {'status': 'NOT_RUN'}
    launcher_reports = sorted(REGISTRY.glob('launcher-probe-*/report.json'))
    launcher_latest = json.loads(launcher_reports[-1].read_text()) if launcher_reports else {'status': 'NOT_RUN'}
    project_config_path = ROOT / '.codex/config.toml'
    project_config = tomllib.loads(project_config_path.read_text(encoding='utf-8')) if project_config_path.exists() else {}
    project_entry = project_config.get('mcp_servers', {}).get('blender_lab', {})
    registered = project_entry.get('enabled') is True
    sources.append({'id': 'blender-lab-mcp', 'repository': official['repository'], 'tag': official['tag'], 'commit': official['commit'],
                    'license': 'GPL-3.0-or-later', 'selection': 'preferred-single-bridge', 'sourceManifest': receipt(official_path),
                    'runtimeStatus': latest['status'], 'runtimeEvidence': 'creation-lab/registry/' + latest['runId'] + '/report.json' if runs else None,
                    'registrationStatus': 'PASS' if registered else 'NOT_RUN',
                    'registrationEvidence': receipt(project_config_path) if registered else None,
                    'codexToolAvailabilityStatus': 'NOT_RUN', 'viewportScreenshotStatus': 'NOT_RUN',
                    'launcherProbeStatus': launcher_latest['status'],
                    'launcherProbeEvidence': receipt(launcher_reports[-1]) if launcher_reports else None,
                    'auditScope': 'targeted source review, archive integrity, isolated stdio MCP smoke; unrelated tools and user editor NOT_RUN'})
    installed = json.loads((REGISTRY / 'mcp-runtime-install.json').read_text(encoding='utf-8'))
    packages = []
    lines = ['# Resolved Windows CPython 3.12 wheels; pip install --require-hashes --only-binary=:all: --target <isolated-dir> -r this-file']
    for item in installed['install']:
        metadata = item['metadata']; download = item['download_info']
        digest = download['archive_info']['hashes']['sha256']
        packages.append({'name': metadata['name'], 'version': metadata['version'], 'url': download['url'], 'sha256': digest,
                         'licenseExpression': metadata.get('license_expression'), 'license': metadata.get('license')})
        lines.append(f"{metadata['name']}=={metadata['version']} --hash=sha256:{digest}")
    save(REGISTRY / 'mcp-runtime.lock.json', {'schemaVersion': 1, 'python': installed['environment'], 'packages': packages, 'scope': 'isolated local Windows runtime; no global install'})
    (REGISTRY / 'mcp-runtime.requirements.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    syntax = []
    for source in [LAB / 'vendor/rivello', LAB / 'vendor/lpm', LAB / 'vendor/blender-lab-mcp/source']:
        for path in sorted(source.rglob('*.py')):
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
            syntax.append(path.relative_to(ROOT).as_posix())
    copy_files = [LAB / 'vendor/rivello/LICENSE', LAB / 'vendor/lpm/LICENSE', LAB / 'vendor/blender-lab-mcp/COPYING.GPL-3.0.txt']
    wrappers = [receipt(path) for path in sorted(REGISTRY.glob('skill-pack/blender-*/SKILL.md'))]
    installed_wrappers = [receipt(ROOT / '.agents/skills' / Path(item['file']).parent.name / 'SKILL.md') for item in wrappers]
    for prepared, installed_wrapper in zip(wrappers, installed_wrappers):
        if prepared['sha256'] != installed_wrapper['sha256']:
            raise ValueError('Installed skill differs from reviewed adapter: ' + installed_wrapper['file'])
    lock = {'schemaVersion': 1, 'recordedAt': datetime.now(timezone.utc).isoformat(), 'sources': sources,
            'licenses': [receipt(path) for path in copy_files], 'adapters': wrappers, 'installedAdapters': installed_wrappers,
            'projectRuntimeFiles': [receipt(REGISTRY / name) for name in ['launch_official_mcp.py', 'launch_isolated_mcp.py', 'probe_official_mcp.py', 'probe_project_launcher.py', 'codex-mcp.example.toml']],
            'runtimeLock': receipt(REGISTRY / 'mcp-runtime.lock.json'), 'runtimeRequirements': receipt(REGISTRY / 'mcp-runtime.requirements.txt'),
            'installation': {'helper': 'skill-installer/scripts/install-skill-from-github.py', 'method': 'git sparse checkout', 'destination': 'creation-lab/vendor', 'upstreamInstallScriptsExecuted': False},
            'validation': {'sourceIntegrity': 'PASS', 'syntax': 'PASS', 'pythonFilesParsed': len(syntax), 'note': 'AST parsing is not runtime testing'}}
    save(LAB / 'sources.lock.json', lock)
    config = tomllib.loads((REGISTRY / 'codex-mcp.example.toml').read_text())
    if config['mcp_servers']['blender_lab']['enabled'] is not False:
        raise ValueError('Example must stay disabled')
    save(REGISTRY / 'source-preparation.json', {'status': 'PASS', 'sourceCount': len(sources), 'pythonFilesParsed': len(syntax),
         'parsedFiles': syntax, 'mcpProbeStatus': latest['status'], 'launcherProbeStatus': launcher_latest['status'],
         'projectRegistrationStatus': 'PASS' if registered else 'NOT_RUN', 'codexToolAvailabilityStatus': 'NOT_RUN',
         'codexExampleParsed': True, 'globalConfigurationChanged': False})
    print(json.dumps({'sources': len(sources), 'pythonFilesParsed': len(syntax), 'mcpProbe': latest['status']}))

if __name__ == '__main__': main()
