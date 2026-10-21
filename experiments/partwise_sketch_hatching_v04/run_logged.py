"""Serial command receipt writer. No numerical children survive this runner."""
import runtime
from runtime import js,now,output_guard
import argparse
import subprocess
import time
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
    with open(folder/(a.name+'.log'),'w') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=590)
    js(receipt,dict(command=command,cwd=str(Path.cwd()),start_utc=start,end_utc=now(),seconds=time.monotonic()-t,
                    returncode=result.returncode,log=str(folder/(a.name+'.log'))))
    print(receipt.read_text(),flush=True)
    raise SystemExit(result.returncode)
