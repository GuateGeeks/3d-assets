"""Restore the locked optional MCP runtime without changing global Python or Codex."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import tempfile

LAB = Path(__file__).resolve().parents[1]


def check_profile():
    if (sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 12)
            or os.name != 'nt' or platform.machine().lower() not in {'amd64', 'x86_64'}
            or struct.calcsize('P') != 8):
        raise ValueError('This wheel lock requires Windows x64 CPython 3.12. '
                         'The creation CLI remains usable without MCP.')


def restore(target, lab=LAB):
    """Publish only a fully installed, importable runtime; never overwrite a target."""
    target = Path(target).absolute()
    if target.exists() or target.is_symlink():
        raise ValueError('Runtime target already exists; preserve active sessions. '
                         'Use --target with a new directory for an independent restore.')
    subprocess.run([sys.executable, str(lab / 'registry/verify_sources.py')], check=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    # A unique sibling permits a final rename on the same filesystem.
    with tempfile.TemporaryDirectory(prefix='.mcp-restore-', dir=target.parent) as work:
        staged = Path(work) / 'runtime'
        subprocess.run([sys.executable, '-m', 'pip', '--isolated', 'install',
                        '--disable-pip-version-check', '--require-hashes',
                        '--only-binary=:all:', '--no-compile', '--target', str(staged),
                        '-r', str(lab / 'registry/mcp-runtime.requirements.txt')], check=True)
        shutil.copytree(lab / 'vendor/blender-lab-mcp/source/mcp',
                        staged / 'official-blender-mcp',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        probe = ("import site,sys; from pathlib import Path; "
                 "p=Path(sys.argv[1]); site.addsitedir(str(p)); "
                 "sys.path.insert(0,str(p/'official-blender-mcp')); "
                 "import blmcp; from mcp.server.fastmcp import FastMCP; "
                 "assert (p/'official-blender-mcp/blmcp/data/prompts.yml').is_file()")
        subprocess.run([sys.executable, '-I', '-c', probe, str(staged)], check=True,
                       env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        # Recheck so another install or active session is never replaced.
        if target.exists() or target.is_symlink():
            raise ValueError('Runtime target appeared during restore; refusing replacement')
        staged.rename(target)
    return {'status': 'PASS', 'runtime': str(target), 'profile': 'windows-cp312-x64',
            'blenderExecuted': False, 'codexConfigurationChanged': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, default=LAB / 'vendor/.runtime',
                        help='New runtime directory; custom targets are for verification only')
    args = parser.parse_args()
    try:
        check_profile()
        print(json.dumps(restore(args.target)))
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print('Runtime restore failed: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
