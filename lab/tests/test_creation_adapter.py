"""Pure verifier contracts using synthetic records, never simulated Blender QA."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('creation_adapter_test', ROOT / 'lab/creation_adapter.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class CreationAdapterContracts(unittest.TestCase):
    def setUp(self):
        temp_root = ROOT / 'lab/.local/adapter-tests'
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='adapter spaces ', dir=temp_root)
        self.root = Path(self.temp.name)
        self.runs = self.root / 'creation-lab/.local/runs'
        self.runs.mkdir(parents=True)
        self.provenance = {'author': 'Fixture', 'origin': 'original', 'license': 'CC0-1.0'}
        self.axes = {'blender': {'up': '+Z', 'front': '-Y'}, 'gltf': {'up': '+Y', 'front': '+Z'}}
        self.dimensions = [0.18, 0.19, 0.3]
        self.bounds = {'min': [-0.09, -0.095, 0], 'max': [0.09, 0.095, 0.3]}
        self.source = self.runs / 'source'
        self.source.mkdir()
        for name, content in [('asset.glb', b'contract source bytes'), ('source.blend', b'contract editable bytes')]:
            (self.source / name).write_bytes(content)
        (self.source / 'renders').mkdir()
        for view in adapter.VIEWS:
            (self.source / 'renders' / (view + '.png')).write_bytes(('synthetic evidence ' + view).encode())
        brief = {'assetId': 'fixture-canary', 'provenance': self.provenance, 'budgets': {'triangles': 6000, 'materials': 2, 'textureSize': 2048}}
        adapter.write_json(self.source / 'brief.json', brief)
        adapter.write_json(self.source / 'metrics.json', {'source': {'dimensionsM': self.dimensions, 'bboxMinM': self.bounds['min'], 'bboxMaxM': self.bounds['max']}})
        self.close(self.source, 'canary', visual='NOT_RUN')
        self.review = self.runs / 'review'
        self.review.mkdir()
        adapter.write_json(self.review / 'review.json', {'decision': 'PASS', 'openedImages': True, 'reviewer': 'Contract fixture',
                           'sourceRun': self.ref(self.source), 'evidence': {view: adapter.sha256(self.source / 'renders' / (view + '.png')) for view in adapter.VIEWS}})
        self.close(self.review, 'review', parent=self.source, source=self.source)
        self.handoff = self.runs / 'handoff'
        self.handoff.mkdir()
        self.candidate = {'schemaVersion': 1, 'kind': 'creation-candidate', 'assetId': 'fixture-canary',
                          'sourceRun': self.ref(self.source), 'reviewRun': self.ref(self.review),
                          'asset': {'path': str(self.source / 'asset.glb'), 'sha256': adapter.sha256(self.source / 'asset.glb')},
                          'editable': {'path': str(self.source / 'source.blend'), 'sha256': adapter.sha256(self.source / 'source.blend')},
                          'qa': {'technical': 'PASS', 'visual': 'PASS', 'rights': 'PASS'}, 'eligibleForPromotion': True,
                          'units': 'm', 'dimensionsM': self.dimensions, 'bboxM': self.bounds, 'axes': self.axes,
                          'provenance': self.provenance, 'budgets': brief['budgets'], 'rigging': {'status': 'BLOCKED'}}
        adapter.write_json(self.handoff / 'candidate.json', self.candidate)
        self.close(self.handoff, 'handoff', parent=self.review, source=self.source)

    def tearDown(self):
        self.temp.cleanup()

    def ref(self, run):
        return {'path': str(run), 'manifestSha256': adapter.sha256(run / 'manifest.json')}

    def close(self, run, command, parent=None, source=None, visual='PASS'):
        artifacts = {path.relative_to(run).as_posix(): adapter.sha256(path) for path in run.rglob('*') if path.is_file() and path.name not in ('manifest.json', 'COMPLETE')}
        data = {'schemaVersion': 1, 'command': command, 'technical': 'PASS', 'visual': visual, 'rights': 'PASS',
                'status': 'PASS' if visual == 'PASS' else 'BLOCKED', 'artifacts': artifacts}
        if parent:
            data['parent'] = self.ref(parent)
        if source:
            data['sourceRun'] = self.ref(source)
        (run / 'manifest.json').write_text(json.dumps(data))
        (run / 'COMPLETE').write_text(adapter.sha256(run / 'manifest.json') + '\n')

    def rewrite_candidate(self, change):
        data = copy.deepcopy(self.candidate)
        change(data)
        (self.handoff / 'candidate.json').write_text(json.dumps(data))
        self.close(self.handoff, 'handoff', parent=self.review, source=self.source)

    def test_approved_chain_and_historical_rigging_block_accepted(self):
        result = adapter.verify_candidate(self.handoff / 'candidate.json', self.root)
        self.assertEqual(result['candidate']['assetId'], 'fixture-canary')
        self.assertEqual(len(result['chain']), 3)

    def test_unbound_candidate_rejected(self):
        self.candidate['qa']['visual'] = 'FAIL'
        (self.handoff / 'candidate.json').write_text(json.dumps(self.candidate))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            adapter.verify_candidate(self.handoff / 'candidate.json', self.root)

    def test_rehashed_false_gate_rejected(self):
        self.rewrite_candidate(lambda value: value['qa'].__setitem__('visual', 'NOT_RUN'))
        with self.assertRaisesRegex(ValueError, 'gates'):
            adapter.verify_candidate(self.handoff / 'candidate.json', self.root)

    def test_metadata_and_source_substitution_rejected(self):
        self.rewrite_candidate(lambda value: value.__setitem__('dimensionsM', [1, 1, 1]))
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            adapter.verify_candidate(self.handoff / 'candidate.json', self.root)

    def test_wrong_review_origin_rejected(self):
        data = adapter.read_json(self.review / 'review.json')
        data['sourceRun'] = self.ref(self.review)
        (self.review / 'review.json').write_text(json.dumps(data))
        self.close(self.review, 'review', parent=self.source, source=self.source)
        self.rewrite_candidate(lambda value: value.__setitem__('reviewRun', self.ref(self.review)))
        with self.assertRaisesRegex(ValueError, 'Visual review'):
            adapter.verify_candidate(self.handoff / 'candidate.json', self.root)

    def test_paths_reject_escape_and_bad_unc(self):
        for value in ('../outside', '/outside/file', '\\\\evil-server\\share\\file', '\\\\wsl.localhost\\OtherDistro\\etc\\file'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                adapter.canonical_reference(value, self.root)
        for value in ('../outside', '/outside', 'a\\b', 'C:/file'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                adapter.relative_name(value)

    def test_symlink_parent_rejected(self):
        link = self.root / 'alias'
        try:
            link.symlink_to(self.source, target_is_directory=True)
        except OSError:
            self.skipTest('Host does not permit test symlink creation')
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            adapter.safe_path(link / 'asset.glb', self.root)

    def test_missing_visual_evidence_rejected(self):
        data = adapter.read_json(self.review / 'review.json')
        del data['evidence']['wireframe']
        (self.review / 'review.json').write_text(json.dumps(data))
        self.close(self.review, 'review', parent=self.source, source=self.source)
        self.rewrite_candidate(lambda value: value.__setitem__('reviewRun', self.ref(self.review)))
        with self.assertRaisesRegex(ValueError, 'Visual review'):
            adapter.verify_candidate(self.handoff / 'candidate.json', self.root)

    def make_prepared(self):
        run = self.root / 'lab/.local/runs/ingested'
        run.mkdir(parents=True)
        receipt = adapter.copy_candidate(self.handoff / 'candidate.json', self.root, run)
        (run / 'prepared').mkdir()
        (run / 'adapter-code').mkdir()
        (run / 'adapter-code/scripts').mkdir()
        (run / 'adapter-code/scripts/creation_geometry.py').write_text('# Contract snapshot only')
        source = run / receipt['sourceOriginal']['file']
        (run / 'prepared/control.glb').write_bytes(source.read_bytes())
        (run / 'prepared/prepared.glb').write_bytes(b'unit contract only, not a Blender result')
        scale = 2 / max(self.dimensions)
        matrix = [[scale, 0, 0, 0], [0, scale, 0, 0], [0, 0, scale, 0], [0, 0, 0, 1]]
        inverse = [[1/scale, 0, 0, 0], [0, 1/scale, 0, 0], [0, 0, 1/scale, 0], [0, 0, 0, 1]]
        adapter.write_json(run / 'prepared/geometry.json', {'schemaVersion': 1, 'kind': 'creation-geometry', 'status': 'passed',
                           'normalization': {'matrix': matrix, 'inverse': inverse, 'scale': scale, 'center': [0, 0, 0]},
                           'sourceSha256': receipt['sourceOriginal']['sha256'],
                           'workerSha256': adapter.sha256(run / 'adapter-code/scripts/creation_geometry.py'),
                           'files': {name: {'file': name, 'sha256': adapter.sha256(run / 'prepared' / name)} for name in ('prepared.glb', 'control.glb')},
                           'checks': [{'name': 'unit contract check', 'status': 'passed'}]})
        adapter.seal_prepared(run, receipt)
        return run

    def test_copied_evidence_survives_original_removal(self):
        run = self.make_prepared()
        # Exact fixture path verified inside this test's private temporary root.
        self.assertTrue(self.runs.resolve().is_relative_to(self.root.resolve()))
        shutil.rmtree(self.runs)
        _, receipt = adapter.load_prepared(run / 'creation-prepared.json', self.root)
        self.assertEqual(receipt['assetId'], 'fixture-canary')
        second = self.root / 'lab/.local/runs/rigged'
        second.mkdir()
        copied, result = adapter.copy_prepared(run / 'creation-prepared.json', self.root, second)
        self.assertEqual(result, receipt)
        self.assertTrue((copied / 'creation-prepared.json').is_file())

    def test_prepared_source_substitution_rejected_even_resealed(self):
        run = self.make_prepared()
        manifest = run / 'creation-prepared.json'
        receipt = adapter.read_json(manifest)
        receipt['sourceOriginal'] = receipt['prepared']
        manifest.write_text(json.dumps(receipt))
        (run / 'creation-prepared.COMPLETE').write_text(adapter.sha256(manifest))
        with self.assertRaisesRegex(ValueError, 'source reference'):
            adapter.load_prepared(manifest, self.root)

    def test_prepared_output_tamper_rejected(self):
        run = self.make_prepared()
        (run / 'prepared/prepared.glb').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            adapter.load_prepared(run / 'creation-prepared.json', self.root)


if __name__ == '__main__':
    unittest.main()
