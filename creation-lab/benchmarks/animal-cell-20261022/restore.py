"""Verify and restore the archived pilot runs using only the Python standard library.

The archives preserve historical failures as well as successes. Restoring evidence
does not promote a candidate or repeat its biological/visual review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

BASE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = BASE.parents[1] / '.local/benchmarks/animal-cell-20261022'
RUN_ID = re.compile(r'[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}')
DIGEST = re.compile(r'[0-9a-f]{64}')
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
            *(f'LPT{i}' for i in range(1, 10))}
TEXT_SUFFIXES = {'.py', '.json', '.log', '.md', '.txt', '.toml', '.yaml', '.yml',
                 '.env', '.sh', '.ps1', '.cmd'}
SECRET_PATTERNS = {
    'private-key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'),
    'aws-access-key': re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'github-token': re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b'),
    'openai-token': re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{30,}\b'),
    'google-api-key': re.compile(rb'\bAIza[0-9A-Za-z_-]{35}\b'),
    'bearer-token': re.compile(rb'\bBearer\s+[A-Za-z0-9._~+-]{24,}', re.I),
    'assigned-credential': re.compile(rb'''["']?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password)["']?\s*[:=]\s*["'][A-Za-z0-9_./+=~-]{24,}["']''', re.I),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(name: str) -> PurePosixPath:
    """Accept file names with the same unambiguous meaning on Windows and POSIX."""
    if not isinstance(name, str) or not name or any(c in name for c in '\\:\x00<>"|?*'):
        raise ValueError(f'Unsafe archive path: {name!r}')
    path = PurePosixPath(name)
    parts = name.split('/')
    if path.is_absolute() or any(not part or part in {'.', '..'} or
                               part.endswith(('.', ' ')) or
                               part.split('.')[0].upper() in RESERVED for part in parts):
        raise ValueError(f'Unsafe archive path: {name!r}')
    return path


def checked_target(root: Path, name: str) -> Path:
    relative = safe_name(name)
    target = root.joinpath(*relative.parts)
    if root.is_symlink():
        raise ValueError(f'Symlink output directory is not allowed: {root}')
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Path escapes destination: {name}')
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f'Symlink destination is not allowed: {current}')
    return target


def load_index(fixtures: Path) -> list[dict]:
    index = json.loads((fixtures / 'index.json').read_text(encoding='utf-8'))
    if index.get('schemaVersion') != 1 or not isinstance(index.get('runs'), list) or not index['runs']:
        raise ValueError('Unsupported or empty fixture index')
    seen = set()
    for entry in index['runs']:
        condition, run_id = entry.get('condition'), entry.get('runId')
        if condition not in list('ABCDEF') or not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
            raise ValueError('Invalid fixture condition/run ID')
        expected = f'{condition}-{run_id}.zip'
        if entry.get('file') != expected or expected in seen:
            raise ValueError('Duplicate or unexpected fixture filename')
        seen.add(expected)
        if not isinstance(entry.get('sha256'), str) or not DIGEST.fullmatch(entry['sha256']):
            raise ValueError('Invalid fixture digest')
        for key in ('bytes', 'uncompressedBytes', 'fileCount'):
            if not isinstance(entry.get(key), int) or isinstance(entry[key], bool) or entry[key] <= 0:
                raise ValueError(f'Invalid fixture {key}')
    return index['runs']


def verify_archive(fixtures: Path, entry: dict) -> dict[str, str]:
    archive = checked_target(fixtures, entry['file'])
    if archive.stat().st_size != entry['bytes'] or sha256(archive) != entry['sha256']:
        raise ValueError(f'Archive checksum mismatch: {archive.name}')
    digests = {}
    metadata = {}
    total_size = 0
    case_names = set()
    with zipfile.ZipFile(archive) as package:
        for info in package.infolist():
            safe_name(info.filename)
            if info.is_dir() or info.filename.casefold() in case_names:
                raise ValueError(f'Directory/duplicate member: {info.filename}')
            case_names.add(info.filename.casefold())
            mode = stat.S_IFMT(info.external_attr >> 16)
            if mode not in (0, stat.S_IFREG):
                raise ValueError(f'Non-regular archive member: {info.filename}')
            if info.flag_bits & 1:
                raise ValueError('Encrypted archive members are unsupported')
            digest = hashlib.sha256()
            captured = bytearray() if info.filename in {'manifest.json', 'COMPLETE'} else None
            scan_text = PurePosixPath(info.filename).suffix.lower() in TEXT_SUFFIXES
            previous = b''
            with package.open(info) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
                    if scan_text:
                        text = previous + chunk
                        for kind, pattern in SECRET_PATTERNS.items():
                            if pattern.search(text):
                                raise ValueError(f'Credential pattern ({kind}) in {archive.name}: {info.filename}')
                        previous = text[-4096:]
                    if captured is not None:
                        if len(captured) + len(chunk) > 1024 * 1024:
                            raise ValueError('Oversized manifest or completion marker')
                        captured.extend(chunk)
            digests[info.filename] = digest.hexdigest()
            if captured is not None:
                metadata[info.filename] = bytes(captured)
            total_size += info.file_size
    if len(digests) != entry['fileCount'] or total_size != entry['uncompressedBytes']:
        raise ValueError(f'Archive inventory mismatch: {archive.name}')
    if 'manifest.json' not in metadata:
        raise ValueError('Missing historical run manifest')
    manifest = json.loads(metadata['manifest.json'])
    if manifest.get('runId') != entry['runId'] or manifest.get('condition', {}).get('id') != entry['condition']:
        raise ValueError('Manifest identity does not match fixture index')
    if digests['manifest.json'] != entry.get('manifestSha256'):
        raise ValueError('Manifest digest does not match fixture index')
    artifacts = manifest.get('artifacts')
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError('Missing manifest artifact inventory')
    for name, digest in artifacts.items():
        safe_name(name)
        if digests.get(name) != digest:
            raise ValueError(f'Manifest artifact mismatch: {archive.name}: {name}')
    complete = metadata.get('COMPLETE')
    if bool(complete is not None) != entry.get('complete'):
        raise ValueError('Completion marker presence differs from fixture index')
    if complete is not None and complete.decode('ascii').strip() != digests['manifest.json']:
        raise ValueError('COMPLETE does not match the historical manifest')
    return digests


def restore(fixtures: Path, output: Path, check: bool = False) -> dict:
    entries = load_index(fixtures)
    plans = [(entry, verify_archive(fixtures, entry)) for entry in entries]
    report = {'schemaVersion': 1, 'status': 'PASS', 'mode': 'check' if check else 'restore',
              'runs': len(plans), 'files': sum(len(hashes) for _, hashes in plans),
              'restoredFiles': 0, 'unchangedFiles': 0, 'obviousCredentialScan': 'PASS'}
    if check:
        return report
    # Validate every collision before writing any run. Never replace changed evidence.
    for entry, hashes in plans:
        prefix = f"{entry['condition']}/{entry['runId']}"
        for name, digest in hashes.items():
            target = checked_target(output, prefix + '/' + name)
            if target.exists():
                if not target.is_file() or sha256(target) != digest:
                    raise ValueError(f'Refusing to overwrite different evidence: {target}')
                report['unchangedFiles'] += 1
    for entry, hashes in plans:
        prefix = f"{entry['condition']}/{entry['runId']}"
        with zipfile.ZipFile(fixtures / entry['file']) as package:
            # A visible COMPLETE marker is the last write, after all archived files.
            for name in sorted(hashes, key=lambda value: (value == 'COMPLETE', value)):
                target = checked_target(output, prefix + '/' + name)
                if target.exists():
                    if not target.is_file() or sha256(target) != hashes[name]:
                        raise ValueError(f'Evidence changed during restoration: {target}')
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                checked_target(output, prefix + '/' + name)
                with package.open(name) as source, target.open('xb') as destination:
                    for chunk in iter(lambda: source.read(1024 * 1024), b''):
                        destination.write(chunk)
                if sha256(target) != hashes[name]:
                    raise ValueError(f'Restored file digest mismatch: {target}')
                report['restoredFiles'] += 1
    report['output'] = str(output.resolve())
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=BASE / 'fixtures', help='Directory with index.json and its ZIP files')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT, help='Destination benchmark run root')
    parser.add_argument('--check', action='store_true', help='Verify all fixture hashes/manifests without writing files')
    args = parser.parse_args()
    try:
        print(json.dumps(restore(args.fixtures, args.output, args.check), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
