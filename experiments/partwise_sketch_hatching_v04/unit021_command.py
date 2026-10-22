"""Bounded serial command receipt writer, including expected TDD failures."""
import runtime
from runtime import js,now
from pathlib import Path
import argparse,subprocess,time
from unit021_run import U
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--expect',type=int,default=0);p.add_argument('args',nargs=argparse.REMAINDER);a=p.parse_args()
args=a.args
if args and args[0]=='--':args=args[1:]
out=U/'logs'/f'{a.name}.receipt.json'
assert not out.exists()
start=time.monotonic();began=now()
with (U/'logs'/f'{a.name}.log').open('w') as f:
    r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=540)
js(out,dict(command=args,cwd=str(Path.cwd()),start_utc=began,end_utc=now(),seconds=time.monotonic()-start,returncode=r.returncode,expected_returncode=a.expect))
print(out.read_text())
raise SystemExit(0 if r.returncode==a.expect else r.returncode or 1)
