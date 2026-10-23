"""Behavioral checks for fresh clones and independent reruns; no Blender needed."""
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import benchmark_io
import collect
import serve
import package as packaging
import zipfile


def make_run(root, run_id, complete=True, ident='A'):
    run = root/ident/run_id
    run.mkdir(parents=True)
    for name, data in {
        'asset.glb':b'glTFfixture',
        'source.blend':b'BLENDERfixture',
        'parts.json':b'{"parts":[]}',
        'build-checks.json':json.dumps({'metrics':{'triangles':1,'meshes':1,'materials':['m'],'dimensionsM':[.3,.2,.1]}}).encode(),
    }.items():
        (run/name).write_bytes(data)
    (run/'renders').mkdir()
    for view in benchmark_io.REVIEW_VIEWS:
        (run/'renders'/(view+'.png')).write_bytes(b'PNGfixture-'+view.encode())
    manifest = {'runId':run_id,'attempt':1,'technical':'PASS','status':'PASS',
                'seconds':1,'generatorSha256':'author-code',
                'artifacts':{p.relative_to(run).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in run.rglob('*') if p.is_file()}}
    (run/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    if complete:
        (run/'COMPLETE').write_text(hashlib.sha256((run/'manifest.json').read_bytes()).hexdigest(),encoding='utf-8')
    return run


def make_review(run):
    return {'id':run.parent.name,'runId':run.name,'score':87,'visual':'PASS','biological':'PASS',
            'imageEvidence':[{'view':view,'sha256':hashlib.sha256((run/'renders'/(view+'.png')).read_bytes()).hexdigest()} for view in sorted(benchmark_io.REVIEW_VIEWS)]}


class ReproductionTests(unittest.TestCase):
    def test_new_package_does_not_present_historical_scores_as_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);runs=root/'runs';entries=[]
            for ident in 'ABCDEF':
                run=make_run(runs,'20260101-new-'+ident,ident=ident)
                entries.append({'id':ident,'runId':run.name,'manifestSha256':hashlib.sha256((run/'manifest.json').read_bytes()).hexdigest(),
                                'technical':'PASS','visual':'PASS','biological':'PASS','score':87})
            source=root/'results.json';source.write_text(json.dumps({'entries':entries}),encoding='utf-8')
            before=source.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                packaging.main(['--runs',str(runs),'--results',str(source),'--output',str(root/'delivery')])
            with zipfile.ZipFile(root/'delivery/celula-animal-seis-alternativas.zip') as archive:
                note=archive.read('LEEME.txt').decode('utf-8')
                current=json.loads(archive.read('benchmark/results.json'))
                self.assertIn('D: run 20260101-new-D; técnica PASS; visual NOT_RUN',note)
                self.assertNotIn('87',note)
                self.assertIn('benchmark/history/RESULTS.md',archive.namelist())
                self.assertNotIn('benchmark/RESULTS.md',archive.namelist())
                self.assertIsNone(next(e for e in current['entries'] if e['id']=='D')['score'])
                self.assertEqual(json.loads(archive.read('benchmark/reviews.json'))['entries'],[])
            self.assertEqual(source.read_bytes(),before)

    def test_viewer_requires_run_id_and_unchanged_review_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run=make_run(root,'20260101-old');review=make_review(run)
            with patch.object(serve,'OUTPUT',root),patch.object(serve,'load_reviews',return_value={'A':review}):
                self.assertEqual(serve.discover()[0]['conditions'][0]['review']['score'],87)
                review.pop('runId')
                self.assertIsNone(serve.discover()[0]['conditions'][0]['review'])
                review['runId']=run.name
                (run/'renders/front.png').write_bytes(b'changed after review')
                self.assertIsNone(serve.discover()[0]['conditions'][0]['review'])

    def test_collect_ignores_missing_id_and_mismatched_review_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run=make_run(root/'runs','20260101-old')
            reviews=root/'reviews';reviews.mkdir()
            for scenario in ('missing-run-id','wrong-image-hash','missing-image-evidence'):
                review=make_review(run)
                if scenario=='missing-run-id':review.pop('runId')
                elif scenario=='wrong-image-hash':review['imageEvidence'][0]['sha256']='0'*64
                else:review['imageEvidence']=[]
                (reviews/'A.json').write_text(json.dumps(review),encoding='utf-8')
                report=root/scenario
                with contextlib.redirect_stdout(io.StringIO()):
                    collect.main(['--runs',str(root/'runs'),'--reviews',str(reviews),'--report-dir',str(report)])
                entry=json.loads((report/'results.json').read_text(encoding='utf-8'))['entries'][0]
                self.assertEqual(entry['visual'],'NOT_RUN')
                self.assertIsNone(entry['score'])

    def test_viewer_ignores_new_incomplete_run_and_mismatched_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_run(root, '20260101-old')
            make_run(root, '20260102-new', complete=False)
            with patch.object(serve,'OUTPUT',root), patch.object(serve,'load_reviews',return_value={'A':{'runId':'20250101-other','score':99}}):
                entry = serve.discover()[0]['conditions'][0]
            self.assertEqual(entry['runId'],'20260101-old')
            self.assertIsNone(entry['review'])

    def test_changed_completion_marker_is_not_served(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = make_run(root, '20260101-old')
            (run/'manifest.json').write_text('{}',encoding='utf-8')
            with patch.object(serve,'OUTPUT',root):
                entry = serve.discover()[0]['conditions'][0]
            self.assertIsNone(entry['urlGlb'])
            self.assertEqual(entry['technical'],'NOT_RUN')

    def test_collect_rerun_does_not_reuse_review_or_overwrite_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); runs=root/'runs'; reviews=root/'reviews'; reviews.mkdir()
            make_run(runs, '20260101-old'); make_run(runs,'20260102-new')
            (reviews/'A.json').write_text(json.dumps({'runId':'20260101-old','score':99}),encoding='utf-8')
            snapshot=hashlib.sha256((collect.BASE/'results.json').read_bytes()).hexdigest()
            args=['--runs',str(runs),'--reviews',str(reviews),'--format-report',str(root/'absent.json'),'--report-dir',str(root/'new-report')]
            with contextlib.redirect_stdout(io.StringIO()):
                collect.main(args)
            entry=json.loads((root/'new-report/results.json').read_text(encoding='utf-8'))['entries'][0]
            self.assertEqual(entry['runId'],'20260102-new')
            self.assertEqual(entry['visual'],'NOT_RUN')
            self.assertIsNone(entry['score'])
            self.assertEqual(snapshot,hashlib.sha256((collect.BASE/'results.json').read_bytes()).hexdigest())
            report_before=(root/'new-report/results.json').read_bytes()
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                collect.main(args)
            self.assertEqual(report_before,(root/'new-report/results.json').read_bytes())

    def test_artifact_escape_cannot_be_collected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); run=make_run(root/'runs','20260101-old')
            outside=root/'secret.txt';outside.write_text('private',encoding='utf-8')
            with self.assertRaises(ValueError):
                benchmark_io.contained_file(run, '../../../secret.txt')


if __name__=='__main__':unittest.main()
