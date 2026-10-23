"""Record upstream license and installed package provenance without network access."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / 'lab/.local'


def main():
    profile = json.loads((ROOT / 'lab/envs/unirig.profile.json').read_text())
    output = ROOT / 'lab/reports/licenses'
    output.mkdir(parents=True, exist_ok=True)
    license_file = LOCAL / 'repos/UniRig/LICENSE'
    shutil.copy2(license_file, output / 'UniRig.LICENSE.txt')
    packages = []
    for dist in sorted(importlib.metadata.distributions(), key=lambda item: item.metadata['Name'].lower()):
        item = {'name': dist.metadata['Name'], 'version': dist.version}
        if dist.metadata.get('License-Expression'):
            item['declaredLicenseExpression'] = dist.metadata['License-Expression']
        item['licenseFiles'] = [str(path) for path in (dist.files or [])
                                if 'license' in Path(str(path)).name.lower() and '.dist-info/' in str(path)]
        direct = dist.read_text('direct_url.json')
        if direct:
            item['directDownload'] = json.loads(direct)
        packages.append(item)
    report = {'schemaVersion': 1, 'upstream': {'repository': profile['repository'], 'commit': profile['commit'],
              'licenseFile': 'licenses/UniRig.LICENSE.txt',
              'licenseSha256': hashlib.sha256(license_file.read_bytes()).hexdigest()},
              'scope': 'installation provenance; packages and upstream source are kept outside the static site',
              'packages': packages}
    (ROOT / 'lab/reports/unirig-provenance.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Recorded upstream license and provenance for', len(packages), 'installed packages.')


if __name__ == '__main__':
    main()
