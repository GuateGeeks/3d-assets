"""Small stdlib remote supervisor, staged with every SSH job (no installation)."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import time


def identity(pid):
    """Linux process identity survives parent exit and guards against PID reuse."""
    try:
        fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        return fields[19],fields[0]
    except (FileNotFoundError,ProcessLookupError): return None


def owned_processes(pid):
    pending=[pid]; owned={}
    while pending:
        current=pending.pop()
        if current in owned: continue
        current_identity=identity(current)
        if current_identity is None: continue
        owned[current]=current_identity[0]
        try:
            pending.extend(int(value) for value in Path(f'/proc/{current}/task/{current}/children').read_text().split())
        except (FileNotFoundError,ProcessLookupError): pass
    return owned


def live_owned(owned):
    result=[]
    for pid,started in owned.items():
        current=identity(pid)
        if current is not None and current[0]==started and current[1]!='Z': result.append(pid)
    return result


def wait_owned(owned,timeout=5):
    deadline=time.monotonic()+timeout
    while live:=live_owned(owned):
        remaining=deadline-time.monotonic()
        if remaining<=0: raise RuntimeError('Cleanup failed: owned processes still live: '+','.join(map(str,live)))
        time.sleep(min(.01,remaining))


def signal_owned(owned,signum):
    for pid in live_owned(owned):
        try: os.kill(pid,signum)
        except ProcessLookupError: pass


def terminate_owned(proc):
    owned=owned_processes(proc.pid)
    signal_owned(owned,signal.SIGTERM)
    try: proc.wait(timeout=5)
    except subprocess.TimeoutExpired: pass
    signal_owned(owned,signal.SIGKILL)
    try: proc.wait(timeout=5)
    except subprocess.TimeoutExpired as error: raise RuntimeError('Cleanup failed: direct child did not exit') from error
    wait_owned(owned)


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
        terminate_owned(proc)
        return 124

if __name__=='__main__': raise SystemExit(main())
