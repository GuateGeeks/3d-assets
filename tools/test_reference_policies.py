import unittest
import acquire_institutions
import promote_institutions

class RightsPolicy(unittest.TestCase):
    def test_cc0_native_downloads_are_accepted(self):
        self.assertEqual(acquire_institutions.sketchfab_license('https://creativecommons.org/publicdomain/zero/1.0/'), 'CC0 1.0')
    def test_noncommercial_sharealike_is_preserved(self):
        self.assertEqual(acquire_institutions.sketchfab_license('http://creativecommons.org/licenses/by-nc-sa/4.0/'), 'CC-BY-NC-SA 4.0')
    def test_unrelated_licenses_and_hosts_are_not_assigned_cc(self):
        for url in ['https://sketchfab.com/licenses/free-standard', 'https://creativecommons.org.evil.test/licenses/by/4.0/']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                acquire_institutions.sketchfab_license(url)
    def test_no_derivatives_requires_individual_review(self):
        with self.assertRaises(ValueError):
            acquire_institutions.sketchfab_license('https://creativecommons.org/licenses/by-nd/4.0/')

class FamilyPreservation(unittest.TestCase):
    def test_another_batch_preserves_existing_families_and_aliases(self):
        existing={'schemaVersion':1,'groups':[{'id':'panels','title':'Paneles solares','modelIds':['old-panel']}], 'aliases':[{'id':'old-alias','canonicalId':'old-panel'}]}
        incoming={'groups':[{'id':'panels','title':'panels','modelIds':['new-panel']},{'id':'new-family','title':'Nueva familia','modelIds':['other']}], 'aliases':[]}
        result=promote_institutions.merge_groups(existing,incoming)
        self.assertEqual(result['groups'][0]['modelIds'], ['old-panel','new-panel'])
        self.assertEqual(result['groups'][0]['title'], 'Paneles solares')
        self.assertEqual(result['aliases'], [{'id':'old-alias','canonicalId':'old-panel'}])
        self.assertEqual(existing['groups'][0]['modelIds'], ['old-panel'])

class NativeLines(unittest.TestCase):
    @staticmethod
    def fixture(lines=False, scale=1):
        import json, struct
        positions=struct.pack('<9f',0,0,0,scale,0,0,0,scale,0)
        binary=positions+struct.pack('<3H',0,1,2)+struct.pack('<2H',0,1)+b'\0\0'
        doc={'asset':{'version':'2.0'},'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0}],
             'buffers':[{'byteLength':len(binary)}],
             'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':36},{'buffer':0,'byteOffset':36,'byteLength':6},{'buffer':0,'byteOffset':42,'byteLength':4}],
             'accessors':[{'bufferView':0,'componentType':5126,'type':'VEC3','count':3},{'bufferView':1,'componentType':5123,'type':'SCALAR','count':3},{'bufferView':2,'componentType':5123,'type':'SCALAR','count':2}],
             'meshes':[{'primitives':[{'attributes':{'POSITION':0},'indices':1}]+([{'attributes':{'POSITION':0},'indices':2,'mode':1}] if lines else [])}]}
        text=json.dumps(doc).encode();text+=b' '*((-len(text))%4)
        body=struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(binary),0x004e4942)+binary
        return b'glTF'+struct.pack('<II',2,12+len(body))+body
    def test_triangle_fingerprint_remains_compatible(self):
        import hashlib,json
        from geometry_fingerprint import fingerprint
        result=fingerprint(self.fixture())
        self.assertEqual(result['method'],'triangle-edge-distribution-v1')
        self.assertEqual(result['sha256'],hashlib.sha256(json.dumps([[500000,500000,1000000]],separators=(',',':')).encode()).hexdigest())
    def test_native_lines_are_audited_without_changing_source(self):
        from geometry_fingerprint import fingerprint
        original=self.fixture(True);before=bytes(original)
        result=fingerprint(original)
        self.assertEqual(result['lines'],1)
        self.assertNotEqual(result['sha256'],fingerprint(self.fixture())['sha256'])
        self.assertEqual(result['sha256'],fingerprint(self.fixture(True,10))['sha256'])
        self.assertEqual(original,before)

class PolyHavenBatchSelection(unittest.TestCase):
    def test_run_local_selection_overrides_the_legacy_selection(self):
        import json, tempfile
        from pathlib import Path
        import polyhaven
        with tempfile.TemporaryDirectory() as directory:
            run=Path(directory)
            (run/'selection.json').write_text(json.dumps({'items':[{'asset':'modular_pipes'}]}))
            self.assertEqual(polyhaven.selection_for(run)['items'], [{'asset':'modular_pipes'}])
    def test_existing_runs_still_use_the_legacy_selection(self):
        import tempfile
        from pathlib import Path
        import polyhaven
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(polyhaven.selection_for(Path(directory)), polyhaven.read(polyhaven.ROOT/'enrichment/polyhaven-selection.json'))

if __name__=='__main__':unittest.main()
