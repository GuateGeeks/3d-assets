"""Read-only local viewer for the Claude animal-cell benchmark (loopback only).

Shows each replica's last run: gates, score, six renders and the GLB in
model-viewer (gallery/vendor). Data comes from results.json plus sealed runs;
only GLB/PNG files of runs listed there are served, never sources or logs.
Usage: serve.py --root BATCH --results results.json --port 4397
"""
import argparse
import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
VENDOR = REPO / 'gallery' / 'vendor'
VIEWS = ('three-quarter', 'front', 'side', 'back', 'wireframe', 'reimport-three-quarter')
SAFE = re.compile(r'^[A-Za-z0-9_-]+$')


def page(results):
    rows = []
    for replica, item in results['replicas'].items():
        last = item['runs'][-1]
        score = last['scoreTotal'] if last['scoreTotal'] is not None else '—'
        images = ''.join(f'<figure><img loading="lazy" src="/run/{replica}/{v}.png" alt="{v}"><figcaption>{v}</figcaption></figure>' for v in VIEWS)
        rows.append(f'''<section><h2>{replica} · {html.escape(item['family'])} #{item['authoring']} — {item['finalStatus']}</h2>
<p>Última etapa: {last['stage']} ({last['runId']}) · técnica {last['technical']} · visual {last['visual']} · contenido {last['content']} ·
puntuación {score} · correcciones {item['correctionsUsed']} · {last['triangles']} triángulos · {last['glbBytes']} bytes</p>
<model-viewer src="/run/{replica}/asset.glb" camera-controls camera-orbit="36.87deg 53.74deg 0.75m" field-of-view="35deg"
 environment-image="neutral" alt="Célula animal {replica}"></model-viewer><div class="views">{images}</div></section>''')
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Benchmark Claude · célula animal</title><script type="module" src="/vendor/model-viewer.min.js"></script>
<style>body{{font-family:system-ui,sans-serif;margin:16px;background:#f4f5f7;color:#1d2330}}section{{background:#fff;border-radius:8px;padding:12px;margin:12px 0}}
model-viewer{{width:100%;height:420px;background:#e4e7eb}}.views{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px}}
img{{width:100%;border-radius:4px}}figure{{margin:0}}figcaption{{font-size:12px}}h2{{font-size:18px;margin:0 0 6px}}</style></head>
<body><h1>Benchmark Claude · célula animal (exploratorio, n=3 por familia)</h1>
<p>Revisión ciega asistida por Opus; no es evaluación docente externa. Ver RESULTS.md.</p>{''.join(rows)}</body></html>'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--results', type=Path, default=HERE / 'results.json')
    p.add_argument('--port', type=int, default=4397)
    args = p.parse_args()
    results = json.loads(args.results.read_text(encoding='utf-8'))
    mapping = json.loads((args.root / 'coordinator/mapping.json').read_text(encoding='utf-8'))['replicas']
    files = {}
    for replica, item in results['replicas'].items():
        run = args.root / mapping[replica]['session'] / 'runs' / item['runs'][-1]['runId']
        files[f'/run/{replica}/asset.glb'] = (run / 'asset.glb', 'model/gltf-binary')
        for view in VIEWS:
            files[f'/run/{replica}/{view}.png'] = (run / 'renders' / (view + '.png'), 'image/png')
    files['/vendor/model-viewer.min.js'] = (VENDOR / 'model-viewer.min.js', 'text/javascript; charset=utf-8')
    body = page(results).encode('utf-8')

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split('?')[0]
            if path in ('/', '/index.html'):
                data, kind = body, 'text/html; charset=utf-8'
            elif path in files and files[path][0].is_file():
                data, kind = files[path][0].read_bytes(), files[path][1]
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'http://127.0.0.1:{args.port}/', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
