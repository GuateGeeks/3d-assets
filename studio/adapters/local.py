"""Bounded local engines. No setup, weight downloads, or implicit inference."""
import contextlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import signal
import shutil
import subprocess
import sys
from studio.core import read_json, write_json, sha256, checked_path, create_run, record_event, validate_glb

WORKER = Path(__file__).with_name('blender_worker.py')
PROFILE = Path(__file__).parents[1]/'contracts/skintokens-profile.json'

def default_profile(): return read_json(PROFILE)

def rig_route(inspection, rigid=False):
    if inspection.get('armatures',0): return 'preserve-rig'
    return 'rigid-animation' if rigid else 'organic-inference'

def validate_profile(profile):
    if profile.get('executor') not in ('local','ssh'): raise ValueError('executor must be local or ssh')
    if profile.get('commit') != default_profile()['commit']: raise ValueError('SkinTokens revision differs from pinned profile')
    for key in ('repositoryRoot','python','checkpoint','hfPath'):
        if key=='hfPath' and profile.get(key) is None: continue
        value=profile.get(key)
        if not isinstance(value,str) or not value.startswith('/') or not re.fullmatch(r'/[A-Za-z0-9_./-]+',value) or '..' in PurePosixPath(value).parts:
            raise ValueError('Configure a safe absolute POSIX path for '+key)
    if profile['executor']=='ssh':
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.@-]*',profile.get('host','')): raise ValueError('Unsafe SSH host')
        value=profile.get('stagingRoot','')
        if not re.fullmatch(r'/[A-Za-z0-9_/-]+',value) or '..' in PurePosixPath(value).parts: raise ValueError('Unsafe remote staging root')
    if not isinstance(profile.get('timeoutSeconds'),int) or not 1<=profile['timeoutSeconds']<=7200: raise ValueError('Timeout must be 1..7200 seconds')
    if profile.get('minimumVramMiB',0)<14336: raise ValueError('Minimum 14 GiB VRAM cannot be relaxed')
    return profile

def check_vram(output, minimum=14336):
    devices=[]
    for index,line in enumerate(output.strip().splitlines()):
        try: total,free=(int(x.strip()) for x in line.split(','))
        except ValueError as e: raise ValueError('Malformed VRAM probe') from e
        if total>=minimum and free>=minimum: devices.append({'totalMiB':total,'freeMiB':free,'gpuIndex':index})
    if not devices: raise ValueError('BLOCKED: SkinTokens requires >=14336 MiB total AND free GPU memory')
    return devices[0]

def skin_command(profile, source, output, use_skeleton=False):
    validate_profile(profile)
    command=[profile['python'],profile['repositoryRoot']+'/demo.py','--input',str(source),'--output',str(output),'--model_ckpt',profile['checkpoint']]
    if profile.get('hfPath'): command+=['--hf_path',profile['hfPath']]
    if profile.get('useTransfer',True): command.append('--use_transfer')
    if use_skeleton: command.append('--use_skeleton')
    return command

def verify_intake(root, source, receipt):
    if receipt.get('inputSha256')!=sha256(source): raise ValueError('Input hash mismatch')
    output=checked_path(root,receipt.get('output',''))
    if not output.is_file() or receipt.get('outputSha256')!=sha256(output): raise ValueError('Output hash mismatch')
    return output

def blender_command(config, source, run, operation, **extra):
    if operation!='demo' and (source is None or not Path(source).is_file()): raise ValueError('Input file missing')
    if config.get('executable'):
        cmd=[config['executable'],'--background','--factory-startup','--python',str(WORKER),'--']
    elif config.get('python'): cmd=[config['python'],str(WORKER)]
    else: raise ValueError('Configure blender.executable or blender.python with bpy')
    cmd += [operation,'--output-dir',str(run)]
    if source is not None: cmd+=['--input',str(source)]
    for key,value in extra.items():
        if value is not None: cmd+=['--'+key.replace('_','-'),str(value)]
    return [str(x) for x in cmd]

def descendant_sessions(pid):
    """Track sessions owned by descendants, including upstream bpy setsid()."""
    pending=[pid]; sessions=set()
    while pending:
        current=pending.pop()
        try:
            children=Path(f'/proc/{current}/task/{current}/children').read_text().split()
            for value in children:
                child=int(value); pending.append(child)
                group=os.getpgid(child)
                if group!=pid: sessions.add(group)
        except (OSError,ProcessLookupError): pass
    return sessions

def execute(command, run, cwd=None, timeout=300, name='process', env=None):
    """Terminate the whole owned process group on timeout, preserve nonzero receipts."""
    if not 1<=timeout<=7200: raise ValueError('Timeout must be 1..7200 seconds')
    options={'cwd':cwd,'env':env,'start_new_session':True} if os.name!='nt' else {'cwd':cwd,'env':env,'creationflags':subprocess.CREATE_NO_WINDOW}
    with (run/(name+'.log')).open('w') as log:
        proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,**options)
        try: code=proc.wait(timeout=timeout)
        except BaseException:
            sessions=descendant_sessions(proc.pid) if os.name!='nt' else set()
            for group in sessions:
                try: os.killpg(group,signal.SIGTERM)
                except ProcessLookupError: pass
            if os.name!='nt': os.killpg(proc.pid,signal.SIGTERM)
            else: proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name!='nt': os.killpg(proc.pid,signal.SIGKILL)
                else: proc.kill()
                proc.wait()
            for group in sessions:
                try: os.killpg(group,signal.SIGKILL)
                except ProcessLookupError: pass
            record_event(run,{'stage':name,'status':'FAIL','reason':'timeout or interruption'})
            raise
    record_event(run,{'stage':name,'exitCode':code,'command':command,'log':name+'.log'})
    if code: raise ValueError(f'{name} exited {code}; see {run/(name+".log")}')

def snapshot_sources(repo, destination, commit='HEAD'):
    """Copy only Git-tracked regular source files, never environments or weights."""
    entries=query(['git','-C',str(repo),'ls-files','-z']).split('\0')
    destination.mkdir(parents=True,exist_ok=False)
    for relative in filter(None,entries):
        source=checked_path(repo,relative)
        if source.suffix.lower() in ('.ckpt','.safetensors','.pt','.pth','.blend'):
            raise ValueError('Tracked model/binary asset requires explicit separate read-only configuration')
        if not source.is_file(): raise ValueError('Only regular tracked source files may be staged')
        target=destination/relative; target.parent.mkdir(parents=True,exist_ok=True)
        result=subprocess.run(['git','-C',str(repo),'show',commit+':'+relative],capture_output=True,timeout=30,check=True)
        target.write_bytes(result.stdout)
    return destination

def query(command,cwd=None):
    p=subprocess.run(command,cwd=cwd,text=True,capture_output=True,timeout=30,check=False)
    if p.returncode: raise ValueError('Preflight failed: '+p.stderr[-1000:])
    return p.stdout.strip()

@contextlib.contextmanager
def heavy_lock(workspace, shared_path=None):
    import fcntl
    lock=workspace/'locks/heavy-gpu.lock'; lock.parent.mkdir(parents=True,exist_ok=True)
    with contextlib.ExitStack() as stack:
        paths=[lock]
        if shared_path is not None:
            shared_path=Path(shared_path)
            if not shared_path.is_absolute() or not shared_path.is_file() or shared_path.is_symlink(): raise ValueError('Configure an existing absolute sharedGpuLock')
            paths.insert(0,shared_path)
        for path in paths:
            # Existing lab lock is opened read-only, preserving owner metadata.
            stream=stack.enter_context(path.open('r' if path==shared_path else 'a'))
            try: fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as e: raise ValueError('Another heavy GPU job is active') from e
        yield
def skin_preflight(profile):
    validate_profile(profile)
    remote=profile['executor']=='ssh'
    prefix=['ssh','-oBatchMode=yes','-oConnectTimeout=15',profile['host']] if remote else []
    def probe(cmd): return query(prefix+[shlex.join(cmd)] if remote else cmd)
    head=probe(['git','-C',profile['repositoryRoot'],'rev-parse','HEAD'])
    if head!=profile['commit']: raise ValueError('SkinTokens checkout revision mismatch')
    if probe(['git','-C',profile['repositoryRoot'],'status','--porcelain','--untracked-files=no']): raise ValueError('SkinTokens tracked sources are modified')
    paths=[profile['python'],profile['checkpoint'],profile['repositoryRoot']+'/demo.py']
    if profile.get('hfPath'): paths.append(profile['hfPath']+'/config.json')
    for path in paths:
        probe(['test','-f',path])
    gpu=check_vram(probe(['nvidia-smi','--query-gpu=memory.total,memory.free','--format=csv,noheader,nounits']),profile['minimumVramMiB'])
    return {'commit':head,'gpu':gpu,'executor':profile['executor']}

def run_skin(args, source, run):
    if source.suffix.lower()!='.glb': raise ValueError('Studio SkinTokens intake requires a self-contained GLB')
    inspection=validate_glb(source)
    if inspection.get('skins',0) and not args.use_skeleton:
        return {'status':'NOT_RUN','route':'preserve-rig','output':str(source),'reason':'Existing skin preserved; --use-skeleton explicitly requests reskinning'}
    input_hash=sha256(source)
    p=dict(default_profile(),**args.settings.get('skintokens',{})); validate_profile(p)
    if args.dry_run: return {'status':'NOT_RUN','command':skin_command(p,source,run/'rigged.glb',args.use_skeleton),'preflight':'NOT_RUN'}
    shared=args.settings.get('sharedGpuLock')
    if p['executor']=='local' and not shared: raise ValueError('Configure sharedGpuLock before local GPU inference')
    with heavy_lock(args.workspace,shared):
        preflight=skin_preflight(p); write_json(run/'preflight.json',preflight)
        env=os.environ.copy(); env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES=str(preflight['gpu']['gpuIndex']))
        if p['executor']=='local':
            snapshot=snapshot_sources(Path(p['repositoryRoot']),run/'engine',p['commit'])
            staged=dict(p,repositoryRoot=str(snapshot))
            staged_input=run/'input.glb'; shutil.copyfile(source,staged_input)
            if sha256(staged_input)!=input_hash: raise ValueError('Input changed during staging')
            env.update(TMPDIR=str(run),XDG_CACHE_HOME=str(run/'cache'),TORCH_HOME=str(run/'cache/torch'),HF_HOME=str(run/'cache/huggingface'))
            execute(skin_command(staged,staged_input,run/'rigged.glb',args.use_skeleton),run,snapshot,p['timeoutSeconds'],'skintokens',env)
            receipt={'inputSha256':input_hash,'output':'rigged.glb','outputSha256':sha256(run/'rigged.glb')}
        else:
            remote=p['stagingRoot']+'/'+run.name
            ssh=['ssh','-oBatchMode=yes','-oConnectTimeout=15',p['host']]
            query(ssh+[shlex.join(['mkdir','-m','700',remote])])
            query(ssh+['mkdir '+shlex.quote(remote+'/engine')+' && git -C '+shlex.quote(p['repositoryRoot'])+' archive '+shlex.quote(p['commit'])+' | tar -x -C '+shlex.quote(remote+'/engine')])
            execute(['scp','-oBatchMode=yes',str(source),p['host']+':'+remote+'/input.glb'],run,name='stage-input')
            execute(['scp','-oBatchMode=yes',str(Path(__file__).with_name('remote_runner.py')),p['host']+':'+remote+'/supervisor.py'],run,name='stage-supervisor')
            remotehash=query(ssh+[shlex.join(['sha256sum',remote+'/input.glb'])]).split()[0]
            if remotehash!=input_hash: raise ValueError('Remote staged input hash mismatch')
            cmd=skin_command(dict(p,repositoryRoot=remote+'/engine'),remote+'/input.glb',remote+'/rigged.glb',args.use_skeleton)
            # flock is held on the executor, in addition to the orchestration lock.
            shell='cd '+shlex.quote(remote+'/engine')+' && '+shlex.join(['flock','-n',p['stagingRoot']+'/heavy-gpu.lock','env','HF_HUB_OFFLINE=1','TRANSFORMERS_OFFLINE=1','PYTHONDONTWRITEBYTECODE=1','CUDA_VISIBLE_DEVICES='+str(preflight['gpu']['gpuIndex']),'TMPDIR='+remote,'XDG_CACHE_HOME='+remote+'/cache',p['python'],remote+'/supervisor.py','--timeout',str(p['timeoutSeconds']),'--']+cmd)
            execute(ssh+[shell],run,timeout=min(7200,p['timeoutSeconds']+20),name='skintokens-ssh')
            digest=query(ssh+[shlex.join(['sha256sum',remote+'/rigged.glb'])]).split()[0]
            execute(['scp','-oBatchMode=yes',p['host']+':'+remote+'/rigged.glb',str(run/'rigged.glb')],run,name='receive-output')
            receipt={'inputSha256':remotehash,'output':'rigged.glb','outputSha256':digest,'remoteRun':remote}
        output=verify_intake(run,source,receipt); validation=validate_glb(output)
        if not validation.get('skins') or not validation.get('meshes'): raise ValueError('SkinTokens output lacks mesh and skin')
        write_json(run/'intake.json',receipt)
        return {'status':'PASS','run':str(run),'output':str(output),'validation':validation,'quality':'NOT_RUN'}

def unirig_command(config, source, operation, timeout):
    root=Path(config.get('laboratoryRoot',''))
    python=config.get('python')
    if not root.is_absolute() or not (root/'lab/lab.py').is_file() or not python or not Path(python).is_file():
        raise ValueError('Configure UniRig laboratoryRoot and existing python')
    if operation not in ('ingest','rig'): raise ValueError('UniRig supports existing candidate ingest or rig')
    if not source.is_file() or source.suffix.lower()!='.json': raise ValueError('UniRig requires a candidate JSON manifest, never a bare mesh')
    if not 1<=timeout<=(300 if operation=='ingest' else 7200): raise ValueError('Invalid UniRig timeout')
    command=[python,str(root/'lab/lab.py'),operation,'--candidate',str(source),'--timeout',str(timeout)]
    if operation=='rig': command+=['--stage','all']
    return command


def describe(settings):
    return [{'id':engine,'implemented':True,'configured':bool(settings.get(engine)),
             'lastVerifiedReceipt':settings.get(engine,{}).get('lastVerifiedReceipt'),
             'operations':operations,'runtimeVerification':'NOT_RUN'}
            for engine,operations in [('blender',['inspect','export','demo','retarget']),('unirig',['ingest','rig']),('skintokens',['rig'])]]

def handler(args):
    allowed={'blender':('inspect','export','demo','retarget'),'unirig':('ingest','rig'),'skintokens':('rig',)}
    if args.operation not in allowed[args.engine]: raise ValueError('Operation is not supported by selected engine')
    source=checked_path(args.workspace,args.input) if args.input else None
    run=create_run(args.workspace,'backend-'+args.engine,{'input':str(source) if source else None})
    if args.engine=='skintokens':
        if source is None: raise ValueError('Input required')
        return run_skin(args,source,run)
    if args.engine=='blender':
        motion=checked_path(args.workspace,args.motion) if args.motion else None
        mapping=checked_path(args.workspace,args.mapping) if args.mapping else None
        inputs={role:{'path':str(path),'sha256':sha256(path),'bytes':path.stat().st_size} for role,path in [('input',source),('motion',motion),('mapping',mapping)] if path is not None}
        input_manifest={'schemaVersion':1,'operation':args.operation,'inputs':inputs,'workerSha256':sha256(WORKER),'retargetCodeSha256':sha256(WORKER.with_name('retarget.py'))}
        write_json(run/'blender-inputs.json',input_manifest)
        cmd=blender_command(args.settings.get('blender',{}),source,run,args.operation,motion=motion,mapping=mapping)
        if args.dry_run: return {'status':'NOT_RUN','command':cmd,'inputManifest':str(run/'blender-inputs.json'),'inputManifestSha256':sha256(run/'blender-inputs.json')}
        env=os.environ.copy(); env.update(CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2')
        execute(cmd,run,timeout=args.timeout,env=env,name='blender')
        for entry in inputs.values():
            path=Path(entry['path'])
            if not path.is_file() or sha256(path)!=entry['sha256']:
                record_event(run,{'stage':'blender-lineage','status':'FAIL','reason':'Input changed during execution','path':str(path)})
                raise ValueError('Blender input changed during execution: '+str(path))
        report=read_json(run/'inspection.json')
        names=['inspection.json']+report.get('artifacts',[])
        outputs=[{'path':name,'sha256':sha256(checked_path(run,name)),'bytes':checked_path(run,name).stat().st_size} for name in names]
        output_manifest={'schemaVersion':1,'status':'PASS','inputsUnchanged':True,'inputManifestSha256':sha256(run/'blender-inputs.json'),'outputs':outputs}
        write_json(run/'blender-outputs.json',output_manifest)
        lineage={'inputManifest':str(run/'blender-inputs.json'),'inputManifestSha256':sha256(run/'blender-inputs.json'),'outputManifest':str(run/'blender-outputs.json'),'outputManifestSha256':sha256(run/'blender-outputs.json')}
        record_event(run,{'stage':'blender-lineage','status':'PASS',**lineage})
        return dict(report,run=str(run),lineage=lineage)
    config=args.settings.get('unirig',{})
    if source is None: raise ValueError('Candidate manifest required')
    cmd=unirig_command(config,source,args.operation,args.timeout)
    root=Path(config['laboratoryRoot']); runs=root/'lab/.local/runs'
    if args.dry_run: return {'status':'NOT_RUN','command':cmd,'writesTo':str(runs),'lock':str(root/'lab/.local/locks/unirig.lock'),'normalization':'Existing ingest explicit 2m preparation; rig restores candidate original dimensions'}
    before=set(runs.iterdir()) if runs.exists() else set()
    env=os.environ.copy(); env.update(PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    # The existing runner owns its own exclusive lock, CUDA environment,
    # normalization, original-scale restoration, and immutable per-stage receipts.
    execute(cmd,run,root,min(7200,args.timeout*8),'unirig',env)
    children=[p for p in runs.iterdir() if p not in before and (p/'run.json').is_file()]
    children=[p for p in children if read_json(p/'run.json').get('command')==args.operation]
    if len(children)!=1: raise ValueError('Cannot identify exactly one delegated UniRig receipt')
    child=children[0]/'run.json'; receipt=read_json(child)
    if receipt.get('status')!='success': raise ValueError('Delegated runner did not record success')
    write_json(run/'unirig-child-receipt.json',receipt)
    result={'status':'PASS','run':str(run),'childReceipt':str(child),'childReceiptSha256':sha256(child),'quality':'NOT_RUN'}
    if args.operation=='ingest': result['preparedManifest']=str(children[0]/'creation-prepared.json')
    if args.operation=='rig': result['restoredCandidate']=receipt.get('restoredCandidate')
    write_json(run/'unirig-delegation.json',result)
    return result
def register_commands(subparsers):
    p=subparsers.add_parser('backend',help='Explicit bounded local engine operations')
    p.add_argument('engine',choices=['blender','unirig','skintokens']); p.add_argument('operation',choices=['inspect','export','demo','retarget','rig','ingest'])
    p.add_argument('--input'); p.add_argument('--motion'); p.add_argument('--mapping'); p.add_argument('--timeout',type=int,default=300); p.add_argument('--dry-run',action='store_true'); p.add_argument('--use-skeleton',action='store_true')
    p.set_defaults(handler=handler)
