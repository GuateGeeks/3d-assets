"""Immutable local benchmark runner. No external model API calls."""
import argparse, ast, hashlib, json, os, shutil, subprocess, sys, time, uuid
from datetime import datetime,timezone
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
OUTPUT=ROOT/'creation-lab/.local/benchmarks/animal-cell-20261022'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,data):Path(path).write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')

def check_source(path):
    source=path.read_text(encoding='utf-8-sig');tree=ast.parse(source)
    allowed={'bpy','math','random','mathutils'}
    for node in ast.walk(tree):
        if isinstance(node,ast.Import) and any(n.name.split('.')[0] not in allowed for n in node.names):raise ValueError('Unexpected import')
        if isinstance(node,ast.ImportFrom) and (node.module or '').split('.')[0] not in allowed:raise ValueError('Unexpected import')
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {'open','exec','eval','compile','__import__'}:raise ValueError('Disallowed external execution or IO')
    return source

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('condition',choices=list('ABCDEF'))
    p.add_argument('--blender',type=Path,required=True);p.add_argument('--attempt',type=int,default=1);p.add_argument('--timeout',type=int,default=600)
    a=p.parse_args();protocol=json.loads((BASE/'protocol.json').read_text(encoding='utf-8'))
    condition=next(c for c in protocol['conditions'] if c['id']==a.condition)
    source=BASE/'conditions'/a.condition/'generator.py';check_source(source)
    rid=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    run=OUTPUT/a.condition/rid;run.mkdir(parents=True,exist_ok=False);(run/'code').mkdir()
    for name in ['brief.json','protocol.json','AUTHORING.md']:shutil.copy2(BASE/name,run/name)
    shutil.copy2(source,run/'generator.py');shutil.copy2(BASE/'worker.py',run/'code/worker.py')
    shutil.copy2(ROOT/'lab/scripts/creation_geometry.py',run/'code/geometry_qa.py');shutil.copy2(__file__,run/'code/runner.py')
    manifest={'schemaVersion':1,'runId':rid,'condition':condition,'attempt':a.attempt,'status':'RUNNING','technical':'NOT_RUN','visual':'NOT_RUN','biological':'NOT_RUN','createdAt':datetime.now(timezone.utc).isoformat(),'stages':[],'replicate':1,'scope':'single-brief pilot; one artifact per model-effort condition','seed':protocol['seed'],'cost':{'status':'NOT_AVAILABLE','reason':'No model billing/token telemetry exposed'},'generatorSha256':digest(run/'generator.py')}
    start=time.monotonic()
    try:
        for stage in ['build','reopen','reimport']:
            command=[str(a.blender),'--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',str(run/'code/worker.py'),'--',stage,str(run)]
            t=time.monotonic();print(json.dumps({'condition':a.condition,'run':str(run),'stage':stage}),flush=True)
            with (run/(stage+'.log')).open('w',encoding='utf-8') as log:
                proc=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=a.timeout,env={**os.environ,'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','PYTHONDONTWRITEBYTECODE':'1'})
            manifest['stages'].append({'name':stage,'returncode':proc.returncode,'seconds':round(time.monotonic()-t,3),'command':command})
            if proc.returncode:raise RuntimeError(stage+' failed; see '+str(run/(stage+'.log')))
        results=[json.loads((run/(stage+'-result.json')).read_text(encoding='utf-8')) for stage in ['build','reopen','reimport']]
        limits=json.loads((run/'brief.json').read_text(encoding='utf-8'))['budgets']
        manifest['technical']='PASS' if all(x['status']=='PASS' for x in results) and (run/'asset.glb').stat().st_size<=limits['glbBytes'] else 'FAIL'
        manifest['status']=manifest['technical'];manifest['glbBytes']=(run/'asset.glb').stat().st_size
    except Exception as exc:
        manifest.update(status='FAIL',technical='FAIL',error=str(exc))
    manifest['seconds']=round(time.monotonic()-start,3)
    manifest['artifacts']={str(f.relative_to(run)).replace('\\','/'):digest(f) for f in sorted(run.rglob('*')) if f.is_file()}
    write(run/'manifest.json',manifest);(run/'COMPLETE').write_text(digest(run/'manifest.json')+'\n')
    print(json.dumps({'condition':a.condition,'run':str(run),'technical':manifest['technical'],'seconds':manifest['seconds'],'error':manifest.get('error')}),flush=True)
    return 0 if manifest['technical']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
