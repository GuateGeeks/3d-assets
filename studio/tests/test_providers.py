import hashlib
import importlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    from studio.adapters import providers as p
except ImportError:
    p = None

class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(p, 'provider adapter must implement the job lifecycle')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def prepare(self, **kw):
        return p.prepare(self.root, kw.pop('provider', 'meshy'), kw.pop('operation', 'text-to-3d'), kw.pop('body', {'prompt':'original robot', 'ai_model':'meshy-t2', 'model_type':'smart-topology', 'target_polycount':4000, 'target_formats':['glb']}), **kw)

    def auth(self, job):
        return {'fingerprint':job['fingerprint'], 'provider':'meshy', 'transport':'native-mcp', 'operation':'text-to-3d', 'expectedCredits':5, 'ceilingCredits':5, 'unit':'meshy credits', 'approvedBy':'user', 'approvalReference':'explicit canary approval'}

    def intent(self, job):
        return p.submission_intent(self.root, job['id'], self.auth(job), budget=5)

    def receipt(self, job, status='PENDING', task='task-1', **extra):
        return p.ingest_receipt(self.root, job['id'], {'structuredContent': {'task_id':task, 'status':status, 'task_type':'text-to-3d', 'progress':100 if status=='SUCCEEDED' else 0, 'outcome':status, 'model_urls':{'glb':'https://cdn.example/model.glb?token=private'}, 'thumbnail_url':'https://cdn.example/thumb.png', 'consumed_credits':5, **extra}})

    def test_zero_budget_prepares_but_cannot_issue_submission_intent(self):
        job=self.prepare()
        self.assertEqual(job['state'], 'prepared')
        self.assertEqual(job['request']['tool'], 'mcp__meshy__meshy_text_to_3d')
        with self.assertRaises(ValueError): p.submission_intent(self.root,job['id'], self.auth(job))
        with self.assertRaises(ValueError): self.receipt(job)
        self.assertEqual(self.intent(job)['state'],'submission-intent')
        with self.assertRaises(ValueError): self.intent(job)

    def test_authorization_is_bound_to_exact_request_and_unit(self):
        job=self.prepare()
        for key,value in [('fingerprint','other'),('transport','magnific-mcp'),('unit','USD'),('operation','rig'),('ceilingCredits',4)]:
            a=self.auth(job);a[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): p.submission_intent(self.root,job['id'],a,budget=5)

    def test_fingerprint_persists_and_duplicate_request_cannot_be_prepared(self):
        job=self.prepare()
        importlib.reload(p)
        self.assertEqual(p.get_job(self.root,job['id'])['fingerprint'],job['fingerprint'])
        with self.assertRaisesRegex(ValueError,'duplicate'): self.prepare()
        changed=self.prepare(body={'prompt':'different robot','ai_model':'meshy-t2','model_type':'smart-topology'})
        self.assertNotEqual(changed['fingerprint'],job['fingerprint'])

    def test_transport_and_mesh_constraints_do_not_silently_switch(self):
        invalid=[{'transport':'magnific-mcp'}, {'body':{'prompt':'x','ai_model':'meshy-t2','model_type':'smart-topology','topology':'quad'}}, {'body':{'prompt':'x','ai_model':'meshy-t2','model_type':'smart-topology','target_polycount':16000}}, {'body':{'prompt':'x','api_key':'secret'}}, {'provider':'tripo','operation':'animate','body':{}}, {'provider':'tripo','body':{'prompt':'x','provider':'meshy'}}, {'provider':'tripo','body':{'prompt':'x','faceLimit':2000001}}, {'body':{'prompt':'x','model_type':'lowpoly'}}]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):self.prepare(**kwargs)
        tripo=self.prepare(provider='tripo',body={'prompt':'separate gear','provider':'tripo','modelVersion':'v3.1-20260211','generateParts':True,'texture':False,'faceLimit':500})
        self.assertEqual(tripo['request']['tool'],'mcp__magnific__models3d_text_generate')
        self.assertFalse(tripo['request']['arguments']['texture'])

    def test_rig_and_animation_require_explicit_compatible_body_and_parent(self):
        with self.assertRaises(ValueError): self.prepare(operation='rig',body={'input_task_id':'model'})
        with self.assertRaises(ValueError): self.prepare(operation='animate',body={'rig_task_id':'unknown','action_id':1},context={'bodyType':'humanoid'})
        rig=self.prepare(operation='rig',body={'input_task_id':'model'},context={'bodyType':'humanoid','textured':True,'faceCount':4000})
        self.assertEqual(rig['request']['tool'],'mcp__meshy__meshy_rig')
        tripo=self.prepare(provider='tripo',operation='rig',body={'creationIdentifier':'animal','rigType':'quadruped','outFormat':'glb'},context={'bodyType':'quadruped'})
        self.assertEqual(tripo['request']['arguments']['provider'],'tripo')

    def test_unknown_submission_requires_explicit_reconciliation_without_resubmit(self):
        job=self.prepare();self.intent(job)
        unknown=p.mark_unknown(self.root,job['id'],'network timeout')
        self.assertEqual(unknown['state'],'reconciliation-required')
        with self.assertRaises(ValueError): self.intent(job)
        with self.assertRaises(ValueError):p.reconcile(self.root,job['id'],{'decision':'not-found'})
        reconciled=p.reconcile(self.root,job['id'],{'decision':'bind','task_id':'task-1','evidence':'list_tasks matched prompt and creation time'})
        self.assertEqual(reconciled['task_id'],'task-1')
        self.assertEqual(p.resume(self.root,job['id'])['arguments']['task_id'],'task-1')

    def test_task_binding_terminal_and_out_of_order_receipts_preserve_state(self):
        job=self.prepare();self.intent(job);self.receipt(job)
        with self.assertRaises(ValueError):self.receipt(job,task='task-other')
        self.receipt(job,'IN_PROGRESS',sequence=3)
        stale=self.receipt(job,'PENDING',sequence=2)
        self.assertEqual(stale['state'],'running')
        self.receipt(job,'SUCCEEDED',sequence=4)
        self.assertEqual(self.receipt(job,'FAILED',sequence=5)['state'],'succeeded')
        self.assertEqual(self.receipt(job,'PENDING',sequence=1)['state'],'succeeded')
        self.assertEqual(p.get_job(self.root,job['id'])['actual_cost'],{'amount':5,'unit':'meshy credits'})

    def test_timeout_is_poll_guidance_not_remote_failure_and_polling_is_bounded(self):
        job=self.prepare();self.intent(job);self.receipt(job,'IN_PROGRESS',outcome='TIMEOUT')
        for attempt in (0,1,6,50):
            advice=p.resume(self.root,job['id'],attempt=attempt)
            self.assertEqual(advice['arguments']['wait'],False)
            self.assertLessEqual(advice['delaySeconds'],60)
        self.assertFalse(p.resume(self.root,job['id'],attempt=50)['mayPoll'])
        self.assertEqual(p.get_job(self.root,job['id'])['state'],'running')

    def test_magnific_complete_creation_fixture_is_normalized(self):
        job=self.prepare(provider='tripo',body={'prompt':'original robot','modelVersion':'v3.1-20260211','texture':False})
        a={'fingerprint':job['fingerprint'],'provider':'tripo','transport':'magnific-mcp','operation':'text-to-3d','expectedCredits':10,'ceilingCredits':10,'unit':'magnific credits','approvedBy':'user','approvalReference':'canary'}
        p.submission_intent(self.root,job['id'],a,budget=10)
        p.ingest_receipt(self.root,job['id'],{'structuredContent':{'creation':{'identifier':'creation-1','status':'IN_PROGRESS','credits':10,'creditsNote':'provider reported','designerUrl':'https://example/designer','expectTime':30,'tool':'models3d_text_generate','webUrl':'https://example/web'},'instruction':'Use creations_get for status'}})
        result=p.ingest_receipt(self.root,job['id'],{'structuredContent':{'identifier':'creation-1','status':'COMPLETED','url':'https://cdn.example/model.glb','previewUrl':'https://cdn.example/p.png','thumbnailUrl':'https://cdn.example/t.png','otherFormats':{},'credits':10,'expectTime':0}})
        self.assertEqual(result['state'],'succeeded')
        self.assertEqual(p.resume(self.root,job['id'])['arguments'],{'creationIdentifier':'creation-1'})

    def test_hash_bound_output_intake_rejects_mismatch_and_preserves_original(self):
        job=self.prepare();self.intent(job);self.receipt(job,'SUCCEEDED')
        source=self.root/'download.glb'
        chunk=json.dumps({'asset':{'version':'2.0'}}).encode();chunk+=b' '*((-len(chunk))%4)
        source.write_bytes(struct.pack('<4sII',b'glTF',2,20+len(chunk))+struct.pack('<I4s',len(chunk),b'JSON')+chunk)
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):p.intake_output(self.root,job['id'],'download.glb','0'*64)
        result=p.intake_output(self.root,job['id'],'download.glb',digest)
        self.assertEqual(result['outputs'][0]['sha256'],digest)
        self.assertEqual(source.read_bytes(),(self.root/result['outputs'][0]['path']).read_bytes())
        with self.assertRaises(ValueError):p.intake_output(self.root,job['id'],'download.glb',digest)
        with self.assertRaises(ValueError):p.intake_output(self.root,job['id'],'../escape.glb',digest)

    def test_receipt_redaction_retains_provenance_without_secrets(self):
        job=self.prepare();self.intent(job);self.receipt(job,headers={'Authorization':'Bearer private'},api_key='private')
        texts=''.join(f.read_text() for f in (self.root/'provider-jobs'/job['id']).glob('*.json'))
        self.assertNotIn('private',texts)
        self.assertIn('task-1',texts)
        self.assertNotIn('token=',texts)

    def test_input_hash_changes_request_and_unsafe_paths_are_rejected(self):
        (self.root/'image.png').write_bytes(b'one')
        first=self.prepare(inputs=['image.png'])
        (self.root/'image.png').write_bytes(b'two')
        second=self.prepare(inputs=['image.png'])
        self.assertNotEqual(first['fingerprint'],second['fingerprint'])
        with self.assertRaises(ValueError):self.prepare(inputs=['../secret'])
        with self.assertRaises(ValueError):p.get_job(self.root,'../escape')




class ProviderBoundaryTests(unittest.TestCase):
    setUp=ProviderTests.setUp
    prepare=ProviderTests.prepare
    auth=ProviderTests.auth
    intent=ProviderTests.intent
    receipt=ProviderTests.receipt
    def test_wrong_argument_types_fail_before_any_job_is_created(self):
        invalid=[{'prompt':'robot','ai_model':'meshy-7.1','should_remesh':'false'}, {'prompt':'robot','ai_model':'meshy-7.1','should_remesh':True,'target_polycount':100.5}, {'prompt':'robot','ai_model':'meshy-7.1','decimation_mode':9}, {'prompt':'robot','ai_model':'meshy-7.1','pose_mode':'lying'}, {'prompt':'robot','ai_model':'meshy-7.1','target_formats':['glb','glb']}]
        for body in invalid:
            with self.subTest(body=body),self.assertRaises(ValueError):self.prepare(body=body)
        self.assertFalse((self.root/'provider-jobs').exists())

    def test_invalid_tripo_multiview_and_default_forced_texture_are_rejected(self):
        for body in [{'model':'tripo-v31','views':{'front':'a'}}, {'model':'tripo-v31','views':{'top':'a','bottom':'b'}}, {'model':'tripo-v31','views':{'front':'a','back':'b'},'rig':True}, {'model':'tripo-p1','creationIdentifier':'img','textureQuality':'detailed'}]:
            with self.subTest(body=body),self.assertRaises(ValueError):self.prepare(provider='tripo',operation='image-to-3d',body=body)

    def test_local_image_envelope_uses_absolute_tool_path_and_tracks_original_hash(self):
        (self.root/'design.png').write_bytes(b'image fixture')
        job=self.prepare(operation='image-to-3d',body={'ai_model':'meshy-7.1','file_path':'design.png','should_texture':False})
        self.assertEqual(job['request']['arguments']['file_path'],str(self.root/'design.png'))
        self.assertEqual(job['inputs'][0]['path'],'design.png')
        (self.root/'design.png').write_bytes(b'changed')
        a=self.auth(job);a['operation']='image-to-3d'
        with self.assertRaises(ValueError):p.submission_intent(self.root,job['id'],a,budget=5)

    def test_receipt_ignores_late_failure_but_accepts_same_terminal_cost_detail(self):
        job=self.prepare();self.intent(job)
        p.ingest_receipt(self.root,job['id'],{'task_id':'task-1','status':'SUCCEEDED','progress':100})
        updated=self.receipt(job,'SUCCEEDED',consumed_credits=7)
        self.assertEqual(updated['actual_cost']['amount'],7)
        self.assertTrue(updated['costCeilingExceeded'])
        self.assertEqual(self.receipt(job,'FAILED')['state'],'succeeded')

    def test_animation_accepts_only_bound_rig_and_catalog_evidence(self):
        rig=self.prepare(operation='rig',body={'input_task_id':'model'},context={'bodyType':'humanoid','textured':True,'faceCount':4000})
        a=self.auth(rig);a['operation']='rig'
        p.submission_intent(self.root,rig['id'],a,budget=5)
        p.ingest_receipt(self.root,rig['id'],{'task_id':'rig-1','task_type':'rigging','status':'SUCCEEDED'})
        with self.assertRaises(ValueError):self.prepare(operation='animate',body={'rig_task_id':'rig-1','action_id':1},context={'parentJob':rig['id']})
        job=self.prepare(operation='animate',body={'rig_task_id':'rig-1','action_ids':[1,2]},context={'parentJob':rig['id'],'animationCatalogReceipt':'catalog-query-20261030'})
        self.assertEqual(job['request']['tool'],'mcp__meshy__meshy_animate')

    def test_symlink_job_store_and_local_output_are_rejected(self):
        outside=self.root/'other';outside.mkdir()
        link=self.root/'provider-jobs';link.symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):self.prepare()
        self.assertEqual(list(outside.iterdir()),[])

class ProviderFinalBoundaryTests(unittest.TestCase):
    setUp=ProviderTests.setUp
    prepare=ProviderTests.prepare
    auth=ProviderTests.auth
    intent=ProviderTests.intent
    receipt=ProviderTests.receipt
    def test_task_id_cannot_be_claimed_by_two_different_jobs(self):
        first=self.prepare();self.intent(first);self.receipt(first)
        second=self.prepare(body={'prompt':'other','ai_model':'meshy-7.1'})
        self.intent(second)
        with self.assertRaises(ValueError):self.receipt(second)

    def test_terminal_cost_enrichment_preserves_outputs_and_provides_download_envelope(self):
        job=self.prepare();self.intent(job);self.receipt(job,'SUCCEEDED')
        updated=p.ingest_receipt(self.root,job['id'],{'task_id':'task-1','status':'SUCCEEDED','consumed_credits':5})
        self.assertEqual(updated['remote_outputs']['glb'],'https://cdn.example/model.glb')
        download=p.resume(self.root,job['id'])['download']
        self.assertEqual(download['tool'],'mcp__meshy__meshy_download_model')
        self.assertEqual(download['arguments']['task_id'],'task-1')
        self.assertEqual(download['arguments']['format'],'glb')
        self.assertTrue(download['arguments']['save_to'].startswith(str(self.root)))

    def test_malformed_json_or_error_receipt_does_not_bind_job(self):
        job=self.prepare();self.intent(job)
        with self.assertRaises(ValueError):p.ingest_receipt(self.root,job['id'],{'isError':True,'structuredContent':{'task_id':'task-1','status':'PENDING'}})
        self.assertIsNone(p.get_job(self.root,job['id'])['task_id'])
        bad=self.root/'bad.json';bad.write_text('{"status":"PENDING","status":"SUCCEEDED"}')
        with self.assertRaises(ValueError):p._read(bad)
        for value in ('.','a/./b','C:secret','a\\b'):
            with self.subTest(path=value),self.assertRaises(ValueError):p._path(self.root,value,False)

    def test_unserializable_receipt_cannot_leave_partial_event(self):
        job=self.prepare();self.intent(job)
        with self.assertRaises(ValueError):self.receipt(job,opaque_metadata=float('nan'))
        self.assertIsNone(p.get_job(self.root,job['id'])['task_id'])
        self.assertEqual(len(list((self.root/'provider-jobs'/job['id']).glob('event-*.json'))),1)

    def test_create_receipt_without_task_type_resumes_with_native_rigging_type(self):
        rig=self.prepare(operation='rig',body={'input_task_id':'model'},context={'bodyType':'humanoid','textured':True,'faceCount':4000})
        a=self.auth(rig);a['operation']='rig'
        p.submission_intent(self.root,rig['id'],a,budget=5)
        p.ingest_receipt(self.root,rig['id'],{'task_id':'rig-1','status':'PENDING','estimated_time':'2 minutes','message':'queued'})
        self.assertEqual(p.resume(self.root,rig['id'])['arguments']['task_type'],'rigging')

    def test_malformed_source_ids_and_format_lists_fail_as_validation_errors(self):
        for operation,body in [('rig',{'input_task_id':42}),('image-to-3d',{'ai_model':'meshy-7.1','input_task_id':42}),('text-to-3d',{'prompt':'robot','ai_model':'meshy-7.1','target_formats':[{}]})]:
            with self.subTest(body=body),self.assertRaises(ValueError):self.prepare(operation=operation,body=body,context={'bodyType':'humanoid','textured':True,'faceCount':4000})

    def test_tripo_texture_quality_is_validated_per_operation(self):
        with self.assertRaises(ValueError):
            self.prepare(provider='tripo',body={'prompt':'robot','modelVersion':'v3.1-20260211','textureQuality':'none'})
        self.assertFalse((self.root/'provider-jobs').exists())
        for quality in ('standard','detailed'):
            text=self.prepare(provider='tripo',body={'prompt':'robot','modelVersion':'v3.1-20260211','textureQuality':quality})
            self.assertEqual(text['request']['arguments']['textureQuality'],quality)
        bare=self.prepare(provider='tripo',body={'prompt':'robot','modelVersion':'v3.1-20260211','texture':False})
        self.assertFalse(bare['request']['arguments']['texture'])
        image=self.prepare(provider='tripo',operation='image-to-3d',body={'creationIdentifier':'image-1','model':'tripo-v31','textureQuality':'none','generateParts':True})
        self.assertEqual(image['request']['arguments']['textureQuality'],'none')
        for quality in ('standard','detailed'):
            image=self.prepare(provider='tripo',operation='image-to-3d',body={'creationIdentifier':'image-1','model':'tripo-v31','textureQuality':quality})
            self.assertEqual(image['request']['arguments']['textureQuality'],quality)
        with self.assertRaises(ValueError):
            self.prepare(provider='tripo',operation='image-to-3d',body={'creationIdentifier':'image-1','model':'tripo-p1','textureQuality':'detailed'})

    def test_capability_exposure_is_separate_from_implementation(self):
        descriptors=p.describe({})
        text=next(d for d in descriptors if d['provider']=='meshy' and d['operation']=='text-to-3d')
        self.assertTrue(text['implemented']);self.assertFalse(text['configured']);self.assertFalse(text['session-exposed'])
        self.assertIn('meshy-t2',text['models'])
        self.assertEqual(text['last-verified-receipt'],None)

if __name__=='__main__':unittest.main()
