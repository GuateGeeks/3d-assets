"""Loopback-only preview of an explicit, hash-bound static inventory."""
from __future__ import annotations
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from studio import core


def make_server(dist: Path, project: Path | None = None, port: int = 0):
    dist=Path(dist).resolve()
    if not (dist/'index.html').is_file():
        raise ValueError('preview is not built; run npm ci and npm run build in studio/web')
    inventory={}
    for entry in dist.rglob('*'):
        if entry.is_symlink(): raise ValueError('preview build contains a symlink')
        if entry.is_file():
            relative=entry.relative_to(dist).as_posix()
            core.checked_path(dist,relative)
            inventory['/'+relative]=(dist,relative,core.sha256(entry))
    scene_url=None
    if project is not None:
        project=Path(project).resolve()
        manifest=core.validate_record(core.read_json(project/'project.json'))
        if manifest['kind']!='project': raise ValueError('project manifest required')
        core.verify_inventory(project,manifest['files'])
        core.validate_record(core.read_json(core.checked_path(project,manifest['scene'])))
        for item in manifest['files']:
            if any(part.startswith('.') or part=='node_modules' for part in item['path'].split('/')):
                raise ValueError('private path in preview inventory')
            inventory['/project/'+item['path']]=(project,item['path'],item['sha256'])
        scene_url='project/'+manifest['scene']

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_HEAD(self): self._respond(False)
        def do_GET(self): self._respond(True)
        def _respond(self,body):
            allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
            if self.headers.get('Host','') not in allowed:
                self.send_error(403,'Loopback host required'); return
            path=unquote(urlsplit(self.path).path)
            if path=='/': path='/index.html'
            if path not in inventory:
                self.send_error(404); return
            root,relative,expected=inventory[path]
            try:
                file=core.checked_path(root,relative)
                data=file.read_bytes()
                import hashlib
                if hashlib.sha256(data).hexdigest()!=expected: raise ValueError('changed artifact')
            except (ValueError,OSError):
                self.send_error(409,'Artifact changed; rebuild or refresh inventory'); return
            mime=mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
            self.send_response(200)
            self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Cross-Origin-Resource-Policy','same-origin')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; worker-src 'self' blob:; frame-ancestors 'none'")
            self.end_headers()
            if body: self.wfile.write(data)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.daemon_threads=True
    server.scene_url=scene_url
    return server
