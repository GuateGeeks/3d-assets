"""Read-only HTTP integration checks for the local benchmark viewer."""
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = Path(__file__).resolve().parent
ORIGIN = 'http://127.0.0.1:4393'


def request(path, method='GET', headers=None):
    try:
        with urlopen(Request(ORIGIN+path, method=method, headers=headers or {}), timeout=10) as response:
            return response.status, response.read(), dict(response.headers)
    except HTTPError as error:
        return error.code, error.read(), dict(error.headers)


def main():
    checks = []
    for path, expected, method, headers in [('/',200,'GET',{}),('/api/benchmark',200,'GET',{}),
        ('/vendor/model-viewer.min.js',200,'HEAD',{}),('/../brief.json',404,'GET',{}),
        ('/%2e%2e/brief.json',404,'GET',{}),('/viewer.js?path=../',404,'GET',{}),
        ('/api/benchmark',403,'GET',{'Host':'untrusted.example'}),('/api/benchmark',405,'POST',{}),
        ('/protocol.json',404,'GET',{}),('/assets/',404,'GET',{})]:
        status, body, returned_headers = request(path, method, headers)
        checks.append({'path':path,'method':method,'expected':expected,'actual':status,'pass':status==expected})
    status, body, headers = request('/api/benchmark')
    data = json.loads(body)
    checks.append({'name':'six-conditions','pass':[v['id'] for v in data['conditions']]==list('ABCDEF')})
    for condition in data['conditions']:
        if not condition['urlGlb']:
            continue
        code, binary, _ = request(condition['urlGlb'])
        checks.append({'name':condition['id']+'-glb-download','pass':code==200 and binary[:4]==b'glTF' and len(binary)==condition['glbBytes']})
        checks.append({'name':condition['id']+'-labels','pass':len(condition['parts']['parts'])==13})
    report = {'schemaVersion':1,'status':'PASS' if all(c['pass'] for c in checks) else 'FAIL','checks':checks}
    (BASE/'viewer-http-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
    if report['status']!='PASS':raise SystemExit(1)


if __name__ == '__main__':main()
