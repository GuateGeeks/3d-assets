import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from studio import core, studio
from studio.adapters import local

ROOT=Path(__file__).resolve().parents[2]

def linked_scene():
    scene=core.read_json(ROOT/'studio/examples/interactive.scene.json')
    scene['bindings']=[{'source':'Button','sourceChannel':'pressed','target':'Servo','targetChannel':'angle','released':0,'pressed':90}]
    return scene

class FinalFixTests(unittest.TestCase):
    def test_archive_rejects_mutation_after_validation_and_removes_partial_output(self):
        for changed in ('source.txt','review.json'):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as d:
                root=Path(d); (root/'source.txt').write_text('original')
                subjects={'source.txt':core.sha256(root/'source.txt')}
                core.write_json(root/'review.json',{'status':'PASS','subjects':subjects})
                manifest={'schemaVersion':1,'kind':'package','id':'test','files':[{'path':'source.txt','sha256':subjects['source.txt']}],
                          'reviews':{gate:{'status':'PASS','path':'review.json','sha256':core.sha256(root/'review.json')} for gate in core.GATES}}
                output=root/'result.zip'; original=core.zipfile.ZipFile.writestr
                def mutate(archive,name,*args,**kwargs):
                    result=original(archive,name,*args,**kwargs)
                    if name=='package.json': (root/changed).write_text('changed after validation')
                    return result
                with patch.object(core.zipfile.ZipFile,'writestr',mutate), self.assertRaisesRegex(ValueError,'hash mismatch'):
                    core.build_package(root,manifest,output)
                self.assertFalse(output.exists())
                output.write_bytes(b'prior delivery')
                with self.assertRaises(ValueError): core.build_package(root,manifest,output)
                self.assertEqual(output.read_bytes(),b'prior delivery')

    def test_review_decision_uses_the_same_receipt_bytes_as_its_digest(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'source.txt').write_text('original')
            subjects={'source.txt':core.sha256(root/'source.txt')}
            bad={'status':'FAIL','subjects':subjects};good={'status':'PASS','subjects':subjects}
            receipt=root/'review.json';core.write_json(receipt,bad)
            manifest={'schemaVersion':1,'kind':'package','id':'test','files':[{'path':p,'sha256':h} for p,h in subjects.items()],
                      'reviews':{gate:{'status':'PASS','path':'review.json','sha256':core.sha256(receipt)} for gate in core.GATES}}
            digest,read=core.sha256,core.read_json
            def change_after_hash(path):
                value=digest(path)
                if path==receipt:core.write_json(receipt,good)
                return value
            def restore_after_read(path):
                value=read(path)
                if path==receipt:core.write_json(receipt,bad)
                return value
            with patch.object(core,'sha256',change_after_hash),patch.object(core,'read_json',restore_after_read):
                with self.assertRaises(ValueError):core.build_package(root,manifest,root/'result.zip')

    def test_bindings_reject_unsafe_or_ambiguous_graphs(self):
        core.validate_record(linked_scene())
        for change in (lambda b:b.update(target='missing'),lambda b:b.update(source='Servo'),lambda b:b.update(sourceChannel='angle'),
                       lambda b:b.update(targetChannel='pressed'),lambda b:b.update(pressed=181),lambda b:b.update(released=True),lambda b:b.update(code='eval()')):
            scene=linked_scene(); change(scene['bindings'][0])
            with self.subTest(binding=scene['bindings']),self.assertRaises(ValueError):core.validate_record(scene)
        scene=linked_scene();scene['bindings']*=2
        with self.assertRaises(ValueError):core.validate_record(scene)
        for bindings in ({},None,'unsafe'):
            scene=linked_scene();scene['bindings']=bindings
            with self.assertRaises(ValueError):core.validate_record(scene)

    def test_cli_timeout_is_json_failure_after_engine_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            workspace=Path(d); run=core.create_run(workspace,'test',{})
            def timed_out(args):local.execute([sys.executable,'-c','import time; time.sleep(60)'],run,timeout=1)
            parsed=type('Args',(),{'config':None,'workspace':workspace,'handler':staticmethod(timed_out)})()
            output=io.StringIO()
            with patch.object(studio,'parser') as parser,contextlib.redirect_stdout(output):
                parser.return_value.parse_args.return_value=parsed
                code=studio.main([])
            self.assertEqual(code,1);result=json.loads(output.getvalue());self.assertEqual(result['status'],'FAIL')
            self.assertEqual(result['run'],str(run));self.assertEqual(result['log'],'process.log')
            events=list((run/'events').glob('*.json'));self.assertTrue(events)
            self.assertEqual(core.read_json(events[-1])['status'],'FAIL')

    def test_cleanup_confirms_sigterm_resistant_detached_children_immediately(self):
        for remote in (False,True):
            with self.subTest(remote=remote),tempfile.TemporaryDirectory() as d:
                root=core.create_run(Path(d),'test',{})
                child="import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"
                code="import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c',"+repr(child)+"],start_new_session=True); print(p.pid,flush=True); time.sleep(60)"
                if remote:
                    result=subprocess.run([sys.executable,str(ROOT/'studio/adapters/remote_runner.py'),'--timeout','1','--',sys.executable,'-c',code],capture_output=True,text=True,timeout=10)
                    self.assertEqual(result.returncode,124,result.stderr);pid=int(result.stdout.strip())
                else:
                    with self.assertRaises(subprocess.TimeoutExpired):local.execute([sys.executable,'-c',code],root,timeout=1)
                    pid=int((root/'process.log').read_text().strip())
                stat=Path('/proc')/str(pid)/'stat'
                try:state=stat.read_text().rsplit(')',1)[1].split()[0]
                except FileNotFoundError:state='gone'
                self.assertIn(state,('gone','Z'))

class CleanupPolicyTests(unittest.TestCase):
    def test_cleanup_deadline_reports_live_identities_and_does_not_wait_on_reused_pids(self):
        from studio.adapters import remote_runner
        with patch.object(remote_runner,'identity',return_value=('old','R')):
            with self.assertRaisesRegex(RuntimeError,'Cleanup failed'):
                remote_runner.wait_owned({123:'old'},timeout=0)
        with patch.object(remote_runner,'identity',return_value=('new','R')):
            remote_runner.wait_owned({123:'old'},timeout=0)

    def test_cli_preflight_subprocess_failure_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as d:
            parsed=type('Args',(),{'config':None,'workspace':Path(d),'handler':staticmethod(lambda args: (_ for _ in ()).throw(subprocess.CalledProcessError(7,['probe'])))})()
            output=io.StringIO()
            with patch.object(studio,'parser') as parser,contextlib.redirect_stdout(output):
                parser.return_value.parse_args.return_value=parsed
                result=studio.main([])
            self.assertEqual(result,1);self.assertEqual(json.loads(output.getvalue())['status'],'FAIL')

class BindingSchemaTests(unittest.TestCase):
    def test_binding_structural_schema_matches_python_contract(self):
        try: from jsonschema import Draft202012Validator
        except ImportError: self.skipTest('jsonschema is an optional schema verification dependency')
        validator=Draft202012Validator(core.read_json(ROOT/'studio/contracts/records.schema.json'))
        validator.validate(linked_scene())
        for update in ({'sourceChannel':'angle'},{'targetChannel':'pressed'},{'released':True},{'pressed':181},{'code':'eval()'}):
            scene=linked_scene();scene['bindings'][0].update(update)
            self.assertTrue(list(validator.iter_errors(scene)))
            with self.assertRaises(ValueError):core.validate_record(scene)
        for bindings in ({},None,'unsafe'):
            scene=linked_scene();scene['bindings']=bindings
            self.assertTrue(list(validator.iter_errors(scene)))
            with self.assertRaises(ValueError):core.validate_record(scene)
