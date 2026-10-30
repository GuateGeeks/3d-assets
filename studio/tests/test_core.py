import json
import struct
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from studio import core

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def test_runs_and_events_never_replace_prior_evidence(self):
        first = core.create_run(self.root, 'example', {'source': 'a'})
        original = (first / 'run.json').read_bytes()
        second = core.create_run(self.root, 'example', {'source': 'a'})
        event = core.record_event(first, {'status': 'FAIL'})
        core.record_event(first, {'status': 'PASS'})
        self.assertNotEqual(first, second)
        self.assertEqual((first / 'run.json').read_bytes(), original)
        self.assertEqual(core.read_json(event)['status'], 'FAIL')
    def test_paths_reject_cross_platform_escapes_and_links(self):
        (self.root/'safe.txt').write_text('safe')
        for bad in ('../safe.txt', '/etc/passwd', 'C:/secret', 'a\\b', '', 'a/../safe.txt'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                core.checked_path(self.root, bad)
        (self.root/'link').symlink_to(self.root/'safe.txt')
        with self.assertRaises(ValueError): core.checked_path(self.root, 'link')
        self.assertEqual(core.checked_path(self.root, 'safe.txt'), self.root/'safe.txt')
    def test_json_rejects_nonfinite_and_duplicate_keys(self):
        for raw in ('{"value":NaN}', '{"value":1,"value":2}', '[]'):
            (self.root/'bad.json').write_text(raw)
            with self.assertRaises(ValueError): core.read_json(self.root/'bad.json')
    def test_glb_validates_header_and_json_not_just_extension(self):
        path = self.root/'model.glb'
        payload = json.dumps({'asset': {'version':'2.0'}, 'scenes':[{'nodes':[]}], 'scene':0}).encode()
        payload += b' ' * (-len(payload)%4)
        path.write_bytes(struct.pack('<III',0x46546c67,2,20+len(payload))+struct.pack('<II',len(payload),0x4e4f534a)+payload)
        self.assertEqual(core.validate_glb(path)['version'], 2)
        path.write_bytes(path.read_bytes()[:-1])
        with self.assertRaises(ValueError): core.validate_glb(path)
    def test_scene_rejects_ambiguous_tracks_and_unknown_targets(self):
        scene = {'schemaVersion':1,'kind':'scene','id':'demo','title':'Demo','duration':10,'mode':'timeline','instances':[{'id':'knob','asset':'servo','position':[0,0,0],'rotation':[0,0,0],'scale':[1,1,1]}], 'tracks':[{'target':'knob','channel':'angle','keyframes':[{'time':0,'value':0},{'time':10,'value':90}]}]}
        core.validate_record(scene)
        scene['tracks'].append(scene['tracks'][0])
        with self.assertRaises(ValueError): core.validate_record(scene)
        scene['tracks'] = [{'target':'absent','channel':'angle','keyframes':[{'time':0,'value':0}]}]
        with self.assertRaises(ValueError): core.validate_record(scene)
    def test_contract_rejects_unknown_version_and_nonfinite_coordinates(self):
        with self.assertRaises(ValueError): core.validate_record({'schemaVersion':2,'kind':'asset'})
        with self.assertRaises(ValueError): core.validate_record({'schemaVersion':1,'kind':'asset','id':'a','revision':'1','artifacts':[],'coordinates':{'units':'m','up':'Y','front':'+Z'},'bounds':[float('inf'),1,1],'provenance':{}})
    def test_package_requires_reviews_and_detects_changed_inputs(self):
        (self.root/'source.txt').write_text('original')
        (self.root/'review.json').write_text(json.dumps({'status':'PASS','subjects':{'source.txt':core.sha256(self.root/'source.txt')}}))
        manifest = {'schemaVersion':1,'kind':'package','id':'demo','files':[{'path':'source.txt','sha256':core.sha256(self.root/'source.txt')}], 'reviews':{name:{'status':'PASS','path':'review.json','sha256':core.sha256(self.root/'review.json')} for name in ('technical','visual','content','provenance')}}
        output = self.root.parent / (self.root.name + '.zip')
        try:
            core.build_package(self.root,manifest,output)
            self.assertTrue(output.exists())
            (self.root/'source.txt').write_text('changed')
            with self.assertRaises(ValueError): core.build_package(self.root,manifest,self.root/'second.zip')
            manifest['reviews']['visual']['status']='NOT_RUN'
            with self.assertRaises(ValueError): core.build_package(self.root,manifest,self.root/'third.zip')
        finally: output.unlink(missing_ok=True)

if __name__ == '__main__': unittest.main()
