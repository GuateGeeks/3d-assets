"""Install the pinned Linux UniRig profile without changing system Python or drivers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

from bootstrap_uv import bootstrap

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / 'lab'
LOCAL = LAB / '.local'
PROFILE = LAB / 'envs/unirig.profile.json'


def environment():
    env = os.environ.copy()
    env.update({
        'UV_CACHE_DIR': str(LOCAL / 'cache/uv'),
        'UV_PYTHON_INSTALL_DIR': str(LOCAL / 'python'),
        'UV_PYTHON_BIN_DIR': str(LOCAL / 'bin'),
        'HF_HOME': str(LOCAL / 'cache/huggingface'),
        'XDG_CACHE_HOME': str(LOCAL / 'cache'),
        'MPLCONFIGDIR': str(LOCAL / 'cache/matplotlib'),
        'HF_HUB_DISABLE_TELEMETRY': '1', 'HF_HUB_DISABLE_XET': '1',
        'WANDB_MODE': 'disabled', 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
        'MAX_JOBS': '2', 'UV_NO_PROGRESS': '1', 'PYTHONUNBUFFERED': '1',
    })
    return env


def run(args, cwd=ROOT, capture=False):
    print('+', ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), cwd=cwd, env=environment(),
                          check=True, text=True, stdout=subprocess.PIPE if capture else None).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages-only', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'linux' or os.uname().machine != 'x86_64':
        parser.error('This profile requires Linux x86_64 (use the WSL launcher on Windows)')
    profile = json.loads(PROFILE.read_text())
    LOCAL.mkdir(parents=True, exist_ok=True)
    uv = bootstrap(profile['uv'])
    run([uv, 'python', 'install', profile['python']])
    venv = LOCAL / 'envs/unirig'
    python = venv / 'bin/python'
    if not python.exists():
        run([uv, 'venv', '--python', profile['python'], venv])
    else:
        actual = run([python, '-c', 'import platform;print(platform.python_version())'], capture=True).strip()
        if actual != profile['python']:
            raise RuntimeError('Existing environment has a different Python version; preserve and inspect it')
    repo = LOCAL / 'repos/UniRig'
    if not repo.exists():
        repo.parent.mkdir(parents=True, exist_ok=True)
        run(['git', 'clone', '--filter=blob:none', '--no-checkout', profile['repository'], repo])
        run(['git', 'checkout', '--detach', profile['commit']], cwd=repo)
    else:
        if run(['git', 'rev-parse', 'HEAD'], cwd=repo, capture=True).strip() != profile['commit']:
            raise RuntimeError('Existing UniRig checkout differs from the pinned commit')
        if run(['git', 'status', '--porcelain'], cwd=repo, capture=True).strip():
            raise RuntimeError('Existing UniRig checkout has local changes; preserve and inspect them')
    constraints = LAB / 'envs/unirig.constraints.txt'
    common = [uv, 'pip', 'install', '--python', python, '-c', constraints]
    lock = LAB / 'envs/unirig-linux-py311.lock.txt'
    if lock.exists():
        run([uv, 'pip', 'sync', '--python', python, '--index-url', profile['torchIndex'],
             '--extra-index-url', 'https://pypi.org/simple', '--index-strategy', 'unsafe-best-match',
             '--find-links', profile['pygIndex'], lock])
    else:
        run([uv, 'pip', 'install', '--python', python, '--index-url', profile['torchIndex'],
             f"torch=={profile['torch']}", f"torchvision=={profile['torchvision']}"])
        # Install the official prebuilt wheel, avoiding an unbounded CUDA source build.
        run([uv, 'pip', 'install', '--python', python, '--no-deps', profile['flashAttentionWheel']])
        requirements = repo / 'requirements.txt'
        filtered = LOCAL / 'unirig.requirements.txt'
        filtered.write_text('\n'.join(line for line in requirements.read_text().splitlines()
                                      if line.strip() != 'flash_attn') + '\n')
        run(common + ['--extra-index-url', profile['torchIndex'], '--index-strategy', 'unsafe-best-match',
            '--find-links', profile['pygIndex'], '-r', filtered,
            'spconv-cu124==2.3.8', 'torch-scatter==2.1.2+pt25cu124',
            'torch-cluster==1.6.3+pt25cu124', 'numpy==1.26.4', 'packaging', 'setuptools<81'])
    run([python, LAB / 'scripts/fix_bpy_metadata.py'])
    run([sys.executable, LAB / 'scripts/fetch_examples.py'])
    run([uv, 'pip', 'check', '--python', python])
    frozen = run([uv, 'pip', 'freeze', '--python', python], capture=True)
    lock.write_text('# Linux x86_64, Python ' + profile['python'] + ', CUDA 12.4\n' + frozen)
    receipt = {
        'schemaVersion': 1, 'engine': 'unirig', 'status': 'packages_installed',
        'recordedAt': datetime.now(timezone.utc).isoformat(),
        'commit': profile['commit'], 'python': profile['python'],
        'profileSha256': hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
        'lockSha256': hashlib.sha256(lock.read_bytes()).hexdigest(),
        'upstreamRequirementsSha256': hashlib.sha256((repo / 'requirements.txt').read_bytes()).hexdigest(),
        'cudaVerified': False, 'inferenceVerified': False,
    }
    reports = LAB / 'reports'
    reports.mkdir(parents=True, exist_ok=True)
    (reports / 'unirig-install.json').write_text(json.dumps(receipt, indent=2) + '\n')
    run([python, LAB / 'scripts/collect_provenance.py'])
    if not args.packages_only:
        run([python, LAB / 'scripts/probe_unirig.py'])
        run([python, LAB / 'scripts/download_models.py'])
    print('UniRig packages installed.' if args.packages_only else 'UniRig packages, GPU checks and model cache ready.', flush=True)


if __name__ == '__main__':
    main()
