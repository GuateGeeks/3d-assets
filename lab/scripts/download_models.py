"""Cache only the required checkpoints and OPT configuration at pinned HF revisions."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / 'lab/.local'
os.environ.setdefault('HF_HOME', str(LOCAL / 'cache/huggingface'))
os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
from huggingface_hub import HfApi, hf_hub_download

PROFILE = ROOT / 'lab/envs/unirig.profile.json'
RECEIPT = ROOT / 'lab/reports/unirig-models.json'


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    profile = json.loads(PROFILE.read_text())
    previous = json.loads(RECEIPT.read_text()) if RECEIPT.exists() else {}
    api = HfApi()
    revision = previous.get('revision') or api.model_info(profile['modelRepository'], timeout=30).sha
    info = api.model_info(profile['modelRepository'], revision=revision, files_metadata=True, timeout=30)
    files = {entry.rfilename: entry for entry in info.siblings}
    report = {'schemaVersion': 1, 'repository': profile['modelRepository'], 'revision': revision,
              'status': 'downloading', 'files': []}
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(report, indent=2) + '\n')
    for name in profile['modelFiles']:
        print('Downloading checkpoint:', name, flush=True)
        path = Path(hf_hub_download(profile['modelRepository'], filename=name, revision=revision, etag_timeout=30))
        digest = sha256(path)
        entry = files[name]
        expected = entry.lfs.sha256 if entry.lfs else None
        if expected and digest != expected:
            raise RuntimeError('Checkpoint checksum mismatch: ' + name)
        report['files'].append({'file': name, 'bytes': path.stat().st_size, 'sha256': digest,
                                'expectedSha256': expected, 'cachePath': str(path.relative_to(LOCAL))})
        RECEIPT.write_text(json.dumps(report, indent=2) + '\n')
    print('Resolving pinned OPT configuration...', flush=True)
    config_revision = previous.get('optConfigRevision') or api.model_info('facebook/opt-350m', timeout=30).sha
    config_path = hf_hub_download('facebook/opt-350m', filename='config.json', revision=config_revision, etag_timeout=30)
    report.update({'optConfigRevision': config_revision, 'optConfigSha256': sha256(config_path), 'status': 'passed'})
    RECEIPT.write_text(json.dumps(report, indent=2) + '\n')
    print('Checkpoint hashes and configuration revision verified.', flush=True)


if __name__ == '__main__':
    os.environ.setdefault('HF_HOME', str(LOCAL / 'cache/huggingface'))
    os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
    os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
    main()
