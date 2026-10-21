"""Serial command receipt writer. No numerical children survive this runner."""
import runtime
from runtime import js,now,output_guard
import argparse
import subprocess
import time
import os
import signal
from pathlib import Path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True,type=Path);p.add_argument('--name',required=True)
    p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    output_guard(a.unit);command=a.command
    if command and command[0]=='--':command=command[1:]
    folder=a.unit/'logs';folder.mkdir(exist_ok=True)
    receipt=folder/(a.name+'.receipt.json')
    if receipt.exists():raise FileExistsError(receipt)
    start=now();t=time.monotonic()
    interrupted=[]
    with open(folder/(a.name+'.log'),'w') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        js(folder/(a.name+'.start.json'),dict(command=command,start_utc=start,pid=process.pid,
                                           own_process_group=process.pid))
        def stop(signum, frame):
            interrupted.append(signum)
            if process.poll() is None:
                try:os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError:pass
        signal.signal(signal.SIGTERM,stop)
        signal.signal(signal.SIGINT,stop)
        while True:
            try:
                returncode=process.wait(timeout=5)
                break
            except subprocess.TimeoutExpired:
                elapsed=time.monotonic()-t
                print(f'{a.name}: running {elapsed:.0f}s; child PID {process.pid}',flush=True)
                if elapsed>580 or interrupted:
                    os.killpg(process.pid,signal.SIGKILL)
                    returncode=process.wait(timeout=10)
                    break
    js(receipt,dict(command=command,cwd=str(Path.cwd()),start_utc=start,end_utc=now(),seconds=time.monotonic()-t,
                    returncode=returncode,interrupt_signals=interrupted,log=str(folder/(a.name+'.log'))))
    print(receipt.read_text(),flush=True)
    raise SystemExit(returncode if not interrupted else 128+interrupted[0])
