import copy
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

    def test_run_and_event_directories_reject_symlink_escape(self):
        outside=self.root/'outside'; outside.mkdir()
        workspace=self.root/'workspace'; workspace.mkdir()
        (workspace/'runs').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError): core.create_run(workspace,'bad',{})
        self.assertEqual(list(outside.iterdir()),[])
        (workspace/'runs').unlink()
        run=core.create_run(workspace,'safe',{})
        (run/'events').rmdir(); (run/'events').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError): core.record_event(run,{'status':'FAIL'})
        self.assertEqual(list(outside.iterdir()),[])

    def test_scene_boundary_matches_browser_contract(self):
        scene={'schemaVersion':1,'kind':'scene','id':'x','title':'X','duration':2,'mode':'timeline','instances':[{'id':'servo','asset':'servo','position':[0,0,0],'rotation':[0,0,0],'scale':[1,1,1]}],'tracks':[]}
        scene['instances'][0]['asset']='https://outside/model.glb'
        with self.assertRaises(ValueError): core.validate_record(scene)
        scene['instances'][0]['asset']='servo'
        scene['tracks']=[{'target':'servo','channel':'angle','keyframes':[{'time':0,'value':181}]}]
        with self.assertRaises(ValueError): core.validate_record(scene)
        scene['tracks']=[{'target':'servo','channel':'pressed','keyframes':[{'time':0,'value':1}]}]
        with self.assertRaises(ValueError): core.validate_record(scene)

    def _microbit_cases(self):
        path = Path(__file__).resolve().parent / 'fixtures' / 'microbit-scene-cases.json'
        return json.loads(path.read_text(encoding='utf-8'))

    def test_microbit_scene_cases_match_typescript(self):
        cases = self._microbit_cases()
        self.assertTrue(cases['valid'] and cases['invalid'])
        for case in cases['valid']:
            with self.subTest(valid=case['name']):
                core.validate_record(copy.deepcopy(case['scene']))
        for case in cases['invalid']:
            with self.subTest(invalid=case['name']):
                with self.assertRaises(ValueError):
                    core.validate_record(copy.deepcopy(case['scene']))

    def test_microbit_grid_and_track_values_reject_bool_and_nonfinite(self):
        base = copy.deepcopy(self._microbit_cases()['valid'][0]['scene'])
        core.validate_record(copy.deepcopy(base))
        for bad in (True, False, float('nan'), float('inf'), float('-inf')):
            for label, mutate in (
                ('grid pressed', lambda s, v: s['patternBindings'][0]['pressed'][2].__setitem__(2, v)),
                ('grid released', lambda s, v: s['patternBindings'][0]['released'][0].__setitem__(0, v)),
                ('track value', lambda s, v: s['tracks'][0]['keyframes'][1].__setitem__('value', v)),
                ('track time', lambda s, v: s['tracks'][0]['keyframes'][1].__setitem__('time', v)),
            ):
                with self.subTest(bad=repr(bad), where=label):
                    scene = copy.deepcopy(base)
                    mutate(scene, bad)
                    with self.assertRaises(ValueError):
                        core.validate_record(scene)

    def test_scene_camera_rejects_bool_and_nonfinite_and_absent_means_default(self):
        base = copy.deepcopy(self._microbit_cases()['valid'][1]['scene'])
        self.assertNotIn('camera', base)
        core.validate_record(copy.deepcopy(base))
        for good in ({'elevation': 62, 'azimuth': 0}, {'elevation': 5.5, 'azimuth': -180}, {'elevation': 89, 'azimuth': 180.0}):
            with self.subTest(good=good):
                scene = copy.deepcopy(base); scene['camera'] = good
                core.validate_record(scene)
        for bad in (True, False, float('nan'), float('inf'), float('-inf')):
            for key in ('elevation', 'azimuth'):
                with self.subTest(bad=repr(bad), key=key):
                    scene = copy.deepcopy(base); scene['camera'] = {'elevation': 60, 'azimuth': 0}; scene['camera'][key] = bad
                    with self.assertRaises(ValueError):
                        core.validate_record(scene)

    def test_schema_describes_the_scene_camera(self):
        schema = json.loads((Path(__file__).resolve().parents[1] / 'contracts' / 'records.schema.json').read_text(encoding='utf-8'))
        scene = next(branch['then'] for branch in schema['allOf'] if branch.get('if', {}).get('properties', {}).get('kind', {}).get('const') == 'scene')
        camera = scene['properties']['camera']
        self.assertFalse(camera['additionalProperties'])
        self.assertEqual(set(camera['required']), {'elevation', 'azimuth'})
        self.assertEqual((camera['properties']['elevation']['minimum'], camera['properties']['elevation']['maximum']), (5, 89))
        self.assertEqual((camera['properties']['azimuth']['minimum'], camera['properties']['azimuth']['maximum']), (-180, 180))
        self.assertNotIn('camera', scene.get('required', []))

    def test_schema_lists_microbit_channels(self):
        schema = json.loads((Path(__file__).resolve().parents[1] / 'contracts' / 'records.schema.json').read_text(encoding='utf-8'))
        scene = next(branch['then'] for branch in schema['allOf'] if branch.get('if', {}).get('properties', {}).get('kind', {}).get('const') == 'scene')
        properties = scene['properties']
        channel = properties['tracks']['items']['properties']['channel']
        names = set(channel.get('enum', []))
        for name in ('pressed', 'angle', 'a', 'b', 'logo'):
            self.assertIn(name, names)
        led = {f'led.{x}.{y}' for x in range(5) for y in range(5)}
        self.assertTrue(led <= names)
        self.assertEqual(len(names), 5 + 25)
        self.assertEqual(properties['instances']['items']['properties']['behavior'], {'enum': ['microbit']})
        pattern = properties['patternBindings']['items']
        self.assertFalse(pattern['additionalProperties'])
        self.assertEqual(set(pattern['required']), {'source', 'target', 'released', 'pressed'})

    def test_brief_requires_measurable_constraints_and_rights(self):
        brief={'schemaVersion':1,'kind':'brief','id':'mechanism','goal':'Press controls a mechanism','targetRuntime':'web','coordinates':{'units':'m','up':'Y','front':'+Z'},'dimensionsMeters':[2,1,1],'budgets':{'triangles':10000,'drawCalls':100,'textureSize':2048},'references':[],'style':'original teaching model','provenance':{'author':'test','source':'original','license':'MIT'},'acceptanceGates':['technical','visual','content','provenance']}
        core.validate_record(brief)
        brief['budgets']['triangles']=0
        with self.assertRaises(ValueError): core.validate_record(brief)
        brief['budgets']['triangles']=10000; brief['dimensionsMeters'][1]=-1
        with self.assertRaises(ValueError): core.validate_record(brief)

if __name__ == '__main__': unittest.main()
