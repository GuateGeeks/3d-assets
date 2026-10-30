import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from studio import core, preview

class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.dist=self.root/'dist'; self.dist.mkdir(); (self.dist/'index.html').write_text('<title>Lab</title>')
        self.project=self.root/'project'; self.project.mkdir()
        scene={'schemaVersion':1,'kind':'scene','id':'sample','title':'Sample','duration':10,'mode':'interactive','instances':[{'id':'button','asset':'button','position':[0,0,0],'rotation':[0,0,0],'scale':[1,1,1]}]}
        core.write_json(self.project/'scene.json',scene)
        core.write_json(self.project/'project.json',{'schemaVersion':1,'kind':'project','id':'test','title':'Test','scene':'scene.json','files':[{'path':'scene.json','sha256':core.sha256(self.project/'scene.json')}], 'provenance':{'author':'test','license':'CC0-1.0','source':'original'}})
        (self.project/'credentials.txt').write_text('must not be served')
        self.server=preview.make_server(self.dist,self.project,0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.tmp.cleanup()
    def test_serves_only_allowlisted_project_files(self):
        with urlopen(self.url+'/') as response: self.assertIn(b'Lab',response.read())
        with urlopen(self.url+'/project/scene.json') as response: self.assertEqual(json.load(response)['id'],'sample')
        for path in ('/project/credentials.txt','/project/project.json','/../credentials.txt','/%2e%2e/credentials.txt','/project/'):
            with self.subTest(path=path),self.assertRaises(HTTPError) as raised: urlopen(self.url+path)
            self.assertEqual(raised.exception.code,404); raised.exception.close()
    def test_rebinding_and_post_start_changes_are_rejected(self):
        with self.assertRaises(HTTPError) as raised: urlopen(Request(self.url+'/',headers={'Host':'attacker.example'}))
        self.assertEqual(raised.exception.code,403); raised.exception.close()
        (self.project/'scene.json').write_text('{}')
        with self.assertRaises(HTTPError) as raised: urlopen(self.url+'/project/scene.json')
        self.assertEqual(raised.exception.code,409); raised.exception.close()
    def test_static_symlinks_are_rejected(self):
        (self.dist/'secret.js').symlink_to(self.project/'credentials.txt')
        with self.assertRaises(ValueError): preview.make_server(self.dist,None,0)

if __name__=='__main__': unittest.main()
