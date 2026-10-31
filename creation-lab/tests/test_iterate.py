"""Evidence and transition regressions, independent of Blender or a model API."""
import contextlib
import importlib.util
import io
import json
import shutil
import stat
import sys
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

    def add_run(self, stage='blockout', technical='PASS', with_images=True, extra_views=None):
        index = len(list((self.path / 'runs').iterdir())) + 1
        rid = f'{index:03d}-test'
        path = self.path / 'runs' / rid
        path.mkdir(); (path / 'renders').mkdir()
        shutil.copy2(self.path / 'brief.json', path / 'brief.json')
        if with_images:
            for view in (*flow.VIEWS, *(extra_views or ())):
                (path / 'renders' / (view + '.png')).write_bytes(b'test-fixture-' + view.encode())
        manifest = {'schemaVersion': 1, 'runId': rid, 'sequence': index, 'stage': stage,
                    'parentRunId': f'{index-1:03d}-test' if index > 1 else None,
                    'sessionSha256': flow.digest(self.path / 'session.json'),
                    'author': self.author, 'technical': technical,
                    'artifacts': {p.relative_to(path).as_posix(): flow.digest(p) for p in path.rglob('*') if p.is_file()}}
        if extra_views is not None:
            manifest['extraViews'] = list(extra_views)
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



class BenchmarkProfileTests(unittest.TestCase):
    """Explicit, isolated benchmark profile; Sol/Luna defaults stay unchanged."""
    HAIKU, SONNET, OPUS = 'claude-haiku-5-5', 'claude-sonnet-5-5', 'claude-opus-5-5'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        IterationTests.setUp(self)  # Reuse the synthetic brief fixture.
        self.profile = {'schemaVersion': 1, 'id': 'test-claude-profile',
                        'roles': {'coordinator': {'models': [self.OPUS], 'efforts': ['high']},
                                  'reviewer': {'models': [self.OPUS], 'efforts': ['medium']}},
                        'conditions': {'haiku': {'author': {'models': [self.HAIKU], 'efforts': ['medium']}},
                                       'sonnet': {'author': {'models': [self.SONNET], 'efforts': ['medium']}}}}
        flow.write(self.root / 'profile.json', self.profile)
        self.coordinator = {'actorId': 'coordinator', 'model': self.OPUS, 'reasoningEffort': 'high'}
        self.bench = flow.init_session(self.root / 'brief.json', self.root / 'bench', 'benchmark', self.coordinator,
                                       profile_path=self.root / 'profile.json', condition='haiku')
        self.bench_session = flow.read(self.bench / 'session.json')
        self.haiku = {'actorId': 'author-haiku', 'model': self.HAIKU, 'reasoningEffort': 'medium'}

    def test_profile_frozen_in_sealed_session(self):
        info = self.bench_session['benchmark']
        self.assertEqual(info['condition'], 'haiku')
        self.assertEqual(info['profileSha256'], flow.digest(self.root / 'profile.json'))
        self.assertEqual(flow.status(self.bench)['condition'], 'haiku')

    def test_condition_author_only(self):
        self.assertEqual(flow.preflight(self.bench, self.bench_session, 'blockout', self.haiku), [])
        for model in (self.SONNET, self.OPUS, flow.SOL, flow.LUNA, 'haiku'):
            with self.assertRaisesRegex(ValueError, 'Model not allowed'):
                flow.preflight(self.bench, self.bench_session, 'blockout', {**self.haiku, 'model': model})
        with self.assertRaisesRegex(ValueError, 'reasoning effort'):
            flow.preflight(self.bench, self.bench_session, 'blockout', {**self.haiku, 'reasoningEffort': 'high'})

    def test_reviewer_and_coordinator_fixed(self):
        flow.session_actor({'actorId': 'r', 'model': self.OPUS, 'reasoningEffort': 'medium'}, self.bench_session, 'reviewer')
        for model, effort in ((self.HAIKU, 'medium'), (self.OPUS, 'high'), (flow.SOL, 'medium')):
            with self.assertRaises(ValueError):
                flow.session_actor({'actorId': 'r', 'model': model, 'reasoningEffort': effort}, self.bench_session, 'reviewer')
        with self.assertRaises(ValueError):
            flow.init_session(self.root / 'brief.json', self.root / 'b2', 'benchmark',
                              {**self.coordinator, 'model': self.SONNET}, profile_path=self.root / 'profile.json', condition='haiku')

    def test_profile_requires_exact_ids_and_known_condition(self):
        for bad in ('haiku', 'opusplan', 'sonnet', ' claude-opus-5-5'):
            profile = json.loads(json.dumps(self.profile))
            profile['conditions']['haiku']['author']['models'] = [bad]
            with self.assertRaisesRegex(ValueError, 'exact model IDs'):
                flow.validate_profile(profile)
        with self.assertRaisesRegex(ValueError, 'not defined'):
            flow.init_session(self.root / 'brief.json', self.root / 'b3', 'benchmark', self.coordinator,
                              profile_path=self.root / 'profile.json', condition='opus')
        with self.assertRaisesRegex(ValueError, 'requires --profile'):
            flow.init_session(self.root / 'brief.json', self.root / 'b4', 'benchmark', self.coordinator)

    def test_default_modes_still_reject_claude_ids(self):
        with self.assertRaisesRegex(ValueError, 'Model not allowed'):
            flow.init_session(self.root / 'brief.json', self.root / 'b5', 'sol', self.coordinator)
        with self.assertRaisesRegex(ValueError, 'apply only to benchmark'):
            flow.init_session(self.root / 'brief.json', self.root / 'b6', 'mixed', self.author,
                              profile_path=self.root / 'profile.json', condition='haiku')
        with self.assertRaisesRegex(ValueError, 'Model not allowed'):
            flow.preflight(self.path, self.session, 'blockout', self.haiku)
        with self.assertRaises(SystemExit):
            flow.main(['init', '--brief', str(self.root / 'brief.json'), '--output', str(self.root / 'b7'),
                       '--mode', 'sol', '--actor-id', 'x', '--model', self.OPUS])
        self.assertFalse((self.root / 'b7').exists())

    def test_tampered_profile_breaks_session_seal(self):
        session = flow.read(self.bench / 'session.json')
        session['benchmark']['profile']['conditions']['haiku']['author']['models'] = [self.OPUS]
        (self.bench / 'session.json').write_text(json.dumps(session))
        with self.assertRaisesRegex(ValueError, 'seal'):
            flow.status(self.bench)

    def test_reviewer_template_and_blind_review_flow(self):
        # Reuse the synthetic run/review helpers against the benchmark session.
        self.path, self.session, self.author = self.bench, self.bench_session, self.haiku
        rid, _ = IterationTests.add_run(self)
        value = flow.review_template(self.bench, rid)
        self.assertEqual(value['reviewer'], {'actorId': '', 'model': self.OPUS, 'reasoningEffort': 'medium'})
        review = IterationTests.review(self, rid)
        flow.save_review(self.bench, review)
        self.assertEqual(flow.status(self.bench)['status'], 'READY_FOR_DETAIL')


class ClaudeModeTests(unittest.TestCase):
    """Non-benchmark `claude` mode: exact Claude IDs; Sol/Luna defaults unchanged."""
    HAIKU, SONNET, OPUS = 'claude-haiku-5-5', 'claude-sonnet-5-5', 'claude-opus-5-5'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        IterationTests.setUp(self)  # Reuse the synthetic brief fixture.

    def who(self, model, effort='medium'):
        return {'actorId': 'ctx-' + model, 'model': model, 'reasoningEffort': effort}

    def test_claude_mode_role_models(self):
        for model in (self.SONNET, self.OPUS):
            flow.actor(self.who(model), 'claude', 'coordinator')
        with self.assertRaisesRegex(ValueError, 'Model not allowed'):
            flow.actor(self.who(self.HAIKU), 'claude', 'coordinator')
        for model in (self.HAIKU, self.SONNET, self.OPUS):
            flow.actor(self.who(model), 'claude', 'author')
        for model in (self.OPUS, self.SONNET):
            flow.actor(self.who(model), 'claude', 'reviewer')
        with self.assertRaisesRegex(ValueError, 'Model not allowed'):
            flow.actor(self.who(self.HAIKU), 'claude', 'reviewer')
        with self.assertRaisesRegex(ValueError, 'reasoning effort'):
            flow.actor(self.who(self.SONNET, 'turbo'), 'claude', 'author')

    def test_claude_ids_rejected_in_sol_luna_modes(self):
        for mode in ('mixed', 'sol', 'luna'):
            for role in ('coordinator', 'author', 'reviewer'):
                with self.assertRaisesRegex(ValueError, 'Model not allowed'):
                    flow.actor(self.who(self.SONNET), mode, role)

    def test_sol_luna_ids_rejected_in_claude_mode(self):
        for model in (flow.SOL, flow.LUNA):
            for role in ('coordinator', 'author', 'reviewer'):
                with self.assertRaisesRegex(ValueError, 'Model not allowed'):
                    flow.actor(self.who(model), 'claude', role)

    def test_aliases_rejected_in_claude_mode(self):
        for alias in ('sonnet', 'opus', 'haiku', ' claude-sonnet-5-5'):
            for role in ('coordinator', 'author', 'reviewer'):
                with self.assertRaisesRegex(ValueError, 'Model not allowed'):
                    flow.actor(self.who(alias), 'claude', role)

    def test_init_session_claude_mode(self):
        coordinator = self.who(self.SONNET)
        path = flow.init_session(self.root / 'brief.json', self.root / 'claude', 'claude', coordinator)
        session = flow.read(path / 'session.json')
        self.assertEqual(session['mode'], 'claude')
        self.assertNotIn('benchmark', session)
        flow.session_actor(self.who(self.HAIKU), session, 'author')
        with self.assertRaisesRegex(ValueError, 'Model not allowed'):
            flow.session_actor(self.who(flow.LUNA), session, 'author')
        self.assertEqual(flow.status(path)['mode'], 'claude')
        with self.assertRaisesRegex(ValueError, 'apply only to benchmark'):
            flow.init_session(self.root / 'brief.json', self.root / 'c2', 'claude', coordinator,
                              profile_path=self.root / 'profile.json', condition='x')
        with self.assertRaisesRegex(ValueError, 'Model not allowed'):
            flow.init_session(self.root / 'brief.json', self.root / 'c3', 'claude', self.who(self.HAIKU))

    def test_claude_review_template_defaults_to_opus(self):
        path = flow.init_session(self.root / 'brief.json', self.root / 'claude2', 'claude', self.who(self.SONNET))
        self.path, self.session, self.author = path, flow.read(path / 'session.json'), self.who(self.HAIKU)
        rid, _ = IterationTests.add_run(self)
        value = flow.review_template(path, rid)
        self.assertEqual(value['reviewer']['model'], self.OPUS)
        self.assertEqual(value['reviewer']['reasoningEffort'], 'medium')
        flow.save_review(path, IterationTests.review(self, rid))

    def test_cli_accepts_claude_mode(self):
        quiet = io.StringIO()
        with contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
            flow.main(['init', '--brief', str(self.root / 'brief.json'), '--output', str(self.root / 'c4'),
                       '--mode', 'claude', '--actor-id', 'x', '--model', self.OPUS])
            self.assertEqual(flow.read(self.root / 'c4' / 'session.json')['mode'], 'claude')
            with self.assertRaises(SystemExit):
                flow.main(['init', '--brief', str(self.root / 'brief.json'), '--output', str(self.root / 'c5'),
                           '--mode', 'claude', '--actor-id', 'x', '--model', flow.SOL])
        self.assertFalse((self.root / 'c5').exists())


# Stand-in for Blender: records each launch and writes the files the real worker
# would, including one image per default view and per extra view named in request.json.
FAKE_BLENDER = """#!{python}
import json, sys
from pathlib import Path
args = sys.argv[sys.argv.index('--') + 1:]
step, run = args[0], Path(args[1])
with (Path(__file__).parent / 'launches.log').open('a') as log:
    log.write(step + '\\n')
if step == 'build':
    (run / 'asset.glb').write_bytes(b'glb')
elif step == 'reopen':
    (run / 'renders').mkdir()
    extra = json.loads((run / 'request.json').read_text()).get('extraViews', [])
    for view in ['front', 'side', 'back', 'three-quarter', 'wireframe'] + extra:
        (run / 'renders' / (view + '.png')).write_bytes(b'fake-' + view.encode())
else:
    (run / 'renders').mkdir(exist_ok=True)
    (run / 'renders' / 'reimport-three-quarter.png').write_bytes(b'fake-reimport')
(run / (step + '-result.json')).write_text(json.dumps({{'status': 'PASS'}}))
"""


class ExtraViewTests(unittest.TestCase):
    """Optional per-run extra views; without the option nothing changes."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        IterationTests.setUp(self)
        self.blender = self.root / 'fake-blender'
        self.blender.write_text(FAKE_BLENDER.format(python=sys.executable))
        self.blender.chmod(self.blender.stat().st_mode | stat.S_IXUSR)
        self.generator = self.root / 'generator.py'
        self.generator.write_text('import bpy\n\ndef build():\n    return {}\n')

    def command(self, *extra):
        return ['run', '--session', str(self.path), '--generator', str(self.generator), '--stage', 'blockout',
                '--blender', str(self.blender), '--actor-id', 'author-1', '--model', flow.SOL, *extra]

    def execute(self, *extra):
        result = flow.run_generator(flow.parser().parse_args(self.command(*extra)))
        return Path(result['run']), flow.read(Path(result['run']) / 'manifest.json')

    def launches(self):
        log = self.root / 'launches.log'
        return log.read_text().split() if log.exists() else []

    def test_catalogue_and_parsing(self):
        self.assertEqual(flow.EXTRA_VIEWS, ('underside', 'top-down'))
        self.assertIsNone(flow.parser().parse_args(self.command()).extra_views)
        args = flow.parser().parse_args(self.command('--extra-view', 'top-down', '--extra-view', 'underside'))
        self.assertEqual(args.extra_views, ['top-down', 'underside'])

    def test_unknown_and_duplicate_rejected_before_any_launch(self):
        for extra in (['--extra-view', 'sideways'], ['--extra-view', 'underside', '--extra-view', 'underside'],
                      ['--extra-view', 'front'], ['--extra-view', 'underside', '--extra-view', 'x']):
            with contextlib.redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit):
                flow.main(self.command(*extra))
            self.assertIn('extra view', err.getvalue())
            self.assertEqual(self.launches(), [])
            self.assertEqual(list((self.path / 'runs').iterdir()), [])
            self.assertFalse((self.path / '.writer.lock').exists())

    def test_run_without_option_is_unchanged(self):
        run, manifest = self.execute()
        self.assertNotIn('extraViews', manifest)
        self.assertNotIn('extraViews', flow.read(run / 'request.json'))
        self.assertEqual(sorted(p.name for p in (run / 'renders').iterdir()),
                         sorted(v + '.png' for v in flow.VIEWS))
        self.assertEqual(self.launches(), ['build', 'reopen', 'reimport'])
        flow.load_run(self.path, manifest['runId'])
        self.assertEqual(list(flow.review_template(self.path, manifest['runId'])['images']), list(flow.VIEWS))

    def test_extra_views_recorded_and_hashed(self):
        run, manifest = self.execute('--extra-view', 'underside', '--extra-view', 'top-down')
        self.assertEqual(manifest['extraViews'], ['underside', 'top-down'])
        self.assertEqual(flow.read(run / 'request.json')['extraViews'], ['underside', 'top-down'])
        for view in ('underside', 'top-down'):
            self.assertEqual(manifest['artifacts']['renders/' + view + '.png'], flow.digest(run / 'renders' / (view + '.png')))
        flow.load_run(self.path, manifest['runId'])
        images = flow.review_template(self.path, manifest['runId'])['images']
        self.assertEqual(list(images), [*flow.VIEWS, 'underside', 'top-down'])
        self.assertTrue(all(images.values()))

    def test_manifest_with_invalid_extra_views_is_refused(self):
        for bad in (['sideways'], ['underside', 'underside'], 'underside', [3]):
            rid, run = self.add_run(extra_views=['underside'])
            manifest = flow.read(run / 'manifest.json')
            manifest['extraViews'] = bad
            (run / 'manifest.json').unlink(); (run / 'COMPLETE').unlink()
            flow.write(run / 'manifest.json', manifest)
            (run / 'COMPLETE').write_text(flow.digest(run / 'manifest.json'))
            with self.assertRaisesRegex(ValueError, 'extra view'):
                flow.load_run(self.path, rid)
            shutil.rmtree(run)

    def add_run(self, **kwargs):
        return IterationTests.add_run(self, **kwargs)

    def review(self, rid, passed=True):
        return IterationTests.review(self, rid, passed)

    def test_review_template_and_validation_use_the_runs_own_views(self):
        rid, _ = self.add_run(extra_views=['underside'])
        review = self.review(rid)
        self.assertEqual(list(review['images']), [*flow.VIEWS, 'underside'])
        review['parts'][0]['views'] = ['underside']
        flow.save_review(self.path, review)
        self.assertEqual(flow.status(self.path)['status'], 'READY_FOR_DETAIL')

    def test_extra_view_not_in_run_is_rejected(self):
        rid, _ = self.add_run()
        review = self.review(rid)
        review['parts'][0]['views'] = ['underside']
        with self.assertRaisesRegex(ValueError, 'Evidence views'):
            flow.save_review(self.path, review)
        review = self.review(rid)
        review['images']['underside'] = flow.digest(self.path / 'brief.json')
        with self.assertRaisesRegex(ValueError, 'six actual'):
            flow.save_review(self.path, review)
        review = self.review(rid, False)
        review['defects'][0]['view'] = 'top-down'
        with self.assertRaisesRegex(ValueError, 'Each defect'):
            flow.save_review(self.path, review)

    def test_run_with_extras_requires_their_hashes_and_ignores_other_extras(self):
        rid, _ = self.add_run(extra_views=['underside'])
        review = self.review(rid)
        review['images'].pop('underside')
        with self.assertRaisesRegex(ValueError, 'six actual'):
            flow.save_review(self.path, review)
        review = self.review(rid)
        review['parts'][0]['views'] = ['top-down']
        with self.assertRaisesRegex(ValueError, 'Evidence views'):
            flow.save_review(self.path, review)
        review = self.review(rid, False)
        review['defects'][0]['view'] = 'underside'
        flow.save_review(self.path, review)

    def test_extra_views_do_not_relax_hidden_part_gate(self):
        rid, _ = self.add_run(extra_views=['underside', 'top-down'])
        for visibility in ('hidden', 'unclear'):
            review = self.review(rid)
            review['parts'][0].update(visibility=visibility, views=['underside', 'top-down'])
            with self.assertRaisesRegex(ValueError, 'Hidden/unclear'):
                flow.save_review(self.path, review)
        # The honest outcome is still available: BLOCKED with actionable defects.
        review['visual']['status'] = review['content']['status'] = 'BLOCKED'
        review['defects'] = [{'view': 'underside', 'detail': 'Still unclear', 'requestedChange': 'Show it'}]
        flow.save_review(self.path, review)
        self.assertEqual(flow.status(self.path)['content'], 'BLOCKED')


if __name__ == '__main__':
    unittest.main()
