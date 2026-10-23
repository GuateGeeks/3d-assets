"""Bounded MCP integration test against owned factory-startup Blender; no global setup."""
import argparse
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
import zipfile

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / 'creation-lab'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', type=Path, required=True)
    parser.add_argument('--reuse-runtime', action='store_true', help='Reuse the previously extracted local package after checking its release manifest')
    args = parser.parse_args()
    run = LAB / 'registry' / ('mcp-probe-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    run.mkdir()
    source = LAB / 'vendor/blender-lab-mcp/source'
    runtime = LAB / 'vendor/.runtime'
    bundle = LAB / 'vendor/blender-lab-mcp/packages/blender-1.0.3.mcpb'
    # Install the exact hashed server bundle into the local disposable runtime.
    # The source audit intentionally keeps generated manuals out of Git.
    with zipfile.ZipFile(bundle) as archive:
        data = archive.read('blmcp/data/prompts.yml')
        package = runtime / 'official-blender-mcp'
        package.mkdir(exist_ok=True)
        if args.reuse_runtime:
            if (package / 'manifest.json').read_bytes() != archive.read('manifest.json'):
                raise ValueError('Prepared release manifest differs from archive')
        else:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                target = (package / member.filename).resolve()
                if not target.is_relative_to(package.resolve()):
                    raise ValueError('Archive path escapes owned runtime')
                target.parent.mkdir(parents=True, exist_ok=True)
                contents = archive.read(member)
                if not target.exists():
                    target.write_bytes(contents)
                elif target.read_bytes() != contents:
                    raise ValueError('Installed server differs from pinned release archive')
    prompt = source / 'mcp/blmcp/data/prompts.yml'
    prompt.parent.mkdir(exist_ok=True)
    if prompt.exists() and prompt.read_bytes() != data:
        raise ValueError('Existing prompt file differs from pinned bundle')
    prompt.write_bytes(data)
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1', PYTHONUTF8='1')
    for name in ['CONFIG', 'SCRIPTS', 'DATAFILES', 'EXTENSIONS']:
        directory = run / ('blender-user-' + name.lower())
        directory.mkdir()
        env['BLENDER_USER_' + name] = str(directory)
    env['BLENDER_MCP_HOST'] = '127.0.0.1'
    env['BLENDER_MCP_PORT'] = str(port)
    env['BLENDER_PATH'] = str(args.blender)
    env['PYTHONPATH'] = os.pathsep.join([str(runtime), str(source / 'mcp')])
    worker = run / 'blender_worker.py'
    worker.write_text('import sys\nsys.path.insert(0, ' + repr(str(source / 'addon')) + ')\nfrom blender_mcp_addon.cli import cli_execute\nraise SystemExit(cli_execute(["--host", "127.0.0.1", "--port", ' + repr(str(port)) + ']))\n', encoding='utf-8')
    report = {'schemaVersion': 1, 'runId': run.name, 'status': 'NOT_RUN',
              'sourceCommit': '2cea8d566dde07fbac28a61d698909d69724e853',
              'blenderExecutable': str(args.blender), 'blenderSha256': digest(args.blender),
              'hostPython': sys.executable, 'hostPythonVersion': sys.version.split()[0],
              'endpoint': {'host': '127.0.0.1', 'port': port},
              'scope': 'owned headless process, temporary preferences, stdio MCP handshake and execute_blender_code only',
              'globalConfigurationChanged': False, 'registeredInCodex': False, 'steps': []}
    report['runtimeReused'] = args.reuse_runtime
    owned = []
    handles = []
    messages = queue.Queue()
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    try:
        blender_log = (run / 'blender.log').open('w', encoding='utf-8'); handles.append(blender_log)
        blender = subprocess.Popen([str(args.blender), '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', str(worker)], stdout=blender_log, stderr=subprocess.STDOUT, env=env, creationflags=flags)
        owned.append(blender)
        report['blenderPid'] = blender.pid
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            if blender.poll() is not None:
                raise RuntimeError('Blender stopped before listener readiness')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.3):
                    break
            except OSError:
                time.sleep(0.15)
        else:
            raise TimeoutError('Blender listener did not start within 25 seconds')
        mcp_log = (run / 'mcp.stderr.log').open('w', encoding='utf-8'); handles.append(mcp_log)
        server = subprocess.Popen([sys.executable, str(LAB / 'registry/launch_official_mcp.py'), '--transport', 'stdio'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=mcp_log, text=True, encoding='utf-8', env=env, creationflags=flags)
        owned.append(server)
        report['mcpPid'] = server.pid
        def reader():
            for line in server.stdout:
                try: messages.put(json.loads(line))
                except ValueError: messages.put({'invalidLine': line[:500]})
            messages.put({'eof': True})
        threading.Thread(target=reader, daemon=True).start()
        def send(payload):
            server.stdin.write(json.dumps(payload) + '\n'); server.stdin.flush()
        def request(number, method, params):
            start = time.monotonic()
            send({'jsonrpc': '2.0', 'id': number, 'method': method, 'params': params})
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                response = messages.get(timeout=max(0.01, deadline - time.monotonic()))
                if response.get('eof') or 'invalidLine' in response:
                    raise RuntimeError('MCP stdio ended or returned invalid protocol data')
                if response.get('id') != number:
                    continue
                if 'error' in response:
                    raise RuntimeError(json.dumps(response['error']))
                report['steps'].append({'method': method, 'seconds': round(time.monotonic() - start, 3), 'status': 'PASS'})
                return response['result']
            raise TimeoutError('MCP request exceeded 25 seconds')
        initialized = request(1, 'initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'gg3d-isolated-audit', 'version': '1.0'}})
        report['handshake'] = initialized
        send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        catalog = request(2, 'tools/list', {})
        names = [tool['name'] for tool in catalog['tools']]
        report['tools'] = names
        if 'execute_blender_code' not in names:
            raise ValueError('Required official tool absent')
        def call(number, code):
            value = request(number, 'tools/call', {'name': 'execute_blender_code', 'arguments': {'code': code}})
            if value.get('isError'):
                raise ValueError('MCP tool error: ' + json.dumps(value))
            result = value.get('structuredContent')
            if result is None:
                result = next(json.loads(item['text']) for item in value['content'] if item['type'] == 'text')
            if result.get('status') != 'ok':
                raise ValueError('Nested Blender error: ' + json.dumps(result))
            return result['result']
        initial = call(3, 'import bpy, os\nresult={"pid":os.getpid(),"version":bpy.app.version_string,"background":bpy.app.background,"objects":len(bpy.data.objects)}')
        report['initial'] = initial
        if initial['pid'] != blender.pid or initial['background'] is not True:
            raise ValueError('Refusing to mutate a process not owned by this probe')
        marker = 'GG3D_Probe_' + uuid.uuid4().hex
        created = call(4, 'import bpy\nbpy.ops.mesh.primitive_cube_add(size=0.3)\nobj=bpy.context.object\nobj.name=' + repr(marker) + '\nbpy.context.view_layer.update()\nresult={"name":obj.name,"dimensions":list(obj.dimensions),"objects":len(bpy.data.objects)}')
        report['created'] = created
        checked = call(5, 'import bpy\nobj=bpy.data.objects[' + repr(marker) + ']\nresult={"name":obj.name,"dimensions":list(obj.dimensions),"vertices":len(obj.data.vertices)}')
        report['verified'] = checked
        if checked['name'] != marker or checked['vertices'] != 8 or any(abs(v - 0.3) > 1e-5 for v in checked['dimensions']):
            raise ValueError('Controlled mutation verification failed')
        render_path = run / 'mcp-render.png'
        render_code = ('import bpy\nfrom mathutils import Vector\n'
                       'scene=bpy.context.scene\nscene.render.engine="CYCLES"\nscene.cycles.device="CPU"\nscene.cycles.samples=8\n'
                       'scene.render.resolution_x=192\nscene.render.resolution_y=192\nscene.render.resolution_percentage=100\n'
                       'scene.render.image_settings.file_format="PNG"\n'
                       'scene.camera.location=(0.65,-0.85,0.55)\nscene.camera.rotation_euler=(-scene.camera.location).to_track_quat("-Z","Y").to_euler()\n'
                       'scene.camera.data.type="ORTHO"\nscene.camera.data.ortho_scale=0.6\n'
                       'obj=bpy.data.objects[' + repr(marker) + ']\n'
                       'mat=bpy.data.materials.new("GG3D_Probe_Material")\nmat.diffuse_color=(0.02,0.4,0.65,1.0)\nobj.data.materials.append(mat)\n'
                       'bpy.data.objects["Cube"].hide_render=True\n'
                       'scene.render.filepath=' + repr(str(render_path)) + '\nbpy.ops.render.render(write_still=True)\n'
                       'result={"width":scene.render.resolution_x,"height":scene.render.resolution_y,"engine":scene.render.engine,"device":scene.cycles.device}')
        report['render'] = call(6, render_code)
        if not render_path.is_file() or render_path.read_bytes()[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError('MCP render output missing or not PNG')
        report['viewportScreenshot'] = {'status': 'NOT_RUN', 'reason': 'headless CPU render; no editor window capture'}
        restored = call(7, 'import bpy\nobj=bpy.data.objects[' + repr(marker) + ']\nmesh=obj.data\nbpy.data.objects.remove(obj,do_unlink=True)\nbpy.data.meshes.remove(mesh)\nresult={"objects":len(bpy.data.objects)}')
        report['restored'] = restored
        if restored['objects'] != initial['objects']:
            raise ValueError('Probe object removal did not restore object count')
        report['status'] = 'PASS'
    except Exception as exc:
        report.update(status='FAIL', error=str(exc), errorType=type(exc).__name__)
    finally:
        for process in reversed(owned):
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        report['ownedProcessesStopped'] = all(p.poll() is not None for p in owned)
        for handle in handles: handle.close()
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                report['listenerClosed'] = False
        except OSError:
            report['listenerClosed'] = True
        report['finishedAt'] = datetime.now(timezone.utc).isoformat()
        report['evidence'] = [{'file': p.name, 'sha256': digest(p), 'bytes': p.stat().st_size} for p in run.iterdir() if p.is_file()]
        (run / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'report': str(run / 'report.json'), 'error': report.get('error')}))
    return 0 if report['status'] == 'PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
