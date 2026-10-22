"""Serve the gallery or generated site on localhost, optionally under a project prefix."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class GalleryHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/' or self.path==self.prefix.rstrip('/'):
            self.send_response(302)
            self.send_header('Location',self.prefix+'index.html' if self.built else self.prefix+'gallery.html')
            self.end_headers()
            return
        if self.prefix!='/':
            if not self.path.startswith(self.prefix):
                self.send_error(404)
                return
            self.path='/'+self.path[len(self.prefix):]
        super().do_GET()
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=4376)
    p.add_argument('--built',action='store_true')
    p.add_argument('--prefix',default='/')
    args=p.parse_args()
    if not args.prefix.startswith('/') or '..' in args.prefix: p.error('Use an absolute URL prefix without parent segments')
    prefix=args.prefix.rstrip('/')+'/'
    directory=ROOT/'_site' if args.built else ROOT
    if not directory.is_dir(): p.error('Build the site first')
    GalleryHandler.prefix=prefix
    GalleryHandler.built=args.built
    server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(GalleryHandler,directory=str(directory)))
    print(f'Gallery: http://127.0.0.1:{args.port}{prefix}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
