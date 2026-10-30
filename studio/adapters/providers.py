"""Offline MCP job preparation and immutable receipt intake. Never invokes providers."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
from urllib.parse import urlsplit, urlunsplit
import uuid

TRANSPORTS = {'meshy': 'native-mcp', 'tripo': 'magnific-mcp'}
UNITS = {'meshy': 'meshy credits', 'tripo': 'magnific credits'}
TOOLS = {'meshy': {'text-to-3d': 'meshy_text_to_3d', 'image-to-3d': 'meshy_image_to_3d', 'remesh': 'meshy_remesh', 'rig': 'meshy_rig', 'animate': 'meshy_animate'}, 'tripo': {'text-to-3d': 'models3d_text_generate', 'image-to-3d': 'models3d_generate', 'remesh': 'models3d_remesh', 'rig': 'models3d_rig'}}
TERMINAL = {'succeeded', 'failed', 'canceled'}
STATUS = {'PENDING':'pending', 'QUEUED':'pending', 'IN_PROGRESS':'running', 'PROCESSING':'running', 'RUNNING':'running', 'SUCCEEDED':'succeeded', 'COMPLETED':'succeeded', 'SUCCESS':'succeeded', 'FAILED':'failed', 'ERROR':'failed', 'CANCELED':'canceled', 'CANCELLED':'canceled'}
MESH_COMMON = 'ai_model alpha_thumbnail auto_size geometry_resolution model_type origin_at pose_mode response_format should_remesh target_formats target_polycount topology decimation_mode'
FIELDS = {
    ('meshy','text-to-3d'): MESH_COMMON+' prompt',
    ('meshy','image-to-3d'): MESH_COMMON+' file_path image_url input_task_id enable_pbr image_enhancement multi_view_thumbnails remove_lighting save_pre_remeshed_model should_texture texture_image_url texture_prompt texture_resolution',
    ('meshy','remesh'): 'input_task_id model_url alpha_thumbnail response_format decimation_mode target_formats target_polycount topology',
    ('meshy','rig'): 'height_meters input_task_id model_url texture_image_url response_format',
    ('meshy','animate'): 'rig_task_id action_id action_ids motion_task_id post_process response_format',
    ('tripo','text-to-3d'): 'prompt provider modelVersion faceLimit topology texture generateParts negativePrompt geometryQuality textureQuality enablePbr folderReference',
    ('tripo','image-to-3d'): 'creationIdentifier views model faceLimit rig textureQuality generateParts folderReference',
    ('tripo','remesh'): 'creationIdentifier provider remeshMode faceLimit topology folderReference',
    ('tripo','rig'): 'creationIdentifier provider outFormat rigType folderReference',
}

def _canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()

def _path(root, relative, exists=True):
    root = Path(root).absolute()
    rel = str(relative)
    if not rel or Path(rel).is_absolute() or PureWindowsPath(rel).is_absolute() or '\\' in rel or ':' in rel or '\x00' in rel or any(x in ('.','..','') for x in rel.split('/')):
        raise ValueError('unsafe relative path')
    # Reject symlinks in every component, including the configured root.
    for candidate in [root, *root.parents]:
        if candidate.is_symlink(): raise ValueError('symlink root')
    current = root
    for part in Path(rel).parts:
        current = current / part
        if current.is_symlink(): raise ValueError('symlink artifact')
    if exists and not current.exists(): raise ValueError('missing artifact: '+rel)
    return current

def _read(path):
    from studio.core import read_json
    return read_json(Path(path))

def _write_new(path,data):
    # Serialize before touching the store; publish atomically without replacement.
    encoded=json.dumps(data,sort_keys=True,indent=2,allow_nan=False)+'\n'
    path=Path(path)
    temporary=path.with_name('.pending-'+uuid.uuid4().hex)
    try:
        with temporary.open('x',encoding='utf-8') as handle:
            handle.write(encoded);handle.flush();os.fsync(handle.fileno())
        os.link(temporary,path)
    finally:temporary.unlink(missing_ok=True)

def _hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

@contextmanager
def _lock(workspace):
    workspace=Path(workspace)
    _path(workspace,'provider-jobs',False).mkdir(parents=True,exist_ok=True)
    lock=_path(workspace,'provider-jobs/.lock',False)
    try: handle=lock.open('x')
    except FileExistsError: raise ValueError('provider job store is busy; never remove a live lock') from None
    try:
        handle.write(str(datetime.now(timezone.utc)));handle.close();yield
    finally: lock.unlink()

def _folder(workspace,job_id):
    if not re.fullmatch(r'[a-f0-9]{32}',str(job_id)):raise ValueError('invalid job ID')
    return _path(workspace,'provider-jobs/'+job_id)

def get_job(workspace,job_id):
    folder=_folder(workspace,job_id)
    state=_read(_path(folder,'request.json'))
    for f in sorted(folder.glob('event-*.json')):
        state=_read(_path(folder,f.name))['snapshot']
    return state

def _event(workspace,job,event,receipt=None):
    folder=_folder(workspace,job['id'])
    index=len(list(folder.glob('event-*.json')))+1
    record={'schemaVersion':1,'event':event,'recordedAt':datetime.now(timezone.utc).isoformat(),'snapshot':job}
    if receipt is not None:record['receipt']=redact(receipt)
    _write_new(folder/f'event-{index:06d}.json',record)
    return deepcopy(job)

def redact(value):
    """Sanitize receipts before persistence; retain URL identity, remove credentials."""
    if isinstance(value,dict):
        return {k:('[REDACTED]' if re.search(r'authorization|cookie|password|secret|token|api.?key|credential',k,re.I) else redact(v)) for k,v in value.items()}
    if isinstance(value,list):return [redact(x) for x in value]
    if isinstance(value,str):
        def clean(match):
            u=urlsplit(match.group(0)); host=u.hostname or ''
            if u.port:host+=':'+str(u.port)
            return urlunsplit((u.scheme,host,u.path,'',''))
        value=re.sub(r'https?://[^\s\"<>]+',clean,value)
        value=re.sub(r'(?i)Bearer\s+[^\s,;]+','Bearer [REDACTED]',value)
        value=re.sub(r'(?i)((?:api[_-]?key|token|password|secret)\s*[:=]\s*)[^\s,;]+',r'\1[REDACTED]',value)
        return value
    return value

def _number(value,name,minimum=0,maximum=float('inf')):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not minimum<=value<=maximum:raise ValueError('invalid '+name)

def _one(body,keys):
    if sum(bool(body.get(k)) for k in keys)!=1:raise ValueError('exactly one of '+', '.join(keys)+' is required')

def _validate(workspace,provider,operation,body,context):
    if provider not in TOOLS or operation not in TOOLS[provider]:raise ValueError('operation unavailable through this provider transport')
    if not isinstance(body,dict) or set(body)-set(FIELDS[(provider,operation)].split()):raise ValueError('unsupported tool argument')
    body=deepcopy(body)
    booleans=set('alpha_thumbnail auto_size should_remesh enable_pbr image_enhancement multi_view_thumbnails remove_lighting save_pre_remeshed_model should_texture texture generateParts enablePbr rig'.split())
    integers=set('target_polycount decimation_mode faceLimit action_id'.split())
    structured={'views','post_process','target_formats','action_ids'}
    for key,value in body.items():
        if key not in booleans|integers|structured|{'height_meters'} and (not isinstance(value,str) or not value.strip()):raise ValueError('nonempty string required: '+key)
        if key in ('target_formats','action_ids') and not isinstance(value,list):raise ValueError('list required: '+key)
        if key=='target_formats' and any(not isinstance(x,str) for x in value):raise ValueError('format names must be strings')
        if key in booleans and not isinstance(value,bool):raise ValueError('boolean required: '+key)
        if key in integers and (not isinstance(value,int) or isinstance(value,bool)):raise ValueError('integer required: '+key)
    for key,choices in {'pose_mode':('a-pose','t-pose'),'origin_at':('bottom','center'),'geometryQuality':('standard','detailed')}.items():
        if key in body and body[key] not in choices:raise ValueError('invalid '+key)
    if 'decimation_mode' in body:_number(body['decimation_mode'],'decimation_mode',1,4)
    if 'height_meters' in body:_number(body['height_meters'],'height_meters',0.001,1000)
    if 'target_formats' in body and isinstance(body['target_formats'],list) and len(set(body['target_formats']))!=len(body['target_formats']):raise ValueError('duplicate target format')
    for key in ('image_url','model_url','texture_image_url'):
        if key in body:
            u=urlsplit(str(body[key]))
            if u.scheme!='https' or not u.netloc or u.username or u.password:raise ValueError('public HTTPS source required')
    if redact(body)!=body:raise ValueError('credentials or signed URLs are not accepted in prepared arguments')
    if operation=='text-to-3d':
        if not isinstance(body.get('prompt'),str) or not body['prompt'].strip() or len(body['prompt'])>800:raise ValueError('prompt must contain 1..800 characters')
    if provider=='meshy':
        if 'response_format' in body and body['response_format']!='json':raise ValueError('JSON receipts required')
        body['response_format']='json'
        if operation in ('text-to-3d','image-to-3d'):
            if body.get('ai_model') not in ('meshy-7.1','meshy-6','meshy-6-lite','meshy-t2','meshy-t2.5'):raise ValueError('explicit supported ai_model required; aliases/deprecated models unavailable')
            model=body.get('model_type','standard')
            if model not in ('standard','smart-topology'):raise ValueError('unsupported model_type')
            smart=model=='smart-topology'
            if smart != (body['ai_model'] in ('meshy-t2','meshy-t2.5')):raise ValueError('model and topology engine incompatible')
            if smart and (body.get('topology','triangle')!='triangle' or body.get('should_remesh') or 'decimation_mode' in body):raise ValueError('smart topology is triangle-only and cannot remesh/decimate')
            if 'target_polycount' in body:
                _number(body['target_polycount'],'target_polycount',100, (30000 if body['ai_model']=='meshy-t2.5' else 15000) if smart else 300000)
                if not smart and not body.get('should_remesh'):raise ValueError('standard polycount requires should_remesh')
            if body.get('geometry_resolution','standard') not in ('standard','2k','4k'):raise ValueError('invalid geometry resolution')
            if body.get('geometry_resolution','standard')!='standard' and (smart or body['ai_model']!='meshy-7.1'):raise ValueError('ultra geometry unsupported on this engine')
            if body.get('texture_resolution','2k') not in ('2k','4k','8k') or (body['ai_model']=='meshy-6-lite' and body.get('texture_resolution','2k')!='2k'):raise ValueError('unsupported texture resolution')
        if operation=='image-to-3d':
            _one(body,['file_path','image_url','input_task_id'])
            if 'file_path' in body: _path(workspace,body['file_path'])
        if operation in ('remesh','rig'):_one(body,['input_task_id','model_url'])
        if operation=='remesh' and 'target_polycount' in body:_number(body['target_polycount'],'target_polycount',100,300000)
        if operation=='rig':
            if context.get('bodyType')!='humanoid' or context.get('textured') is not True:raise ValueError('Meshy rig requires explicit textured humanoid context')
            _number(context.get('faceCount'),'faceCount',1,300000)
        if operation=='animate':
            _one(body,['action_id','action_ids','motion_task_id'])
            parent=get_job(workspace,context.get('parentJob',''))
            if parent['provider']!='meshy' or parent['operation']!='rig' or parent['state']!='succeeded' or parent.get('task_id')!=body.get('rig_task_id'):raise ValueError('animation requires a succeeded native Meshy rig parent')
            if ('action_id' in body or 'action_ids' in body) and not context.get('animationCatalogReceipt'):raise ValueError('catalog discovery receipt reference required; never guess action IDs')
            actions=body.get('action_ids',[body['action_id']] if 'action_id' in body else [])
            if not isinstance(actions,list) or any(not isinstance(x,int) or isinstance(x,bool) or x<0 for x in actions):raise ValueError('invalid action IDs')
            if 'post_process' in body:
                post=body['post_process']
                if not isinstance(post,dict) or set(post)-{'operation_type','fps'} or post.get('operation_type') not in ('change_fps','fbx2usdz','extract_armature') or (post['operation_type']=='change_fps' and post.get('fps') not in (24,25,30,60)):raise ValueError('invalid animation post processing')
            if 'action_ids' in body and (not isinstance(body['action_ids'],list) or not 1<=len(body['action_ids'])<=10 or len(set(body['action_ids']))!=len(body['action_ids'])):raise ValueError('1..10 unique actions required')
        if 'target_formats' in body and (not isinstance(body['target_formats'],list) or not body['target_formats'] or set(body['target_formats'])-set(('glb','obj','fbx','stl','usdz','3mf','blend') if operation=='remesh' else ('glb','obj','fbx','stl','usdz','3mf'))):raise ValueError('unsupported formats')
        if body.get('topology','triangle') not in ('triangle','quad'):raise ValueError('invalid topology')
        if body.get('topology')=='quad' and not set(body.get('target_formats',[])) & {'fbx','obj','blend'}:raise ValueError('quads require a quad-capable output')
    else:
        if operation!='image-to-3d':
            if body.get('provider','tripo')!='tripo':raise ValueError('no implicit provider/transport switch')
            body['provider']='tripo'
        if operation=='text-to-3d':
            if 'textureQuality' in body and body['textureQuality'] not in ('standard','detailed'):raise ValueError('Tripo text textureQuality must be standard or detailed; use texture false for bare geometry')
            if body.get('modelVersion') not in ('v3.1-20260211','v3.0-20250812','v2.5-20250123'):raise ValueError('explicit Tripo version required')
            if body.get('generateParts') and (body['modelVersion']=='v2.5-20250123' or body.get('texture') is not False):raise ValueError('parts require v3 and explicitly disabled textures')
        if operation=='image-to-3d':
            if 'textureQuality' in body and body['textureQuality'] not in ('none','standard','detailed'):raise ValueError('invalid Tripo image textureQuality')
            if body.get('model') not in ('tripo-v31','tripo-p1','tripo-p2'):raise ValueError('explicit Tripo model required')
            _one(body,['creationIdentifier','views'])
            if 'views' in body:
                views=body['views']
                if not isinstance(views,dict) or not 2<=len(views)<=4 or set(views)-{'front','left','back','right'} or any(not isinstance(x,str) or not x for x in views.values()) or body.get('rig'):raise ValueError('multiview needs 2..4 named views and cannot rig')
            if body.get('textureQuality')=='detailed' and body['model'] not in ('tripo-v31','tripo-p2'):raise ValueError('detailed texture unsupported on this model')
            if body.get('generateParts') and (body['model']!='tripo-v31' or body.get('textureQuality')!='none'):raise ValueError('parts require v31 and textureQuality none')
        if operation in ('rig','remesh') and not body.get('creationIdentifier'):raise ValueError('creationIdentifier required')
        if 'topology' in body and body['topology'] not in ('triangle','quad'):raise ValueError('invalid topology')
        quad=body.get('topology')=='quad'
        if 'faceLimit' in body:
            low,high=500,150000 if quad else 2000000
            if operation=='image-to-3d':
                low=100;high={'tripo-p1':20000,'tripo-p2':50000,'tripo-v31':2000000}[body['model']]
            if operation=='remesh':
                low=1
                if body.get('remeshMode','retopology')=='retopology':high=10000 if quad else 20000
            _number(body['faceLimit'],'faceLimit',low,high)
        if operation=='remesh' and body.get('remeshMode','retopology') not in ('retopology','simplify'):raise ValueError('invalid remeshMode')
        if operation=='rig':
            rig=body.get('rigType','biped')
            if rig not in ('biped','quadruped','hexapod','octopod','avian','serpentine','aquatic'):raise ValueError('unsupported rig type')
            if context.get('bodyType')!=rig:raise ValueError('explicit matching bodyType required')
            if body.get('outFormat','glb') not in ('glb','fbx'):raise ValueError('unsupported rig format')
    _canonical(body)
    return body

def prepare(workspace,provider,operation,body,transport=None,inputs=None,context=None):
    context=context or {}; inputs=inputs or []
    if provider not in TRANSPORTS or (transport is not None and transport!=TRANSPORTS[provider]):raise ValueError('unsupported provider/transport pair')
    if redact(context)!=context:raise ValueError('secret context prohibited')
    body=_validate(workspace,provider,operation,body,context)
    hashes=[{'path':str(x),'sha256':_hash(_path(workspace,x))} for x in sorted(set(inputs))]
    if 'file_path' in body and body['file_path'] not in [x['path'] for x in hashes]:hashes.append({'path':body['file_path'],'sha256':_hash(_path(workspace,body['file_path']))})
    tool=('mcp__meshy__' if provider=='meshy' else 'mcp__magnific__')+TOOLS[provider][operation]
    if 'file_path' in body:body['file_path']=str(_path(workspace,body['file_path']).absolute())
    envelope={'tool':tool,'arguments':body}
    identity={'schemaVersion':1,'adapterVersion':'1.0','provider':provider,'transport':TRANSPORTS[provider],'operation':operation,'request':envelope,'inputs':hashes,'context':context}
    fingerprint=hashlib.sha256(_canonical(identity)).hexdigest()
    with _lock(workspace):
        for folder in _path(workspace,'provider-jobs').iterdir():
            if folder.is_dir():
                existing=get_job(workspace,folder.name)
                if existing['fingerprint']==fingerprint:raise ValueError('duplicate request; resume job '+existing['id'])
        job={**identity,'id':uuid.uuid4().hex,'fingerprint':fingerprint,'state':'prepared','task_id':None,'outputs':[],'createdAt':datetime.now(timezone.utc).isoformat(),'verification':'local-contract-only; live verification requires separate evidence'}
        folder=_path(workspace,'provider-jobs/'+job['id'],False);folder.mkdir()
        _write_new(folder/'request.json',job)
        return deepcopy(job)

def submission_intent(workspace,job_id,authorization,budget=0):
    with _lock(workspace):
        job=get_job(workspace,job_id)
        if job['state']!='prepared':raise ValueError('submission already intended; reconcile/resume, never retry create')
        for field in ('fingerprint','provider','transport','operation'):
            if authorization.get(field)!=job[field]:raise ValueError('authorization scope mismatch: '+field)
        if authorization.get('unit')!=UNITS[job['provider']]:raise ValueError('credit units must match selected transport')
        for field in ('expectedCredits','ceilingCredits'):_number(authorization.get(field),field)
        _number(budget,'budget')
        if not 0<authorization['expectedCredits']<=authorization['ceilingCredits']<=budget:raise ValueError('paid submission requires explicit positive budget and authorized ceiling')
        if not authorization.get('approvedBy') or not authorization.get('approvalReference'):raise ValueError('approval evidence required')
        for source in job['inputs']:
            if _hash(_path(workspace,source['path']))!=source['sha256']:raise ValueError('prepared input changed')
        job['authorization']=redact(authorization);job['state']='submission-intent'
        return _event(workspace,job,'submission-intent')

def mark_unknown(workspace,job_id,reason):
    with _lock(workspace):
        job=get_job(workspace,job_id)
        if job['state']!='submission-intent' or job['task_id']:raise ValueError('unknown outcome only applies to unbound submission intent')
        job['state']='reconciliation-required';job['error']=redact(str(reason))
        return _event(workspace,job,'unknown-submission')

def _check_binding(workspace,job,task):
    for folder in _path(workspace,'provider-jobs').iterdir():
        if folder.is_dir() and folder.name!=job['id']:
            other=get_job(workspace,folder.name)
            if other['provider']==job['provider'] and other['transport']==job['transport'] and other.get('task_id')==task:raise ValueError('remote task identifier already belongs to another job')

def reconcile(workspace,job_id,evidence):
    with _lock(workspace):
        job=get_job(workspace,job_id)
        if job['state'] not in ('submission-intent','reconciliation-required'):raise ValueError('job does not need reconciliation')
        if evidence.get('decision')!='bind' or not evidence.get('task_id') or not evidence.get('evidence'):raise ValueError('bind an evidenced remote ID; absence from a list never authorizes retry')
        _check_binding(workspace,job,str(evidence['task_id']))
        job['task_id']=str(evidence['task_id']);job['state']='pending'
        return _event(workspace,job,'reconciled',evidence)

def _payload(receipt):
    if isinstance(receipt,dict) and receipt.get('isError'):raise ValueError('tool error is not a task receipt; mark unknown and reconcile')
    if not isinstance(receipt,dict):raise ValueError('receipt must be an object')
    data=receipt.get('structuredContent',receipt)
    if data is receipt and 'content' in receipt:
        texts=[x.get('text','') for x in receipt['content'] if x.get('type')=='text']
        try:data=json.loads('\n'.join(texts))
        except (ValueError,TypeError):raise ValueError('receipt requires structured JSON data') from None
    if not isinstance(data,dict):raise ValueError('receipt payload must be an object')
    if 'creation' in data:data=data['creation']
    elif 'creations' in data:
        if len(data['creations'])!=1:raise ValueError('exactly one creation receipt required')
        data=data['creations'][0]
    if not isinstance(data,dict):raise ValueError('malformed creation receipt')
    return data

def ingest_receipt(workspace,job_id,receipt):
    with _lock(workspace):
        job=get_job(workspace,job_id)
        if job['state']=='prepared':raise ValueError('submission intent required before receipt intake')
        data=_payload(receipt)
        task=data.get('task_id') if job['provider']=='meshy' else data.get('identifier')
        if not isinstance(task,str) or not task.strip():raise ValueError('remote task identifier required')
        if job['task_id'] and task!=job['task_id']:raise ValueError('remote task identifier is already bound')
        _check_binding(workspace,job,task)
        raw=str(data.get('status','')).upper()
        if raw not in STATUS:raise ValueError('unrecognized remote status')
        if data.get('task_type') and data['task_type']!={'rig':'rigging','animate':'animation'}.get(job['operation'],job['operation']):raise ValueError('remote task type mismatch')
        new_state=STATUS[raw]
        sequence=data.get('sequence')
        if sequence is not None:_number(sequence,'sequence',0)
        stale=sequence is not None and sequence<job.get('lastSequence',-1)
        # Pending/running cannot regress; terminal is sticky even for a newer conflicting receipt.
        if (job['state'] in TERMINAL and job['state']!=new_state) or stale or (job['state']=='running' and new_state=='pending'):
            return _event(workspace,job,'receipt-ignored',receipt)
        job['task_id']=task;job['task_type']=data.get('task_type',{'rig':'rigging','animate':'animation'}.get(job['operation'],job['operation']));job['state']=new_state;job['raw_status']=raw
        if sequence is not None:job['lastSequence']=sequence
        if 'progress' in data:
            _number(data['progress'],'progress',0,100);job['progress']=max(job.get('progress',0),data['progress'])
        reported=data.get('consumed_credits') if job['provider']=='meshy' else data.get('credits')
        if reported is not None:
            _number(reported,'reported cost');job['actual_cost']={'amount':reported,'unit':UNITS[job['provider']]}
            job['costCeilingExceeded']=reported>job['authorization']['ceilingCredits']
        if 'model_urls' in data or data.get('url'):job['remote_outputs']=redact(data.get('model_urls',{'glb':data['url']} if data.get('url') else {}))
        if 'result' in data:job['remote_result']=redact(data['result'])
        job['error']=redact({k:v for k,v in data.items() if k.startswith('error')})
        return _event(workspace,job,'receipt',receipt)

def resume(workspace,job_id,attempt=0):
    job=get_job(workspace,job_id)
    if not isinstance(attempt,int) or isinstance(attempt,bool) or attempt<0:raise ValueError('attempt must be a nonnegative integer')
    if not job['task_id']:
        return {'state':job['state'],'maySubmit':job['state']=='prepared','mayPoll':False,'action':'submit only after bound authorization' if job['state']=='prepared' else 'reconcile via provider task listing; never repeat create','fingerprint':job['fingerprint'],'request':job['request'] if job['state']=='prepared' else None}
    args={'task_id':job['task_id'],'task_type':job.get('task_type',{'rig':'rigging','animate':'animation'}.get(job['operation'],job['operation'])),'wait':False,'response_format':'json'} if job['provider']=='meshy' else {'creationIdentifier':job['task_id']}
    download=None
    if job['state']=='succeeded':
        if job['provider']=='meshy':
            destination='provider-jobs/'+job_id+'/download-'+uuid.uuid4().hex+'.glb'
            download={'tool':'mcp__meshy__meshy_download_model','arguments':{'task_id':job['task_id'],'task_type':args['task_type'],'format':'glb','save_to':str(_path(workspace,destination,False))},'intakeSource':destination,'note':'Save only through a connector that can access this absolute workspace path; then compute SHA-256 and use provider intake.'}
        else:download={'tool':'mcp__magnific__creations_get','arguments':args,'note':'Get a fresh authorized temporary model URL; save locally inside workspace and compute SHA-256 for provider intake. URL query credentials are deliberately not persisted.'}
    return {'download':download,'state':job['state'],'maySubmit':False,'mayPoll':job['state'] not in TERMINAL and attempt<12,'tool':'mcp__meshy__meshy_get_task_status' if job['provider']=='meshy' else 'mcp__magnific__creations_get','arguments':args,'delaySeconds':min(60,5*2**min(attempt,4)),'maxAttempts':12,'action':'download authorized output promptly' if job['state']=='succeeded' else 'rediscover connector and poll same identifier; stop after maxAttempts'}

def intake_output(workspace,job_id,source,expected_sha256):
    from studio.core import validate_glb
    with _lock(workspace):
        job=get_job(workspace,job_id)
        if job['state']!='succeeded':raise ValueError('only succeeded jobs can intake outputs')
        path=_path(workspace,source)
        if not re.fullmatch(r'[a-f0-9]{64}',str(expected_sha256)) or _hash(path)!=expected_sha256:raise ValueError('output hash mismatch')
        if path.suffix.lower()!='.glb':raise ValueError('initial validated intake supports GLB only')
        validation=validate_glb(path)
        if any(x['sha256']==expected_sha256 for x in job['outputs']):raise ValueError('duplicate output intake')
        dest_rel='provider-jobs/'+job_id+'/output-'+uuid.uuid4().hex+'.glb';dest=_path(workspace,dest_rel,False)
        with path.open('rb') as src,dest.open('xb') as dst:
            for chunk in iter(lambda:src.read(1024*1024),b''):dst.write(chunk)
        if _hash(dest)!=expected_sha256:raise ValueError('output changed while copying; intake rejected')
        job['outputs'].append({'path':dest_rel,'sha256':expected_sha256,'source':str(source),'task_id':job['task_id'],'validation':validation})
        return _event(workspace,job,'output-intake')

def describe(settings):
    settings=settings.get('providers',{})
    result=[]
    for provider,ops in TOOLS.items():
        config=settings.get(provider,{})
        for operation in ops:
            result.append({'provider':provider,'transport':TRANSPORTS[provider],'adapterVersion':'1.0','operation':operation,'implemented':True,'configured':bool(config.get('configured',False)),'session-exposed':bool(config.get('sessionExposed',False)),'last-verified-receipt':config.get('lastVerifiedReceipt'),'liveVerification':'NOT_RUN','budgetDefault':0,'models':(['meshy-7.1','meshy-6','meshy-6-lite','meshy-t2','meshy-t2.5'] if provider=='meshy' else ['v3.1-20260211','v3.0-20250812','v2.5-20250123']),'formats':['glb','fbx','obj'] if provider=='meshy' else ['glb'],'validatedIntakeFormats':['glb'],'limits':{'nativeRigMaxFaces':300000,'smartTopologyMaxFaces':{'meshy-t2':15000,'meshy-t2.5':30000},'tripoTextTriangleFaces':[500,2000000],'pollAttempts':12,'maxPollDelaySeconds':60},'outputSemantics':'provider model; local GLB intake validates container, not visual quality','bodyTypes':['humanoid'] if provider=='meshy' and operation=='rig' else ['operation-dependent; explicit context for rigs']})
    result.append({'provider':'tripo','transport':'magnific-mcp','operation':'animate','implemented':False,'reason':'Tripo retarget/animation unavailable through this transport; use explicit Blender mapping'})
    return result

def _cli(args):
    w=args.workspace;command=args.provider_command
    if command=='prepare':return prepare(w,args.provider,args.operation,_read(_path(w,args.body)),args.transport,args.input,_read(_path(w,args.context)) if args.context else None)
    if command=='intent':return submission_intent(w,args.job,_read(_path(w,args.authorization)),args.budget)
    if command=='receipt':return ingest_receipt(w,args.job,_read(_path(w,args.receipt)))
    if command=='unknown':return mark_unknown(w,args.job,args.reason)
    if command=='reconcile':return reconcile(w,args.job,_read(_path(w,args.evidence)))
    if command=='resume':return resume(w,args.job,args.attempt)
    if command=='intake':return intake_output(w,args.job,args.source,args.sha256)
    return get_job(w,args.job)

def register_commands(subparsers):
    group=subparsers.add_parser('provider',help='Prepare MCP envelopes and intake actual receipts (offline only)')
    commands=group.add_subparsers(dest='provider_command',required=True)
    for name in ('prepare','intent','receipt','unknown','reconcile','resume','intake','show'):
        parser=commands.add_parser(name);parser.set_defaults(handler=_cli)
        if name=='prepare':
            parser.add_argument('--provider',required=True,choices=sorted(TRANSPORTS));parser.add_argument('--operation',required=True);parser.add_argument('--body',required=True);parser.add_argument('--transport');parser.add_argument('--input',action='append',default=[]);parser.add_argument('--context')
        else:parser.add_argument('--job',required=True)
        if name=='intent':parser.add_argument('--authorization',required=True);parser.add_argument('--budget',type=float,default=0)
        if name=='receipt':parser.add_argument('--receipt',required=True)
        if name=='unknown':parser.add_argument('--reason',required=True)
        if name=='reconcile':parser.add_argument('--evidence',required=True)
        if name=='resume':parser.add_argument('--attempt',type=int,default=0)
        if name=='intake':parser.add_argument('--source',required=True);parser.add_argument('--sha256',required=True)
