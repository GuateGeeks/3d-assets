"""Serve official MCP through a fresh owned Blender; stdout is MCP protocol only."""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import uuid

LAB = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', type=Path, required=True)
    args = parser.parse_args()
    runtime = LAB / 'vendor/.runtime'
    if not (runtime / 'official-blender-mcp/blmcp/data/prompts.yml').is_file():
        parser.error('Prepared runtime absent; restore locked wheels and run probe_official_mcp.py first')
    run = runtime / 'sessions' / uuid.uuid4().hex
    run.mkdir(parents=True)
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1', PYTHONUTF8='1')
    for name in ['CONFIG', 'SCRIPTS', 'DATAFILES', 'EXTENSIONS']:
        path = run / name.lower(); path.mkdir()
        env['BLENDER_USER_' + name] = str(path)
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0)); port = reservation.getsockname()[1]
    env.update(BLENDER_MCP_HOST='127.0.0.1', BLENDER_MCP_PORT=str(port))
    source = LAB / 'vendor/blender-lab-mcp/source/addon'
    worker = run / 'worker.py'
    worker.write_text('import sys\nsys.path.insert(0,' + repr(str(source)) + ')\nfrom blender_mcp_addon.cli import cli_execute\nraise SystemExit(cli_execute(["--host","127.0.0.1","--port",' + repr(str(port)) + ']))\n', encoding='utf-8')
    owned = []
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    def stop():
        for child in reversed(owned):
            if child.poll() is None:
                child.terminate()
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=5)
    def interrupted(signum, frame):
        stop(); raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    receipt = {'version': '1.0.3', 'host': '127.0.0.1', 'port': port, 'blender': str(args.blender), 'globalConfigChanged': False}
    try:
        with (run / 'blender.log').open('w', encoding='utf-8') as log:
            blender = subprocess.Popen([str(args.blender), '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', str(worker)], stdout=log, stderr=subprocess.STDOUT, env=env, creationflags=flags)
            owned.append(blender); receipt['blenderPid'] = blender.pid
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if blender.poll() is not None: raise RuntimeError('Owned Blender stopped during startup')
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=0.3): break
                except OSError: time.sleep(0.15)
            else: raise TimeoutError('Owned Blender listener did not start')
            host = subprocess.Popen([sys.executable, str(LAB / 'registry/launch_official_mcp.py'), '--transport', 'stdio'], stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, env=env, creationflags=flags)
            owned.append(host); receipt['mcpPid'] = host.pid
            (run / 'session.json').write_text(json.dumps(receipt, indent=2) + '\n')
            return host.wait()
    finally:
        stop()
        receipt['ownedProcessesStopped'] = all(child.poll() is not None for child in owned)
        (run / 'session.json').write_text(json.dumps(receipt, indent=2) + '\n')

if __name__ == '__main__': raise SystemExit(main())
