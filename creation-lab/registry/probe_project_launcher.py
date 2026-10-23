"""Test the exact project launcher over MCP stdio, then close its owned session."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import threading
import time
import uuid

LAB = Path(__file__).resolve().parents[1]

def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', required=True)
    args = parser.parse_args()
    run = LAB / 'registry' / ('launcher-probe-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    run.mkdir()
    sessions = LAB / 'vendor/.runtime/sessions'
    previous = set(sessions.glob('*')) if sessions.exists() else set()
    responses = queue.Queue()
    report = {'status': 'NOT_RUN', 'scope': 'exact project launcher, MCP initialize/list_tools/query/create/verify/render/remove and cleanup', 'globalConfigurationChanged': False}
    with (run / 'stderr.log').open('w', encoding='utf-8') as errors:
        process = subprocess.Popen([sys.executable, str(LAB / 'registry/launch_isolated_mcp.py'), '--blender', args.blender], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        def reader():
            for line in process.stdout:
                responses.put(json.loads(line))
            responses.put({'eof': True})
        threading.Thread(target=reader, daemon=True).start()
        def send(value): process.stdin.write(json.dumps(value) + '\n'); process.stdin.flush()
        def request(i, method, params):
            send({'jsonrpc': '2.0', 'id': i, 'method': method, 'params': params})
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                value = responses.get(timeout=max(0.01, deadline - time.monotonic()))
                if value.get('eof'): raise ValueError('Launcher ended before response')
                if value.get('id') == i:
                    if 'error' in value: raise ValueError(str(value['error']))
                    return value['result']
            raise TimeoutError('MCP request deadline exceeded')
        try:
            report['initialize'] = request(1, 'initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'gg3d-project-launcher-test', 'version': '1'}})
            send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
            tools = request(2, 'tools/list', {})
            report['tools'] = [item['name'] for item in tools['tools']]
            def call(i, code):
                result = request(i, 'tools/call', {'name': 'execute_blender_code', 'arguments': {'code': code}})
                nested = result.get('structuredContent') or next(json.loads(item['text']) for item in result['content'] if item['type'] == 'text')
                if result.get('isError') or nested.get('status') != 'ok': raise ValueError('Blender tool call failed')
                return nested['result']
            report['query'] = call(3, 'import bpy,os\nresult={"pid":os.getpid(),"version":bpy.app.version_string,"background":bpy.app.background,"objects":len(bpy.data.objects)}')
            created = set(sessions.glob('*')) - previous
            if len(created) != 1: raise ValueError('Expected one owned session')
            session = created.pop() / 'session.json'
            receipt = json.loads(session.read_text())
            if receipt['blenderPid'] != report['query']['pid'] or report['query']['background'] is not True: raise ValueError('Unexpected Blender PID or mode')
            report['session'] = receipt
            marker = 'GG3D_Launcher_Probe_' + uuid.uuid4().hex
            report['created'] = call(4, 'import bpy\nbpy.ops.mesh.primitive_cube_add(size=0.3)\nobj=bpy.context.object\nobj.name=' + repr(marker) + '\nbpy.context.view_layer.update()\nresult={"name":obj.name,"dimensions":list(obj.dimensions)}')
            report['verified'] = call(5, 'import bpy\nobj=bpy.data.objects[' + repr(marker) + ']\nresult={"name":obj.name,"dimensions":list(obj.dimensions),"vertices":len(obj.data.vertices)}')
            checked = report['verified']
            if checked['name'] != marker or checked['vertices'] != 8 or any(abs(v - 0.3) > 1e-5 for v in checked['dimensions']): raise ValueError('Controlled mutation verification failed')
            render_path = run / 'mcp-render.png'
            report['render'] = call(6, 'import bpy\nscene=bpy.context.scene\nscene.render.engine="CYCLES"\nscene.cycles.device="CPU"\nscene.cycles.samples=8\nscene.render.resolution_x=192\nscene.render.resolution_y=192\nscene.render.resolution_percentage=100\nscene.render.image_settings.file_format="PNG"\nscene.camera.location=(0.65,-0.85,0.55)\nscene.camera.rotation_euler=(-scene.camera.location).to_track_quat("-Z","Y").to_euler()\nscene.camera.data.type="ORTHO"\nscene.camera.data.ortho_scale=0.6\nbpy.data.objects["Cube"].hide_render=True\nscene.render.filepath=' + repr(str(render_path)) + '\nbpy.ops.render.render(write_still=True)\nresult={"width":scene.render.resolution_x,"height":scene.render.resolution_y,"engine":scene.render.engine,"device":scene.cycles.device}')
            png = render_path.read_bytes()
            if png[:8] != b'\x89PNG\r\n\x1a\n': raise ValueError('Render is not PNG')
            report['render'].update(file=render_path.name, sha256=hashlib.sha256(png).hexdigest(), bytes=len(png))
            report['viewportScreenshot'] = {'status': 'NOT_RUN', 'reason': 'headless CPU render; no editor window capture'}
            report['restored'] = call(7, 'import bpy\nobj=bpy.data.objects[' + repr(marker) + ']\nmesh=obj.data\nbpy.data.objects.remove(obj,do_unlink=True)\nbpy.data.meshes.remove(mesh)\nresult={"objects":len(bpy.data.objects)}')
            if report['restored']['objects'] != report['query']['objects']: raise ValueError('Probe object removal did not restore object count')
            process.stdin.close()
            report['exitCode'] = process.wait(timeout=15)
            report['cleanup'] = json.loads(session.read_text())
            if report['exitCode'] != 0 or not report['cleanup']['ownedProcessesStopped']: raise ValueError('Launcher cleanup failed')
            try:
                with socket.create_connection(('127.0.0.1', receipt['port']), timeout=0.2): raise ValueError('Owned listener remains open')
            except OSError: report['listenerClosed'] = True
            report['status'] = 'PASS'
        except Exception as exc:
            report.update(status='FAIL', error=str(exc))
        finally:
            if process.poll() is None:
                if not process.stdin.closed: process.stdin.close()
                try: process.wait(timeout=15)
                except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=5)
    report['finishedAt'] = datetime.now(timezone.utc).isoformat()
    (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'report': str(run / 'report.json'), 'error': report.get('error')}))
    return 0 if report['status'] == 'PASS' else 1

if __name__ == '__main__': raise SystemExit(main())
