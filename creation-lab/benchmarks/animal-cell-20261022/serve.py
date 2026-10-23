"""Read-only animal-cell pilot viewer. Run with Python 3.10+: python serve.py.

GET /api/benchmark returns {brief, conditions:[{id, model, reasoningEffort,
runId, technical, seconds, glbBytes, metrics:{triangles,meshes,materials},
parts, urlGlb, urlBlend, urlPreview, review}]}. Missing values are null;
technical is NOT_RUN when no artifact exists. parts is the parts.json object.
The newest completed manifest with an existing GLB wins, including technical FAIL runs.
Review input: reviews.json {entries:[{id,runId,imageEvidence,visual?,biological?,score?,summary?}]}.
An array or an object keyed by condition ID is also accepted. Reviews with a
runId and six image hashes apply only to that exact unchanged run. No score is derived by the server.
Only selected run artifacts are exposed; no logs, sources, paths, or listing.
"""
import argparse
import json
import math
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from benchmark_io import read_complete_manifest, review_matches_run

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
OUTPUT = ROOT / 'creation-lab' / '.local' / 'benchmarks' / BASE.name
REVIEWS = BASE / 'reviews.json'
VENDOR = ROOT / 'gallery' / 'vendor'
PORT = 4393
STATIC = {
    '/': (BASE / 'viewer.html', 'text/html; charset=utf-8'),
    '/viewer.html': (BASE / 'viewer.html', 'text/html; charset=utf-8'),
    '/viewer.css': (BASE / 'viewer.css', 'text/css; charset=utf-8'),
    '/viewer.js': (BASE / 'viewer.js', 'text/javascript; charset=utf-8'),
    '/vendor/model-viewer.min.js': (VENDOR / 'model-viewer.min.js', 'text/javascript; charset=utf-8'),
    '/vendor/inter-400.woff2': (VENDOR / 'inter-400.woff2', 'font/woff2'),
    '/vendor/inter-600.woff2': (VENDOR / 'inter-600.woff2', 'font/woff2'),
}
SAFE_RUN = re.compile(r'^[A-Za-z0-9_-]+$')


def read_json(path, fallback=None):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError, UnicodeError):
        return fallback


def safe_file(path, root):
    try:
        return path.is_file() and path.resolve().is_relative_to(root.resolve())
    except (OSError, RuntimeError):
        return False


def numeric(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def load_reviews():
    data = read_json(REVIEWS, {})
    if isinstance(data, dict) and 'entries' in data:
        data = data['entries']
    if isinstance(data, list):
        return {entry['id']: entry for entry in data if isinstance(entry, dict) and entry.get('id') in tuple('ABCDEF')}
    if isinstance(data, dict):
        return {key: value for key, value in data.items() if key in tuple('ABCDEF') and isinstance(value, dict)}
    return {}


def discover():
    """Return public metadata and exact URL-to-file allowlist together."""
    brief = read_json(BASE / 'brief.json', {})
    protocol = read_json(BASE / 'protocol.json', {})
    reviews = load_reviews()
    conditions, assets = [], {}
    for spec in protocol.get('conditions', []):
        cid = spec.get('id')
        if cid not in tuple('ABCDEF'):
            continue
        entry = {**{key: spec.get(key) for key in ('id', 'model', 'reasoningEffort')},
                 'runId': None, 'technical': 'NOT_RUN', 'seconds': None,
                 'glbBytes': None, 'metrics': {'triangles': None, 'meshes': None, 'materials': None},
                 'parts': None, 'urlGlb': None, 'urlBlend': None, 'urlPreview': None, 'review': None}
        folder = OUTPUT / cid
        try:
            runs = sorted((path for path in folder.iterdir() if path.is_dir() and SAFE_RUN.fullmatch(path.name)), key=lambda path: path.name, reverse=True)
        except OSError:
            runs = []
        for run in runs:
            if not all(safe_file(run / filename, OUTPUT) and safe_file(run / filename, run) for filename in ('manifest.json', 'asset.glb')):
                continue
            manifest = read_complete_manifest(run)
            if not isinstance(manifest, dict):
                continue
            # A directory name is the route identity; never trust manifest paths.
            rid = run.name
            checks = read_json(run / 'build-checks.json', {}) if safe_file(run / 'build-checks.json', run) else {}
            metrics = checks.get('metrics', {}) if isinstance(checks, dict) else {}
            metrics = metrics if isinstance(metrics, dict) else {}
            materials = metrics.get('materials')
            entry.update(runId=rid, technical=manifest.get('technical', 'NOT_RUN'),
                         seconds=numeric(manifest.get('seconds')), glbBytes=(run / 'asset.glb').stat().st_size,
                         metrics={'triangles': numeric(metrics.get('triangles')), 'meshes': numeric(metrics.get('meshes')),
                                  'materials': len(materials) if isinstance(materials, (list, dict)) else numeric(materials)},
                         parts=read_json(run / 'parts.json') if safe_file(run / 'parts.json', run) else None)
            for filename, key, mime in [('asset.glb', 'urlGlb', 'model/gltf-binary'), ('source.blend', 'urlBlend', 'application/octet-stream'), ('renders/three-quarter.png', 'urlPreview', 'image/png')]:
                path = run / filename
                if safe_file(path, run) and safe_file(path, OUTPUT):
                    url = f'/assets/{cid}/{rid}/{filename}'
                    assets[url] = (path, mime)
                    entry[key] = url
            review = reviews.get(cid)
            if review_matches_run(run, review, manifest):
                entry['review'] = review
            break
        conditions.append(entry)
    return {'brief': brief, 'conditions': conditions}, assets


class Handler(BaseHTTPRequestHandler):
    server_version = 'CellViewer'
    sys_version = ''

    def do_HEAD(self):
        self.respond(head=True)

    def do_GET(self):
        self.respond()

    def do_POST(self):
        self.send_error(405, 'Method not allowed')

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST
    do_OPTIONS = do_POST

    def respond(self, head=False):
        host = self.headers.get('Host', '')
        if host not in (f'127.0.0.1:{PORT}', f'localhost:{PORT}'):
            self.send_error(403, 'Forbidden')
            return
        # No route requires escaping. Reject encoded traversal before decoding,
        # backslashes, dot segments, absolute URLs and query strings outright.
        if '%' in self.path or '\\' in self.path or '..' in self.path or any(ord(c) < 32 for c in self.path):
            self.send_error(404, 'Not found')
            return
        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
            self.send_error(404, 'Not found')
            return
        path = parsed.path
        data, assets = discover()
        if path == '/api/benchmark':
            content = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(200)
            self.headers_for('application/json; charset=utf-8', len(content))
            self.end_headers()
            if not head:
                self.wfile.write(content)
            return
        route = STATIC.get(path) or assets.get(path)
        if route is None or not route[0].is_file():
            self.send_error(404, 'Not found')
            return
        file, mime = route
        try:
            size = file.stat().st_size
            with file.open('rb') as stream:
                self.send_response(200)
                self.headers_for(mime, size)
                if file.suffix == '.blend':
                    self.send_header('Content-Disposition', 'attachment; filename="source.blend"')
                self.end_headers()
                if not head:
                    while chunk := stream.read(262144):
                        self.wfile.write(chunk)
        except (OSError, BrokenPipeError, ConnectionResetError):
            return

    def headers_for(self, mime, length):
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(length))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self'; worker-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")

    def log_message(self, format, *args):
        # Never echo untrusted requested paths or local filesystem details.
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=PORT, help='Local HTTP port (default: 4393)')
    parser.add_argument('--runs', type=Path, default=OUTPUT, help='Folder containing A-F run directories')
    parser.add_argument('--reviews', type=Path, default=REVIEWS, help='Review JSON; entries apply only to their exact runId')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    PORT = args.port
    OUTPUT = args.runs.resolve()
    REVIEWS = args.reviews.resolve()
    print(f'Célula animal: http://127.0.0.1:{PORT}', flush=True)
    try:
        ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
