"""Install a checksum-verified uv binary under the ignored laboratory directory."""
import hashlib
import io
import json
import os
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / 'lab/.local'


def bootstrap(version):
    executable = LOCAL / 'bin/uv'
    receipt_path = LOCAL / 'bootstrap/uv.json'
    if executable.is_file() and receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text())
        if receipt['version'] != version:
            raise RuntimeError('Existing uv version differs from the profile')
        if hashlib.sha256(executable.read_bytes()).hexdigest() != receipt['binarySha256']:
            raise RuntimeError('Existing uv binary checksum differs from its receipt')
        return executable
    with urllib.request.urlopen(f'https://pypi.org/pypi/uv/{version}/json', timeout=60) as response:
        metadata = json.load(response)
    wheels = [entry for entry in metadata['urls']
              if entry['filename'].endswith('manylinux_2_17_x86_64.manylinux2014_x86_64.whl')]
    if len(wheels) != 1:
        raise RuntimeError('Could not identify the official Linux x86_64 uv wheel')
    wheel = wheels[0]
    with urllib.request.urlopen(wheel['url'], timeout=120) as response:
        data = response.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != wheel['digests']['sha256']:
        raise RuntimeError('uv wheel SHA-256 mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = [name for name in archive.namelist() if name.endswith('/uv')]
        if len(names) != 1:
            raise RuntimeError('Unexpected uv wheel layout')
        binary = archive.read(names[0])
    executable.parent.mkdir(parents=True, exist_ok=True)
    temporary = executable.with_suffix('.partial')
    temporary.write_bytes(binary)
    temporary.chmod(0o755)
    os.replace(temporary, executable)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps({'version': version, 'url': wheel['url'],
        'wheelSha256': digest, 'binarySha256': hashlib.sha256(binary).hexdigest()}, indent=2) + '\n')
    return executable


if __name__ == '__main__':
    profile = json.loads((ROOT / 'lab/envs/unirig.profile.json').read_text())
    print(bootstrap(profile['uv']))
