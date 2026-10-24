"""Read-only GPT pilot vs Claude benchmark viewer. Run with Python 3.10+.

python creation-lab/benchmarks/claude-animal-cell/compare.py --claude-root creation-lab/.local/MI-BATCH

GET /api/compare returns {brief, groups:[{id, title, note, conditions:[...]}]}.
GPT conditions come from the pilot viewer's own discovery (newest completed run,
review only when its runId and six image hashes match). Claude replicas show
their newest completed run; a blind review applies only when blind-map.json
links it to that runId and its declared image hashes match the renders.
The Claude author model is coordinator-only data: never serve this to reviewers.
Only selected run artifacts are exposed; no logs, sources, paths or listing.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
PILOT = BASE.parent / 'animal-cell-20261022'
VENDOR = ROOT / 'gallery' / 'vendor'
PORT = 4394
VIEWS = ('front', 'side', 'back', 'three-quarter', 'wireframe', 'reimport-three-quarter')
SAFE = re.compile(r'^[A-Za-z0-9_-]+$')
STATIC = {
    '/': (BASE / 'compare.html', 'text/html; charset=utf-8'),
    '/compare.js': (BASE / 'compare.js', 'text/javascript; charset=utf-8'),
    '/compare.css': (BASE / 'compare.css', 'text/css; charset=utf-8'),
    '/viewer.css': (PILOT / 'viewer.css', 'text/css; charset=utf-8'),
    '/vendor/model-viewer.min.js': (VENDOR / 'model-viewer.min.js', 'text/javascript; charset=utf-8'),
    '/vendor/inter-400.woff2': (VENDOR / 'inter-400.woff2', 'font/woff2'),
    '/vendor/inter-600.woff2': (VENDOR / 'inter-600.woff2', 'font/woff2'),
}
CLAUDE_ROOT = None


def load_pilot_server():
    # Reuse the pilot's discovery and review matching instead of re-deriving them.
    import sys
    sys.path.insert(0, str(PILOT))
    spec = importlib.util.spec_from_file_location('pilot_serve', PILOT / 'serve.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pilot = load_pilot_server()


def read_json(path, fallback=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError, UnicodeError):
        return fallback


def inside(path, root):
    try:
        return path.is_file() and path.resolve().is_relative_to(root.resolve())
    except (OSError, RuntimeError):
        return False


def numeric(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gpt_group(assets):
    data, pilot_assets = pilot.discover()
    conditions = []
    for entry in data['conditions']:
        urls = {}
        for key in ('urlGlb', 'urlBlend', 'urlPreview'):
            url = entry.get(key)
            if url in pilot_assets:
                urls[key] = '/gpt' + url
                assets[urls[key]] = pilot_assets[url]
            else:
                urls[key] = None
        review = entry.get('review')
        runs = [p for p in (pilot.OUTPUT / entry['id']).glob('*') if p.is_dir() and pilot.read_complete_manifest(p)] if entry['runId'] else []
        conditions.append({**entry, **urls, 'family': 'GPT', 'stage': 'final',
                           'iterations': max(len(runs) - 1, 0), 'iterationKind': ['reparación técnica', 'reparaciones técnicas'],
                           'review': None if not review else {
                               'visual': review.get('visual'), 'biological': review.get('biological'),
                               'score': numeric(review.get('score')), 'summary': review.get('summary')}})
    return {'id': 'gpt', 'title': 'GPT · piloto 22 oct', 'conditions': conditions,
            'note': 'Una propuesta por condición; máximo una reparación técnica, sin correcciones visuales. Revisor ciego en contexto nuevo.'}


def claude_review(root, replica, run):
    blind_map = read_json(root / 'coordinator' / 'blind-map.json', {}) or {}
    for blind, link in blind_map.items():
        if not (SAFE.fullmatch(blind) and isinstance(link, dict) and link.get('replica') == replica and link.get('runId') == run.name):
            continue
        review = read_json(root / 'blind' / blind / 'review.json')
        if not isinstance(review, dict):
            continue
        declared = review.get('imageSha256') or {}
        try:
            if any(declared.get(view) != sha256(run / 'renders' / f'{view}.png') for view in VIEWS):
                continue
        except OSError:
            continue
        status = lambda gate: (review.get(gate) or {}).get('status') if isinstance(review.get(gate), dict) else review.get(gate)
        scores = review.get('scores')
        score = sum(scores.values()) if isinstance(scores, dict) and scores and all(numeric(v) is not None for v in scores.values()) else None
        reasons = [(review.get(gate) or {}).get('reason') for gate in ('visual', 'content') if isinstance(review.get(gate), dict)]
        return {'visual': status('visual'), 'biological': status('content'), 'score': score,
                'summary': ' '.join(r for r in reasons if isinstance(r, str))}
    return None


def claude_group(root, assets):
    mapping = (read_json(root / 'coordinator' / 'mapping.json', {}) or {}).get('replicas', {})
    conditions = []
    for replica in sorted(mapping, key=lambda r: int(r[1:]) if r[1:].isdigit() else 0):
        if not SAFE.fullmatch(replica):
            continue
        folder = root / 'sessions' / replica / 'runs'
        try:
            runs = sorted((p for p in folder.iterdir() if p.is_dir() and SAFE.fullmatch(p.name)), key=lambda p: p.name, reverse=True)
        except OSError:
            runs = []
        complete = [(run, m) for run in runs if inside(run / 'asset.glb', run) and isinstance(m := pilot.read_complete_manifest(run), dict)]
        entry = {'family': 'Claude', 'id': replica, 'model': None, 'reasoningEffort': None, 'runId': None,
                 'technical': 'NOT_RUN', 'stage': None, 'seconds': None, 'glbBytes': None,
                 'metrics': {'triangles': None, 'meshes': None, 'materials': None}, 'parts': None,
                 'urlGlb': None, 'urlBlend': None, 'urlPreview': None, 'review': None,
                 'iterations': max(len(complete) - len({m.get('stage') for _, m in complete}), 0),
                 'iterationKind': ['corrección', 'correcciones']}
        if complete:
            run, manifest = complete[0]
            author = manifest.get('author') or {}
            checks = read_json(run / 'build-checks.json', {}) or {}
            metrics = checks.get('metrics') if isinstance(checks.get('metrics'), dict) else {}
            materials = metrics.get('materials')
            seconds = [numeric(step.get('seconds')) for step in manifest.get('stages') or [] if isinstance(step, dict)]
            entry.update(model=author.get('model'), reasoningEffort=author.get('reasoningEffort'), runId=run.name,
                         technical=manifest.get('technical', 'NOT_RUN'), stage=manifest.get('stage'),
                         seconds=sum(s for s in seconds if s is not None) if seconds else None,
                         glbBytes=(run / 'asset.glb').stat().st_size,
                         metrics={'triangles': numeric(metrics.get('triangles')), 'meshes': numeric(metrics.get('meshes')),
                                  'materials': len(materials) if isinstance(materials, (list, dict)) else numeric(materials)},
                         parts=read_json(run / 'parts.json') if inside(run / 'parts.json', run) else None,
                         review=claude_review(root, replica, run))
            for filename, key, mime in [('asset.glb', 'urlGlb', 'model/gltf-binary'), ('source.blend', 'urlBlend', 'application/octet-stream'),
                                        ('renders/three-quarter.png', 'urlPreview', 'image/png')]:
                if inside(run / filename, run):
                    url = f'/claude/{replica}/{run.name}/{filename}'
                    assets[url] = (run / filename, mime)
                    entry[key] = url
        conditions.append(entry)
    return {'id': 'claude', 'title': 'Claude · benchmark 23 oct (en curso)', 'conditions': conditions,
            'note': 'Tres autorías por familia; blockout y detalle con hasta dos correcciones visuales. Revisor ciego Opus 5.5. Se muestra el último run completo de cada réplica.'}


def discover():
    assets = {}
    groups = [gpt_group(assets), claude_group(CLAUDE_ROOT, assets)]
    return {'brief': read_json(PILOT / 'brief.json', {}), 'groups': groups}, assets


class Handler(BaseHTTPRequestHandler):
    server_version = 'CellCompare'
    sys_version = ''

    def do_HEAD(self):
        self.respond(head=True)

    def do_GET(self):
        self.respond()

    def do_POST(self):
        self.send_error(405, 'Method not allowed')

    do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_POST

    def respond(self, head=False):
        if self.headers.get('Host', '') not in (f'127.0.0.1:{PORT}', f'localhost:{PORT}'):
            self.send_error(403, 'Forbidden')
            return
        if '%' in self.path or '\\' in self.path or '..' in self.path or any(ord(c) < 32 for c in self.path):
            self.send_error(404, 'Not found')
            return
        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
            self.send_error(404, 'Not found')
            return
        data, assets = discover()
        if parsed.path == '/api/compare':
            content = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(200)
            pilot.Handler.headers_for(self, 'application/json; charset=utf-8', len(content))
            self.end_headers()
            if not head:
                self.wfile.write(content)
            return
        route = STATIC.get(parsed.path) or assets.get(parsed.path)
        if route is None or not route[0].is_file():
            self.send_error(404, 'Not found')
            return
        file, mime = route
        try:
            with file.open('rb') as stream:
                self.send_response(200)
                pilot.Handler.headers_for(self, mime, file.stat().st_size)
                if file.suffix == '.blend':
                    self.send_header('Content-Disposition', 'attachment; filename="source.blend"')
                self.end_headers()
                if not head:
                    while chunk := stream.read(262144):
                        self.wfile.write(chunk)
        except (OSError, BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--claude-root', type=Path, required=True, help='Claude batch folder (contains coordinator/, sessions/, blind/)')
    parser.add_argument('--gpt-runs', type=Path, default=pilot.OUTPUT, help='Restored GPT pilot runs (A-F)')
    parser.add_argument('--gpt-reviews', type=Path, default=pilot.REVIEWS, help='GPT pilot reviews.json')
    parser.add_argument('--port', type=int, default=PORT, help='Local HTTP port (default: 4394)')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    if not (args.claude_root / 'coordinator' / 'mapping.json').is_file():
        parser.error('--claude-root must contain coordinator/mapping.json')
    PORT = args.port
    CLAUDE_ROOT = args.claude_root.resolve()
    pilot.OUTPUT = args.gpt_runs.resolve()
    pilot.REVIEWS = args.gpt_reviews.resolve()
    print(f'Comparación GPT vs Claude: http://127.0.0.1:{PORT}', flush=True)
    try:
        ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
