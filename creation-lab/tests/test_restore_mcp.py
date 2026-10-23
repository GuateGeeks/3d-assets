"""Installer failures must not publish a partial runtime or replace active sessions."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('restore_mcp', Path(__file__).resolve().parents[1] / 'registry/restore_mcp_runtime.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RestoreRuntimeTests(unittest.TestCase):
    def test_existing_runtime_is_preserved_without_subprocesses(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'runtime'
            target.mkdir()
            marker = target / 'active-session'
            marker.write_text('owned')
            with patch.object(MODULE.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'already exists'):
                    MODULE.restore(target)
                run.assert_not_called()
            self.assertEqual(marker.read_text(), 'owned')

    def test_pip_failure_leaves_no_partial_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'runtime'
            with patch.object(MODULE.subprocess, 'run', side_effect=[None, subprocess.CalledProcessError(1, 'pip')]):
                with self.assertRaises(subprocess.CalledProcessError):
                    MODULE.restore(target)
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_wrong_platform_rejected(self):
        with patch.object(MODULE.os, 'name', 'posix'):
            with self.assertRaisesRegex(ValueError, 'Windows x64 CPython 3.12'):
                MODULE.check_profile()


if __name__ == '__main__':
    unittest.main()
