"""Opt-in real Blender topology regression. Never replaced by a mock backend."""
import os
from pathlib import Path
import subprocess
import unittest


@unittest.skipUnless(os.environ.get('CREATION_TEST_BLENDER'), 'Set CREATION_TEST_BLENDER to opt into real Blender')
class BlenderIntegration(unittest.TestCase):
    def test_material_assignment_and_winding(self):
        worker = Path(__file__).resolve().parents[1] / 'scripts/blender_worker.py'
        result = subprocess.run([os.environ['CREATION_TEST_BLENDER'], '--background', '--factory-startup',
                                 '--disable-autoexec', '--threads', '2', '--python', str(worker), '--', 'surface-test'],
                                capture_output=True, text=True, timeout=60,
                                env={**os.environ, 'CUDA_VISIBLE_DEVICES': ''})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"materialSwapDetected": true', result.stdout)
        self.assertIn('"windingReversalDetected": true', result.stdout)

    def test_normal_seams_and_real_hole(self):
        worker = Path(__file__).resolve().parents[1] / 'scripts/blender_worker.py'
        result = subprocess.run([os.environ['CREATION_TEST_BLENDER'], '--background', '--factory-startup',
                                 '--disable-autoexec', '--threads', '2', '--python', str(worker), '--', 'topology-test'],
                                capture_output=True, text=True, timeout=60,
                                env={**os.environ, 'CUDA_VISIBLE_DEVICES': ''})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"weldedClosedEdges": 0', result.stdout)
        self.assertIn('CREATION_TOPOLOGY=', result.stdout)


if __name__ == '__main__':
    unittest.main()
