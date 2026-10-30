import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CLI=ROOT/'studio/studio.py'
class CliTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.workspace=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def invoke(self,*args):
        result=subprocess.run([sys.executable,str(CLI),'--workspace',str(self.workspace),*args],capture_output=True,text=True)
        return result, json.loads(result.stdout)
    def test_project_init_validate_and_duplicate_preservation(self):
        scene=self.workspace/'input.json'
        scene.write_text(json.dumps({'schemaVersion':1,'kind':'scene','id':'sample','title':'Sample','duration':10,'mode':'interactive','instances':[{'id':'button','asset':'button','position':[0,0,0],'rotation':[0,0,0],'scale':[1,1,1]}]}))
        result,data=self.invoke('project','init','demo','--scene',str(scene))
        self.assertEqual(result.returncode,0,result.stderr)
        project=Path(data['project'])
        original=(project/'project.json').read_bytes()
        result,data=self.invoke('validate',str(project/'project.json'))
        self.assertEqual(result.returncode,0,result.stderr); self.assertEqual(data['status'],'PASS')
        result,data=self.invoke('project','init','demo','--scene',str(scene))
        self.assertNotEqual(result.returncode,0); self.assertEqual((project/'project.json').read_bytes(),original)
    def test_invalid_manifest_is_machine_readable_failure(self):
        invalid=self.workspace/'bad.json'; invalid.write_text('{"schemaVersion":99}')
        result,data=self.invoke('validate',str(invalid))
        self.assertNotEqual(result.returncode,0); self.assertEqual(data['status'],'FAIL')
    def test_capabilities_does_not_claim_live_verification(self):
        result,data=self.invoke('capabilities')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('capabilities',data)
        self.assertTrue(data['capabilities'])

    def test_project_and_run_show_reject_internal_symlinks(self):
        outside=self.workspace/'outside'; outside.mkdir()
        (self.workspace/'projects').symlink_to(outside,target_is_directory=True)
        result,data=self.invoke('project','init','escape')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(list(outside.iterdir()),[])
        sys.path.insert(0,str(ROOT))
        from studio import core
        run=core.create_run(self.workspace,'test',{})
        (run/'events').rmdir(); (run/'events').symlink_to(outside,target_is_directory=True)
        (outside/'secret.json').write_text('{"secret":"outside"}')
        result,data=self.invoke('run','show',run.name)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('outside',json.dumps(data.get('events',[])))

if __name__=='__main__': unittest.main()
