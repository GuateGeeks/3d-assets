"""Compare staged GLBs with the current catalog before promotion; no asset mutations."""
from pathlib import Path,PureWindowsPath
import sys,json,hashlib
from geometry_fingerprint import fingerprint
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    selection=Path(sys.argv[1]).resolve();run=selection.parent
    previous=json.loads((ROOT/'index.json').read_text(encoding='utf-8'))['models']
    baseline={};unsupported=[];existing_hashes={m['sha256']:m['id'] for m in previous}
    for m in previous:
        try:
            f=fingerprint((ROOT/m['file']).read_bytes());baseline.setdefault(f['sha256'],[]).append(m['id'])
        except (KeyError,ValueError,IndexError) as e:unsupported.append({'id':m['id'],'reason':str(e)})
    comparisons=[];newprints={};newhashes={}
    for item in json.loads(selection.read_text(encoding='utf-8'))['items']:
        folder=Path(item['output'])
        if not folder.is_absolute():folder=run/PureWindowsPath(item['output']).parent.name/PureWindowsPath(item['output']).name
        data=(folder/'model.glb').read_bytes();sha=hashlib.sha256(data).hexdigest();f=fingerprint(data)
        exact=[x for x in [existing_hashes.get(sha),newhashes.get(sha)] if x]
        geometry=baseline.get(f['sha256'],[])+newprints.get(f['sha256'],[])
        comparisons.append({'id':item['id'],'sha256':sha,'fingerprint':f,'exactMatches':exact,'geometryMatches':geometry})
        newprints.setdefault(f['sha256'],[]).append(item['id']);newhashes[sha]=item['id']
    report={'baselineModels':len(previous),'baselineFingerprintCount':len(previous)-len(unsupported),'unsupported':unsupported,'comparisons':comparisons,'scope':'Hashes and invariant triangle distributions plus manual review of author/title/material variants. Nonmatches do not prove unrelated authorship.'}
    (run/'deduplication.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'baselineModels':len(previous),'unsupported':unsupported,'matches':[m for m in comparisons if m['exactMatches'] or m['geometryMatches']]}))
