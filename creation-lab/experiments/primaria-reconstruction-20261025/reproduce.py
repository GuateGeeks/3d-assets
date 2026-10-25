"""Rebuild the delivered model using only bundled recipe + Blender.
python reproduce.py --blender /absolute/path/to/blender --output /new/output/directory
"""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--blender',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--recipe')
    a=p.parse_args()
    root=Path(__file__).resolve().parent
    out=Path(a.output).resolve()
    if out.exists():raise SystemExit('Output must be a NEW directory; previous evidence is never overwritten.')
    recipe=Path(a.recipe).resolve() if a.recipe else root/'completion-recipe'
    out.mkdir(parents=True)
    for name in ['generator.py','brief.json']:
        shutil.copy2(recipe/name,out/name)
    shutil.copytree(recipe/'code',out/'code',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    receipts=[]
    for stage in ['build','reopen','reimport']:
        command=[a.blender,'--background','--factory-startup','--python',str(out/'code'/'worker.py'),'--',stage,str(out)]
        run=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
        (out/(stage+'.log')).write_text(run.stdout,encoding='utf-8')
        receipts.append({'stage':stage,'returncode':run.returncode})
        if run.returncode:break
    checks={}
    for name in ['build','reopen','reimport']:
        f=out/(name+'-result.json')
        checks[name]=json.loads(f.read_text(encoding='utf-8')).get('status') if f.exists() else 'NOT_RUN'
    report={'technical': 'PASS' if all(v=='PASS' for v in checks.values()) else 'FAIL',
      'visual':'NOT_RUN','content':'NOT_RUN','runs':receipts,'checks':checks,
      'note':'Reproducibility only. Open six rendered images before claiming visual likeness.',
      'sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [out/'asset.glb',out/'source.blend'] if f.exists()}}
    (out/'reproduction.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    if report['technical']!='PASS':sys.exit(1)
if __name__=='__main__':main()
