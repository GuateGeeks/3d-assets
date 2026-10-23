"""Stdlib contract tests. These do not claim to exercise Blender."""
import importlib.util
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

MODULE = Path(__file__).resolve().parents[1] / 'create.py'
spec = importlib.util.spec_from_file_location('creation_cli', MODULE)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class Contracts(unittest.TestCase):
    def setUp(self):
        temp_root = MODULE.parent / '.local' / 'tests'
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='creation test spaces ', dir=temp_root)
        self.root = Path(self.temp.name)
        self.brief = json.loads((MODULE.parent / 'examples/canary.json').read_text())

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, args):
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            code = cli.main(args + ['--runs-root', str(self.root / 'runs with spaces')])
        return code, output.getvalue(), error.getvalue()

    def test_invalid_dimensions_and_budgets(self):
        for dims in ([0, 1, 1], [True, 1, 1], [float('nan'), 1, 1], [1, 1], [101, 1, 1]):
            with self.subTest(dims=dims), self.assertRaises(ValueError):
                cli.validate_brief({**self.brief, 'dimensionsM': dims})
        with self.assertRaises(ValueError):
            cli.validate_brief({**self.brief, 'budgets': {'triangles': 6001}})

    def test_provider_does_not_accept_credentials(self):
        for provider in ({'mode': 'configured', 'apiKey': 'secret'},
                         {'mode': 'configured', 'endpoint': 'https://user:secret@provider.invalid'},
                         {'mode': 'configured', 'credentialEnv': 'bad=value'}):
            with self.assertRaises(ValueError):
                cli.validate_brief({**self.brief, 'provider': provider})

    def test_slug_and_provenance_required(self):
        with self.assertRaises(ValueError):
            cli.validate_brief({**self.brief, 'assetId': '../escape'})
        with self.assertRaises(ValueError):
            cli.validate_brief({**self.brief, 'provenance': {'license': 'CC0-1.0'}})
        for slug in (17, True, None):
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                cli.validate_brief({**self.brief, 'assetId': slug})
        for budgets in ([], None, '6000'):
            with self.subTest(budgets=budgets), self.assertRaises(ValueError):
                cli.validate_brief({**self.brief, 'budgets': budgets})

    def test_brief_runs_unique_input_unchanged(self):
        source = self.root / 'my brief.json'
        source.write_text(json.dumps(self.brief))
        original = source.read_bytes()
        code1, out1, _ = self.run_cli(['brief', '--input', str(source)])
        code2, out2, _ = self.run_cli(['brief', '--input', str(source)])
        self.assertEqual((code1, code2), (0, 0))
        run1 = Path(json.loads(out1)['run'])
        run2 = Path(json.loads(out2)['run'])
        self.assertNotEqual(run1, run2)
        self.assertEqual(source.read_bytes(), original)
        _, data = cli.load_run(run1)
        self.assertEqual(data['visual'], 'NOT_RUN')
        self.assertEqual(data['status'], 'BLOCKED')
        self.assertEqual(data['providerExecution'], 'NOT_RUN')
        with self.assertRaises(FileExistsError):
            cli.write_json(run1 / 'brief.json', self.brief)

    def test_tampered_artifact_rejected(self):
        run, manifest = cli.new_run(self.root, 'test')
        cli.write_json(run / 'brief.json', self.brief)
        with redirect_stdout(io.StringIO()):
            cli.finish(run, manifest)
        (run / 'brief.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            cli.load_run(run)

    def test_tampered_manifest_rejected(self):
        run, manifest = cli.new_run(self.root, 'test')
        with redirect_stdout(io.StringIO()):
            cli.finish(run, manifest)
        (run / 'manifest.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'COMPLETE'):
            cli.load_run(run)

    def test_path_traversal_rejected(self):
        run = self.root / 'run'
        run.mkdir()
        outside = self.root / 'outside.json'
        outside.write_text('{}')
        for candidate in ('../outside.json', str(outside.resolve())):
            with self.assertRaises(ValueError):
                cli.artifact(run, candidate)

    def test_missing_backend_file_is_explicit_error(self):
        code, _, err = self.run_cli(['doctor', '--bpy-python', str(self.root / 'missing python')])
        self.assertEqual(code, 2)
        self.assertIn('creation-lab:', err)

    def test_incomplete_run_not_accepted(self):
        run, _ = cli.new_run(self.root, 'test')
        with self.assertRaises(OSError):
            cli.load_run(run)

    def test_reopen_invariants_detect_change_with_same_budget(self):
        # Contract data, not a mocked Blender execution. A budget alone cannot
        # detect moved geometry or a changed material after loading a saved file.
        before = {'triangles': 12, 'materialCount': 1, 'bboxMinM': [0, 0, 0],
                  'bboxMaxM': [0.1, 0.2, 0.3], 'transformsApplied': True,
                  'geometrySignature': 'original', 'surfaceSignature': 'surface', 'materialValues': [
                      {'name': 'Paint', 'baseColor': [0.1, 0.2, 0.3, 1], 'roughness': 0.5, 'metallic': 0}]}
        self.assertTrue(all(c['status'] == 'PASS' for c in cli.invariant_checks(before, before, 'reopen')))
        mutations = [('bounds', lambda item: item['bboxMinM'].__setitem__(0, 0.01)),
                     ('transformsApplied', lambda item: item.__setitem__('transformsApplied', False)),
                     ('orientationGeometry', lambda item: item.__setitem__('geometrySignature', 'rotated')),
                     ('orientedMaterialSurface', lambda item: item.__setitem__('surfaceSignature', 'swapped')),
                     ('materialAppearance', lambda item: item['materialValues'][0].__setitem__('roughness', 0.9))]
        for expected, change in mutations:
            after = copy.deepcopy(before)
            change(after)
            with self.subTest(expected=expected):
                checks = {c['name']: c['status'] for c in cli.invariant_checks(before, after, 'reopen')}
                self.assertEqual(checks['reopen.' + expected], 'FAIL')


if __name__ == '__main__':
    unittest.main()
