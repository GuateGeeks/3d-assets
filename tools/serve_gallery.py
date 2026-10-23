"""Serve the catalog and an optional, inventory-limited local rigging review."""
import argparse, hashlib, io, json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'lab/.local/review'
PUBLIC_PATHS = {'gallery.html','index.html','index.json','index.csv','selection.json','INDEX.md','ATTRIBUTIONS.md','COVERAGE.md','coverage.json','validation.json','LICENSE.md','THIRD_PARTY_NOTICES.md','credits.html','coverage.html','kits.html','kits','models','indices','gallery','sources','LICENSES'}
class GalleryHandler(SimpleHTTPRequestHandler):
    prefix = '/'
    built = False
    lab = False
    def do_GET(self):
        if urlsplit(self.path).path in {'/', self.prefix.rstrip('/')}:
            self.send_response(302)
            self.send_header('Location', self.prefix + ('index.html' if self.built else 'gallery.html') + ('?lab=1' if self.lab else ''))
            self.end_headers()
            return
        super().do_GET()
    def json_file(self, value):
        data=json.dumps(value,ensure_ascii=False).encode()
        self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers()
        return io.BytesIO(data)
    def send_head(self):
        path=unquote(urlsplit(self.path).path)
        if self.prefix != '/':
            if not path.startswith(self.prefix): self.send_error(404);return None
            path='/' + path[len(self.prefix):]
        parts=Path(path).parts
        if any(part.startswith('.') or part in {'lab','derived','packs','__pycache__'} for part in parts):
            self.send_error(404);return None
        if path.startswith('/_lab/'):
            if not self.lab or self.built: self.send_error(404);return None
            try:
                manifest=json.loads((REVIEW/'manifest.json').read_text(encoding='utf-8'))
                if path=='/_lab/manifest.json':
                    public={key:value for key,value in manifest.items() if key!='files'}
                    # URLs remain relative to the project prefix, including prefixed local previews.
                    return self.json_file(public)
                token=path.removeprefix('/_lab/assets/')
                entry=manifest['files'].get(token)
                if not entry: self.send_error(404);return None
                target=(REVIEW/'assets'/entry['file']).resolve()
                if not target.is_relative_to((REVIEW/'assets').resolve()) or target.suffix!='.glb':
                    self.send_error(404);return None
                data=target.read_bytes()
                if hashlib.sha256(data).hexdigest()!=entry['sha256']:
                    self.send_error(409,'Review asset changed; rebuild review');return None
                self.send_response(200);self.send_header('Content-Type','model/gltf-binary')
                self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers()
                return io.BytesIO(data)
            except (OSError,ValueError,KeyError):
                self.send_error(404,'Prepare the local review first');return None
        if path.startswith('/_lab'): self.send_error(404);return None
        if path.lstrip('/').split('/')[0] not in PUBLIC_PATHS:
            self.send_error(404);return None
        # Resolve symlinks before serving; no alias may expose caches or another repository.
        self.path=path + (('?' + urlsplit(self.path).query) if urlsplit(self.path).query else '')
        target=Path(self.translate_path(path)).resolve();base=Path(self.directory).resolve()
        if not target.is_relative_to(base) or any(part.startswith('.') or part in {'lab','derived','packs'} for part in target.relative_to(base).parts):
            self.send_error(404);return None
        return super().send_head()
    def list_directory(self,path):
        self.send_error(404);return None
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=4376);p.add_argument('--built',action='store_true')
    p.add_argument('--prefix',default='/');p.add_argument('--lab',action='store_true',help='Enable the local review inventory; never serve caches or weights')
    args=p.parse_args()
    if not args.prefix.startswith('/') or '..' in args.prefix: p.error('Use an absolute URL prefix without parent segments')
    if args.lab and args.built: p.error('--lab cannot be combined with --built')
    prefix=args.prefix.rstrip('/')+'/'
    directory=ROOT/'_site' if args.built else ROOT
    if not directory.is_dir(): p.error('Build the site first')
    GalleryHandler.prefix=prefix;GalleryHandler.built=args.built;GalleryHandler.lab=args.lab
    server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(GalleryHandler,directory=str(directory)))
    print(f'Gallery: http://127.0.0.1:{args.port}{prefix}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
