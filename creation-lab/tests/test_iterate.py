"""Evidence and transition regressions, independent of Blender or a model API."""
import importlib.util
import json
import shutil
from pathlib import Path
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('iterate', BASE / 'iterate.py')
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)


class IterationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.brief = {'schemaVersion': 1, 'id': 'test-asset', 'purpose': 'Test spatial relationships',
                      'parts': [{'id': 'shell', 'label': 'Envoltura'}], 'seed': 1,
                      'displayScale': {'units': 'm', 'longestDimension': .3, 'tolerance': .02},
                      'budgets': {'triangles': 100, 'materials': 2, 'meshObjects': 3, 'glbBytes': 1000},
                      'provenance': {'author': 'test', 'origin': 'test fixture', 'license': 'CC0-1.0'},
                      'blockoutChecks': ['The opening exposes the interior.'],
                      'contentChecks': ['The final rim is continuous.']}
        flow.write(self.root / 'brief.json', self.brief)
        self.author = {'actorId': 'author-1', 'model': flow.SOL, 'reasoningEffort': 'medium'}
        self.path = flow.init_session(self.root / 'brief.json', self.root / 'session', 'mixed', self.author)
        self.session = flow.read(self.path / 'session.json')

    def add_run(self, stage='blockout', technical='PASS', with_images=True):
        index = len(list((self.path / 'runs').iterdir())) + 1
        rid = f'{index:03d}-test'
        path = self.path / 'runs' / rid
        path.mkdir(); (path / 'renders').mkdir()
        shutil.copy2(self.path / 'brief.json', path / 'brief.json')
        if with_images:
            for view in flow.VIEWS:
                (path / 'renders' / (view + '.png')).write_bytes(b'test-fixture-' + view.encode())
        manifest = {'schemaVersion': 1, 'runId': rid, 'sequence': index, 'stage': stage,
                    'parentRunId': f'{index-1:03d}-test' if index > 1 else None,
                    'sessionSha256': flow.digest(self.path / 'session.json'),
                    'author': self.author, 'technical': technical,
                    'artifacts': {p.relative_to(path).as_posix(): flow.digest(p) for p in path.rglob('*') if p.is_file()}}
        flow.write(path / 'manifest.json', manifest)
        (path / 'COMPLETE').write_text(flow.digest(path / 'manifest.json'))
        return rid, path

    def review(self, rid, passed=True):
        value = flow.review_template(self.path, rid)
        value['reviewer']['actorId'] = 'independent-reviewer'
        value['openedImages'] = True
        for gate in ('visual', 'content'):
            value[gate] = {'status': 'PASS' if passed else 'FAIL', 'reason': 'Synthetic test observation'}
        for part in value['parts']:
            part.update(visibility='visible', views=['three-quarter'], reason='Synthetic test observation')
        for check in value['checks']:
            check.update(status='PASS' if passed else 'FAIL', reason='Synthetic test observation')
        if not passed:
            value['defects'] = [{'view': 'front', 'detail': 'Occluded', 'requestedChange': 'Open the shell'}]
        return value

    def test_detail_requires_latest_approved_blockout(self):
        with self.assertRaisesRegex(ValueError, 'Start with blockout'):
            flow.preflight(self.path, self.session, 'detail', self.author)
        rid, _ = self.add_run()
        with self.assertRaisesRegex(ValueError, 'approved latest blockout'):
            flow.preflight(self.path, self.session, 'detail', self.author)
        flow.save_review(self.path, self.review(rid))
        self.assertEqual(flow.status(self.path)['status'], 'READY_FOR_DETAIL')
        self.assertEqual(len(flow.preflight(self.path, self.session, 'detail', self.author)), 1)
        rid2, _ = self.add_run()
        with self.assertRaisesRegex(ValueError, 'approved latest blockout'):
            flow.preflight(self.path, self.session, 'detail', self.author)

    def test_blockout_checks_do_not_claim_final_detail(self):
        rid, _ = self.add_run()
        self.assertEqual(flow.review_template(self.path, rid)['checks'][0]['check'], self.brief['blockoutChecks'][0])
        flow.save_review(self.path, self.review(rid))
        rid2, _ = self.add_run('detail')
        self.assertEqual(flow.review_template(self.path, rid2)['checks'][0]['check'], self.brief['contentChecks'][0])

    def test_reviewer_independence_and_modes(self):
        rid, _ = self.add_run()
        review = self.review(rid); review['reviewer']['actorId'] = self.author['actorId']
        with self.assertRaisesRegex(ValueError, 'independent'):
            flow.save_review(self.path, review)
        review['reviewer']['actorId'] = 'independent-reviewer'; review['reviewer']['model'] = flow.LUNA
        with self.assertRaisesRegex(ValueError, 'Model not allowed'):
            flow.save_review(self.path, review)
        for mode, model in [('sol', flow.LUNA), ('luna', flow.SOL)]:
            with self.assertRaises(ValueError):
                flow.actor({**self.author, 'model': model}, mode, 'author')
        with self.assertRaises(ValueError):
            flow.actor({**self.author, 'model': 'gpt-6-astra'}, 'mixed', 'author')

    def test_six_actual_hashes_and_opened_images_required(self):
        rid, _ = self.add_run()
        review = self.review(rid); review['openedImages'] = False
        with self.assertRaisesRegex(ValueError, 'Open the actual'):
            flow.save_review(self.path, review)
        review['openedImages'] = True; review['images'].pop('back')
        with self.assertRaisesRegex(ValueError, 'six actual'):
            flow.save_review(self.path, review)

    def test_hidden_parts_and_failed_content_cannot_pass(self):
        rid, _ = self.add_run(); review = self.review(rid)
        review['parts'][0]['visibility'] = 'hidden'
        with self.assertRaisesRegex(ValueError, 'Hidden/unclear'):
            flow.save_review(self.path, review)
        review['parts'][0]['visibility'] = 'visible'; review['checks'][0]['status'] = 'BLOCKED'
        with self.assertRaisesRegex(ValueError, 'Failed/unobserved'):
            flow.save_review(self.path, review)

    def test_tampered_artifact_or_manifest_invalidates_review(self):
        rid, run = self.add_run(); review = self.review(rid)
        flow.save_review(self.path, review)
        (run / 'renders/front.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Changed artifact'):
            flow.status(self.path)

    def test_correction_budget_shared_across_stages(self):
        rid, _ = self.add_run(); flow.save_review(self.path, self.review(rid, False))
        self.assertEqual(len(flow.preflight(self.path, self.session, 'blockout', self.author)), 1)

    def test_recovery_can_retry_without_overwriting_earlier_evidence(self):
        rid, run = self.add_run()
        flow.write(run / 'request.json', flow.read(run / 'manifest.json'))
        (run / 'COMPLETE').unlink()
        (self.path / '.writer.lock').write_text('writer one')
        flow.recover(self.path, rid, 'Synthetic interruption one', True)
        first = flow.digest(run / 'unsealed-manifest.json')
        (run / 'COMPLETE').unlink()
        (self.path / '.writer.lock').write_text('writer two')
        flow.recover(self.path, rid, 'Synthetic interruption two', True)
        self.assertEqual(flow.digest(run / 'unsealed-manifest.json'), first)
        self.assertEqual(len(list(run.glob('unsealed-manifest*.json'))), 2)
        self.assertEqual(flow.status(self.path)['technical'], 'FAIL')
        rid, _ = self.add_run(); flow.save_review(self.path, self.review(rid))
        flow.preflight(self.path, self.session, 'detail', self.author)
        rid, _ = self.add_run('detail'); flow.save_review(self.path, self.review(rid, False))
        flow.preflight(self.path, self.session, 'detail', self.author)
        rid, _ = self.add_run('detail'); flow.save_review(self.path, self.review(rid, False))
        self.assertEqual(flow.status(self.path)['next'], 'stop-budget-exhausted')
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            flow.preflight(self.path, self.session, 'detail', self.author)

    def test_technical_failure_never_overridden_by_visual_pass(self):
        rid, _ = self.add_run(technical='FAIL'); flow.save_review(self.path, self.review(rid))
        self.assertEqual(flow.status(self.path)['status'], 'FAIL')
        with self.assertRaisesRegex(ValueError, 'approved latest blockout'):
            flow.preflight(self.path, self.session, 'detail', self.author)

    def test_failed_build_can_be_repaired_without_missing_images(self):
        rid, _ = self.add_run(technical='FAIL', with_images=False)
        self.assertEqual(len(flow.preflight(self.path, self.session, 'blockout', self.author)), 1)
        with self.assertRaisesRegex(ValueError, 'six actual'):
            flow.save_review(self.path, self.review(rid))

    def test_review_and_brief_are_not_overwritten(self):
        rid, _ = self.add_run(); review = self.review(rid)
        flow.save_review(self.path, review)
        with self.assertRaises(FileExistsError):
            flow.save_review(self.path, review)
        (self.path / 'brief.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Brief changed'):
            flow.status(self.path)

    def test_previous_reviewer_cannot_author(self):
        rid, _ = self.add_run(); review = self.review(rid); flow.save_review(self.path, review)
        with self.assertRaisesRegex(ValueError, 'reviewer context'):
            flow.preflight(self.path, self.session, 'detail', review['reviewer'])

    def test_only_one_session_writer(self):
        with flow.session_lock(self.path):
            with self.assertRaisesRegex(ValueError, 'already has a writer'):
                with flow.session_lock(self.path):
                    pass
        self.assertFalse((self.path / '.writer.lock').exists())

    def test_foreign_session_run_is_rejected(self):
        rid, run = self.add_run()
        other = flow.init_session(self.root / 'brief.json', self.root / 'other', 'mixed', self.author)
        shutil.copytree(run, other / 'runs' / rid)
        with self.assertRaisesRegex(ValueError, 'another session'):
            flow.status(other)

    def test_interrupted_run_can_be_preserved_as_failure(self):
        rid, run = self.add_run()
        manifest = flow.read(run / 'manifest.json')
        flow.write(run / 'request.json', manifest)
        (run / 'COMPLETE').unlink()
        (self.path / '.writer.lock').write_text('interrupted writer')
        self.assertEqual(flow.status(self.path)['next'], 'inspect-pending-run')
        with self.assertRaisesRegex(ValueError, 'Pending run'):
            flow.preflight(self.path, self.session, 'detail', self.author)
        with self.assertRaisesRegex(ValueError, 'stop the old process'):
            flow.recover(self.path, rid, 'Process ended in this synthetic fixture', False)
        flow.recover(self.path, rid, 'Process ended in this synthetic fixture', True)
        self.assertTrue((run / 'unsealed-manifest.json').exists())
        self.assertTrue((run / 'interrupted-writer.lock').exists())
        self.assertEqual(flow.status(self.path)['technical'], 'FAIL')
        self.assertEqual(len(flow.preflight(self.path, self.session, 'blockout', self.author)), 1)


if __name__ == '__main__':
    unittest.main()
