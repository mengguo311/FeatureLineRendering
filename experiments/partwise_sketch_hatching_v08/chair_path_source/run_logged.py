import runtime
from pathlib import Path
import argparse
import subprocess
import time

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('argv',nargs=argparse.REMAINDER)
    a=p.parse_args();argv=a.argv
    if argv and argv[0]=='--':argv=argv[1:]
    receipt=runtime.output_guard(a.receipt)
    if receipt.exists():raise FileExistsError(receipt)
    receipt.parent.mkdir(parents=True,exist_ok=True)
    log=receipt.with_suffix('.log');start=time.monotonic()
    record=dict(argv=argv,started_utc=runtime.now(),parent_pid=runtime.os.getpid(),child_returncode='UNKNOWN',timeout=False)
    runtime.js(receipt.with_suffix('.start.json'),record)
    with log.open('x') as f:
        try:
            r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,timeout=590)
            record['child_returncode']=r.returncode
        except subprocess.TimeoutExpired:
            record['timeout']=True
    record.update(finished_utc=runtime.now(),seconds=time.monotonic()-start,log=str(log))
    runtime.js(receipt,record)
    print(runtime.json.dumps(record,ensure_ascii=False),flush=True)
    raise SystemExit(record['child_returncode'] if isinstance(record['child_returncode'],int) else 124)

if __name__=='__main__':main()
