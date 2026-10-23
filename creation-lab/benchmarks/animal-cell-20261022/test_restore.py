"""Behavioral checks for portable evidence restoration; no Blender is required."""
import hashlib
import importlib.util
import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('cell_restore', Path(__file__).with_name('restore.py'))
restore = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(restore)
RUN_ID = '20261022T231712Z-01df29e7'


def digest(data):
    return hashlib.sha256(data).hexdigest()


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.fixtures = self.root / 'fixtures'
        self.fixtures.mkdir()
        self.output = self.root / 'output'

    def fixture(self, extra=None, marker=True, broken_manifest=False):
        files = {'asset.glb': b'glTF-original-evidence'}
        files.update(extra or {})
        manifest = {'runId': RUN_ID, 'condition': {'id': 'A'}, 'status': 'FAIL',
                    'artifacts': {name: digest(data) for name, data in files.items()}}
        if broken_manifest:
            manifest['artifacts']['asset.glb'] = '0' * 64
        files['manifest.json'] = json.dumps(manifest).encode()
        if marker:
            files['COMPLETE'] = (digest(files['manifest.json']) + '\n').encode()
        path = self.fixtures / f'A-{RUN_ID}.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for name, data in files.items():
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, data)
        entry = {'condition': 'A', 'runId': RUN_ID, 'file': path.name,
                 'sha256': restore.sha256(path), 'bytes': path.stat().st_size,
                 'uncompressedBytes': sum(map(len, files.values())), 'fileCount': len(files),
                 'manifestSha256': digest(files['manifest.json']), 'complete': marker}
        self.write_index(entry)
        return path, entry

    def write_index(self, entry):
        (self.fixtures / 'index.json').write_text(json.dumps({'schemaVersion': 1, 'runs': [entry]}))

    def test_restore_is_exact_and_idempotent_and_preserves_failed_evidence(self):
        self.fixture()
        first = restore.restore(self.fixtures, self.output)
        self.assertEqual(first['restoredFiles'], 3)
        self.assertEqual((self.output / 'A' / RUN_ID / 'asset.glb').read_bytes(), b'glTF-original-evidence')
        second = restore.restore(self.fixtures, self.output)
        self.assertEqual(second['restoredFiles'], 0)
        self.assertEqual(second['unchangedFiles'], 3)

    def test_check_does_not_create_output(self):
        self.fixture()
        self.assertEqual(restore.restore(self.fixtures, self.output, check=True)['status'], 'PASS')
        self.assertFalse(self.output.exists())

    def test_tampered_zip_rejected_before_writes(self):
        archive, _ = self.fixture()
        with archive.open('ab') as stream:
            stream.write(b'tampering')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            restore.restore(self.fixtures, self.output)
        self.assertFalse(self.output.exists())

    def test_changed_existing_file_is_preserved(self):
        self.fixture()
        target = self.output / 'A' / RUN_ID / 'asset.glb'
        target.parent.mkdir(parents=True)
        target.write_bytes(b'user changes')
        with self.assertRaisesRegex(ValueError, 'Refusing to overwrite'):
            restore.restore(self.fixtures, self.output)
        self.assertEqual(target.read_bytes(), b'user changes')
        self.assertFalse((target.parent / 'COMPLETE').exists())

    def test_traversal_with_valid_index_hash_is_rejected(self):
        self.fixture({'../escaped.txt': b'escape'})
        with self.assertRaisesRegex(ValueError, 'Unsafe archive path'):
            restore.restore(self.fixtures, self.output)
        self.assertFalse((self.root / 'escaped.txt').exists())

    def test_windows_alias_paths_are_rejected(self):
        for name in ('C:/secret', 'foo\\bar', '/absolute', 'CON.txt', 'x./data', 'a//b', 'a:b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                restore.safe_name(name)

    def test_symlink_archive_member_rejected(self):
        archive, entry = self.fixture()
        with zipfile.ZipFile(archive, 'a') as package:
            info = zipfile.ZipInfo('link')
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            package.writestr(info, b'/tmp')
        entry.update(sha256=restore.sha256(archive), bytes=archive.stat().st_size,
                     fileCount=entry['fileCount'] + 1, uncompressedBytes=entry['uncompressedBytes'] + 4)
        self.write_index(entry)
        with self.assertRaisesRegex(ValueError, 'Non-regular archive member'):
            restore.restore(self.fixtures, self.output)

    def test_existing_symlink_destination_is_rejected(self):
        self.fixture()
        outside = self.root / 'outside'
        outside.mkdir()
        self.output.mkdir()
        try:
            (self.output / 'A').symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('This environment cannot create symlinks')
        with self.assertRaisesRegex(ValueError, 'escapes destination|Symlink destination'):
            restore.restore(self.fixtures, self.output)
        self.assertEqual(list(outside.iterdir()), [])

    def test_manifest_mismatch_rejected(self):
        self.fixture(broken_manifest=True)
        with self.assertRaisesRegex(ValueError, 'Manifest artifact mismatch'):
            restore.restore(self.fixtures, self.output)

    def test_incomplete_run_without_marker_is_not_given_one(self):
        self.fixture(marker=False)
        restore.restore(self.fixtures, self.output)
        self.assertFalse((self.output / 'A' / RUN_ID / 'COMPLETE').exists())

    def test_credential_pattern_rejected_without_exposing_value(self):
        secret = 'ghp_' + 'a' * 36
        self.fixture({'build.log': secret.encode()})
        with self.assertRaisesRegex(ValueError, 'Credential pattern') as error:
            restore.restore(self.fixtures, self.output)
        self.assertNotIn(secret, str(error.exception))


if __name__ == '__main__':
    unittest.main()
