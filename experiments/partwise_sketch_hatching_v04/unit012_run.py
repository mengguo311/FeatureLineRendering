"""Bounded, serial unit012 command receipts; no legacy producers invoked."""
import runtime
from runtime import OUTPUT_ROOT, js, now
import argparse, subprocess, time

def main():
    p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    folder=OUTPUT_ROOT/'units/unit_012/logs';folder.mkdir(exist_ok=True)
    receipt=folder/(a.name+'.receipt.json')
    if receipt.exists():raise FileExistsError(receipt)
    t=time.monotonic();start=now()
    with (folder/(a.name+'.log')).open('w') as log:
        try:
            result=subprocess.run(a.command,stdout=log,stderr=subprocess.STDOUT,timeout=570)
            rc=result.returncode
        except subprocess.TimeoutExpired:
            rc=124
    js(receipt,dict(command=a.command,started_utc=start,ended_utc=now(),seconds=time.monotonic()-t,returncode=rc,timeout_seconds=570))
    print(receipt.read_text(),flush=True)
    raise SystemExit(rc)

if __name__=='__main__':main()
