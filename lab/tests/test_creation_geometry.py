"""Real bpy CPU contract tests; skip only when the isolated lab Python is absent."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / 'lab/.local/envs/unirig/bin/python'
WORKER = ROOT / 'lab/scripts/creation_geometry.py'
FIXTURE = ROOT / 'lab/tests/creation_geometry_fixture.py'


@unittest.skipUnless(PYTHON.is_file(), 'Requires the already installed CPU bpy environment')
class CreationGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='creation-geometry-', dir=ROOT / 'lab/.local/tmp')
        cls.path = Path(cls.temp.name)
        cls.source = cls.path / 'source.glb'
        cls.run_worker(FIXTURE, 'static', '--output', cls.source)
        cls.source_hash = hashlib.sha256(cls.source.read_bytes()).hexdigest()
        cls.run_worker(WORKER, 'prepare', '--input', cls.source, '--output-dir', cls.path / 'prepared', '--report', cls.path / 'prepare-report.json')
        cls.geometry = cls.path / 'prepared/geometry.json'

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def run_worker(cls, script, *args, expected=0):
        result = subprocess.run([str(PYTHON), str(script), *map(str, args)], cwd=ROOT, text=True, capture_output=True, timeout=120)
        if result.returncode != expected:
            evidence = ''
            if '--report' in args:
                report = Path(args[args.index('--report') + 1])
                if report.exists():
                    data = json.loads(report.read_text())
                    evidence = json.dumps(data.get('checks', data), indent=2)
            raise AssertionError(f'Expected {expected}, got {result.returncode}: {result.stdout}\n{result.stderr}\n{evidence}')
        return result

    def test_roundtrip_preserves_hierarchy_world_space_materials_uv_texture_and_weights(self):
        prepared = json.loads(self.geometry.read_text())
        self.assertEqual(prepared['status'], 'passed')
        self.assertEqual(prepared['source']['meshes'], 2)
        self.assertEqual(len(prepared['source']['materials']), 2)
        self.assertEqual(prepared['source']['textureCount'], 1)
        self.assertAlmostEqual(max(prepared['source']['dimensionsM']), 0.3, places=6)
        self.assertAlmostEqual(max(prepared['prepared']['dimensionsM']), 2.0, places=5)
        rigged = self.path / 'rigged.glb'
        self.run_worker(FIXTURE, 'weighted', '--input', self.path / 'prepared/prepared.glb', '--output', rigged)
        report = self.path / 'restore-report.json'
        self.run_worker(WORKER, 'restore', '--input', rigged, '--geometry', self.geometry, '--output-dir', self.path / 'restored', '--report', report)
        result = json.loads(report.read_text())
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['weights']['vertices'], result['weights']['weightedVertices'])
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.source_hash)

    def test_rejects_unweighted_component_and_appearance_damage(self):
        for failure in ['unweighted', 'uv', 'material']:
            with self.subTest(failure=failure):
                rigged = self.path / (failure + '.glb')
                self.run_worker(FIXTURE, 'weighted', '--input', self.path / 'prepared/prepared.glb', '--output', rigged, '--broken', failure)
                report = self.path / (failure + '-report.json')
                self.run_worker(WORKER, 'restore', '--input', rigged, '--geometry', self.geometry, '--output-dir', self.path / (failure + '-restored'), '--report', report, expected=1)
                result = json.loads(report.read_text())
                self.assertEqual(result['status'], 'invalid_output')
                self.assertTrue(any(check['status'] == 'failed' for check in result['checks']))

    def test_rejects_wrong_inverse_without_mutating_input(self):
        geometry = json.loads(self.geometry.read_text())
        geometry['normalization']['inverse'][0][3] += 0.1
        damaged = self.path / 'wrong-inverse.json'
        damaged.write_text(json.dumps(geometry))
        report = self.path / 'inverse-report.json'
        self.run_worker(WORKER, 'restore', '--input', self.source, '--geometry', damaged, '--output-dir', self.path / 'wrong-inverse', '--report', report, expected=1)
        self.assertIn('inverse', json.loads(report.read_text())['error'])

    def test_rejects_swapped_texture_routing_with_unchanged_images_and_linked_sockets(self):
        report = self.path / 'routing-regression.json'
        self.run_worker(FIXTURE, 'appearance-regression', '--broken', 'routing', '--output', report)
        result = json.loads(report.read_text())
        self.assertTrue(result['baselineAccepted'])
        self.assertTrue(result['coordinatesAndUvUnchanged'])
        self.assertEqual(result['textureImageCount'], 2)
        self.assertTrue(result['texturePixelsUnchanged'])
        self.assertTrue(result['bothSocketsStillLinked'])
        self.assertFalse(result['materialsEqual'])
        self.assertFalse(result['mutationAccepted'])

    def test_rejects_flat_to_smooth_normals_with_unchanged_surface_positions_and_materials(self):
        report = self.path / 'normals-regression.json'
        self.run_worker(FIXTURE, 'appearance-regression', '--broken', 'normals', '--output', report)
        result = json.loads(report.read_text())
        self.assertTrue(result['baselineAccepted'])
        self.assertTrue(result['coordinatesAndUvUnchanged'])
        self.assertTrue(result['materialsEqual'])
        self.assertTrue(result['texturePixelsUnchanged'])
        self.assertTrue(result['normalsChanged'])
        self.assertFalse(result['mutationAccepted'])
        self.assertIn('shading normals', result['reason'])


if __name__ == '__main__':
    unittest.main()
