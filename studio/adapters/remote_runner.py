"""Small stdlib remote supervisor, staged with every SSH job (no installation)."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys


def groups(pid):
    pending=[pid]; result=set()
    while pending:
        current=pending.pop()
        try:
            for value in Path(f'/proc/{current}/task/{current}/children').read_text().split():
                child=int(value); pending.append(child); group=os.getpgid(child)
                if group!=pid: result.add(group)
        except OSError: pass
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--timeout',type=int,required=True); parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args(); command=args.command[1:] if args.command[:1]==['--'] else args.command
    if not 1<=args.timeout<=7200 or not command: raise ValueError('Bounded command required')
    proc=subprocess.Popen(command,start_new_session=True)
    def interrupt(signum,frame): raise InterruptedError('Supervisor interrupted')
    signal.signal(signal.SIGTERM,interrupt); signal.signal(signal.SIGHUP,interrupt)
    try: return proc.wait(timeout=args.timeout)
    except (subprocess.TimeoutExpired,InterruptedError,KeyboardInterrupt):
        owned=groups(proc.pid)|{proc.pid}
        for group in owned:
            try: os.killpg(group,signal.SIGTERM)
            except ProcessLookupError: pass
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: pass
        for group in owned:
            try: os.killpg(group,signal.SIGKILL)
            except ProcessLookupError: pass
        proc.wait(); return 124

if __name__=='__main__': raise SystemExit(main())
