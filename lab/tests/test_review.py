"""Review server isolation and corpus provenance, without loading CUDA."""
import hashlib, importlib.util, json, struct, tempfile, threading, unittest
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('gallery_server',ROOT/'tools/serve_gallery.py');server_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(server_module)
def gltf(path):
 data=path.read_bytes();assert data[:4]==b'glTF';length,kind=struct.unpack_from('<II',data,12);assert kind==0x4E4F534A
 return json.loads(data[20:20+length])
class ReviewServerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  review=self.root/'lab/.local/review';assets=review/'assets';assets.mkdir(parents=True)
  (self.root/'gallery.html').write_text('catalog')
  (self.root/'lab/secret.txt').write_text('not public');(assets/'pose.glb').write_bytes(b'fixture')
  (review/'manifest.json').write_text(json.dumps({'schemaVersion':1,'assets':[{'label':'Cuadrúpedo'}],'files':{'known':{'file':'pose.glb','sha256':hashlib.sha256(b'fixture').hexdigest()},'escape':{'file':'../../../secret.txt','sha256':'bad'}}},ensure_ascii=False),encoding='utf-8')
  self.review=review
  self.patch=patch.object(server_module,'REVIEW',review);self.patch.start();self.addCleanup(self.patch.stop)
  class Handler(server_module.GalleryHandler):
   lab=True
   def log_message(self,*args):pass
  self.handler=Handler
  self.server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(self.root)))
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
  self.addCleanup(self.close)
 def close(self):self.server.shutdown();self.server.server_close();self.thread.join()
 def request(self,path,method='GET'):
  try:
   with urlopen(Request('http://127.0.0.1:'+str(self.server.server_port)+path,method=method)) as r:return r.status,r.read()
  except HTTPError as e:
   try:return e.code,e.read()
   finally:e.close()
 def test_inventory_utf8_and_only_registered_files(self):
  code,data=self.request('/_lab/manifest.json');self.assertEqual(code,200);manifest=json.loads(data);self.assertNotIn('files',manifest);self.assertEqual(manifest['assets'][0]['label'],'Cuadrúpedo')
  self.assertEqual(self.request('/_lab/assets/known'),(200,b'fixture'))
  for path in ['/_lab/assets/unknown','/_lab/assets/escape','/lab/secret.txt','/AGENTS.md','/creation-lab/brief.json','/lab/.local/review/manifest.json','/%2e%2e/lab/secret.txt','/.git/config']:
   with self.subTest(path=path):self.assertEqual(self.request(path)[0],404);self.assertEqual(self.request(path,'HEAD')[0],404)
 def test_changed_file_is_rejected_and_disabled_server_hides_inventory(self):
  (self.review/'assets/pose.glb').write_bytes(b'changed');self.assertEqual(self.request('/_lab/assets/known')[0],409)
  self.handler.lab=False;self.assertEqual(self.request('/_lab/manifest.json')[0],404)
  self.assertEqual(self.request('/gallery.html')[0],200)
 def test_prefix_and_symlink_cannot_bypass(self):
  self.handler.prefix='/assets/'
  self.assertEqual(self.request('/assets/gallery.html')[0],200);self.assertEqual(self.request('/gallery.html')[0],404)
  (self.root/'alias').symlink_to(self.root/'lab',target_is_directory=True)
  self.assertEqual(self.request('/assets/alias/secret.txt')[0],404)
  (self.root/'gallery').symlink_to(self.root/'lab',target_is_directory=True)
  self.assertEqual(self.request('/assets/gallery/secret.txt')[0],404)
class CorpusEvidenceTests(unittest.TestCase):
 @unittest.skipUnless((ROOT/'lab/.local/review/manifest.json').exists(),'Prepare local corpus evidence first')
 def test_original_hashes_and_generated_skeleton_inputs_and_no_clips(self):
  for asset in ['human','quadruped']:
   run=json.loads((ROOT/'lab/reports'/('rig-'+asset+'.json')).read_text());self.assertEqual(run['status'],'success')
   p=run['provenance'];self.assertEqual(hashlib.sha256((ROOT/p['sourceFile']).read_bytes()).hexdigest(),p['sourceSha256'])
   prepared=gltf(ROOT/p['prepared']['file']);control=gltf(ROOT/p['control']['file'])
   self.assertFalse(prepared.get('skins'));self.assertFalse(prepared.get('animations'));self.assertTrue(control.get('skins'));self.assertFalse(control.get('animations'))
   skeleton=next(x for x in run['artifacts'] if x['file'].endswith('model_skeleton.fbx'))
   self.assertEqual(run['skinningInput']['sha256'],skeleton['sha256']);self.assertEqual(run['skinningInput']['file'],skeleton['file'])
   candidate=next(x for x in run['artifacts'] if x['file'].endswith('model_rigged.glb'));doc=gltf(ROOT/candidate['file']);self.assertTrue(doc.get('skins'));self.assertFalse(doc.get('animations'))
  inventory=json.loads((ROOT/'lab/.local/review/manifest.json').read_text())
  self.assertEqual(len(inventory['assets']),2);self.assertEqual(len(inventory['files']),44)
  for asset in inventory['assets']:
   immutable=ROOT/'lab/.local/runs'/asset['reviewRunId']/'review-manifest.json'
   self.assertEqual(next(x for x in json.loads(immutable.read_text())['assets'] if x['id']==asset['id']),asset)
  for entry in inventory['files'].values():
   path=ROOT/'lab/.local/review/assets'/entry['file'];self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),entry['sha256']);self.assertFalse(gltf(path).get('animations'))
if __name__=='__main__':unittest.main()
