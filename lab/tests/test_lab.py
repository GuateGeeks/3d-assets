"""Hardware-independent checks for isolation, failure reporting and publication scanning."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('rig_lab', ROOT / 'lab/lab.py')
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


class LaboratoryTests(unittest.TestCase):
    def setUp(self):
        self.report_patch = patch.object(lab, 'REPORTS', lab.LOCAL / 'test-reports')
        self.report_patch.start()
        self.addCleanup(self.report_patch.stop)

    def test_lock_rejects_second_process_and_releases(self):
        code = "import sys;sys.path.insert(0,'lab');import lab;\nwith lab.engine_lock(): print('acquired')"
        with lab.engine_lock():
            result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Another UniRig', result.stderr)
        result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_failure_is_recorded_and_missing_artifact_is_rejected(self):
        run = lab.Run('test')
        with self.assertRaises(lab.StageError):
            run.execute('fail', [sys.executable, '-c', "raise RuntimeError('intentional failure')"])
        self.assertNotEqual(run.report['stages'][0]['exitCode'], 0)
        with self.assertRaises(lab.StageError) as error:
            run.artifact(run.path / 'missing.fbx')
        self.assertEqual(error.exception.status, 'invalid_output')
        run.finish('dependency_error', 'Intentional test fixture')
        self.assertEqual(json.loads((run.path / 'run.json').read_text())['status'], 'dependency_error')

    def test_timeout_stops_child(self):
        run = lab.Run('test')
        with self.assertRaises(TimeoutError):
            run.execute('timeout', [sys.executable, '-c', 'import time;time.sleep(20)'], timeout=0.2)
        self.assertIsNotNone(run.report['stages'][0]['exitCode'])
        run.finish('timeout')

    def test_local_downloads_are_excluded_but_own_code_is_scanned(self):
        cache = ROOT / 'lab/.local/test-scan'
        cache.mkdir(parents=True, exist_ok=True)
        marker = 'chatgpt' + '-conversation:'
        ignored = cache / 'fixture.txt'
        scanned = ROOT / 'lab/tests/scan-fixture.txt'
        try:
            ignored.write_text(marker)
            result = subprocess.run([sys.executable, 'tools/check_site.py'], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            scanned.write_text(marker)
            result = subprocess.run([sys.executable, 'tools/check_site.py'], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('lab/tests/scan-fixture.txt', result.stderr)
        finally:
            ignored.unlink(missing_ok=True)
            scanned.unlink(missing_ok=True)

    def test_symlink_cannot_bypass_source_scan(self):
        cache = ROOT / 'lab/.local/test-scan'
        cache.mkdir(parents=True, exist_ok=True)
        target = cache / 'linked-fixture.txt'
        link = ROOT / 'lab/tests/linked-fixture.txt'
        try:
            target.write_text('chatgpt' + '-conversation:')
            link.symlink_to(target)
            result = subprocess.run([sys.executable, 'tools/check_site.py'], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Unlisted symlink', result.stderr)
        finally:
            link.unlink(missing_ok=True)
            target.unlink(missing_ok=True)

    def test_public_build_excludes_laboratory(self):
        for name in ['lab', 'derived', 'packs']:
            self.assertFalse((ROOT / '_site' / name).exists())


if __name__ == '__main__':
    unittest.main()
