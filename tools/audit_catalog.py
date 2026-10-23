"""Check multi-source catalog indices without changing captured search evidence."""
from pathlib import Path
import json,csv,hashlib
from collections import Counter
from reindex import records
ROOT=Path(__file__).resolve().parents[1]
def audit():
    models=records();ids={m['id'] for m in models};byid={m['id']:m for m in models}
    index=json.loads((ROOT/'index.json').read_text(encoding='utf-8'))['models']
    if {m['id'] for m in index}!=ids:raise ValueError('Catalog/model mismatch')
    rows=list(csv.DictReader((ROOT/'index.csv').open(encoding='utf-8-sig',newline='')))
    if len(rows)!=len(ids) or {r['id'] for r in rows}!=ids:raise ValueError('CSV mismatch')
    for row in rows:
        m=byid[row['id']]
        if any(row[k]!=m[k] for k in ['file','sha256','licenseRaw','providerId']):raise ValueError('CSV field mismatch')
    credits=(ROOT/'ATTRIBUTIONS.md').read_text(encoding='utf-8')
    if any(credits.count('`'+mid+'`')!=1 for mid in ids):raise ValueError('Credits mismatch')
    count=0
    for p in (ROOT/'indices').rglob('*.json'):
        d=json.loads(p.read_text(encoding='utf-8'));subset=d['modelIds']
        if len(subset)!=d['count'] or len(set(subset))!=len(subset) or not set(subset)<=ids:raise ValueError('Subset mismatch '+str(p))
        count+=1
    report={'schemaVersion':2,'models':len(models),'csvRows':len(rows),'subsetIndices':count,'providers':dict(Counter(m['provider'] for m in models)),'licenseCounts':dict(Counter(m['licenseRaw'] for m in models)),'result':'passed','coverageScope':'Historical Poly Pizza searches retained; enrichment is separately documented.'}
    (ROOT/'audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':audit()
