"""One-command build and actual-GPU reproduction; no install or old-root writes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from runtime import ART, EXP, OUT, PYTHON, ROOT, atomic_json, guard, sha

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--benchmark',action='store_true',help='also repeat synthetic and four real-view benchmarks')
    args=parser.parse_args()
    guard('reproduce',gpu=False)
    stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'_'+str(time.time_ns())
    logdir=OUT/'reproductions'/stamp;logdir.mkdir(parents=True)
    steps=['build.py','tests/test_api_vertical.py','tests/test_native.py','verify_real.py']
    if args.benchmark:steps+=['run_synthetic_benchmark.py','rebenchmark_real.py']
    receipt=dict(python=PYTHON,started_utc=stamp,steps=[],success=False)
    for step in steps:
        guard('reproduce_'+step.replace('/','_'),gpu=False)
        logpath=logdir/(step.replace('/','_')+'.log')
        print('RUN',step,flush=True)
        with logpath.open('w') as log:
            result=subprocess.run([PYTHON,'-B',str(EXP/step)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        print(logpath.read_text()[-6000:],flush=True)
        receipt['steps'].append(dict(step=step,returncode=result.returncode,log=str(logpath.relative_to(ROOT)),sha256=sha(logpath)))
        atomic_json(logdir/'RECEIPT.json',receipt)
        if result.returncode:
            raise SystemExit(result.returncode)
    receipt['success']=True
    atomic_json(logdir/'RECEIPT.json',receipt)
    atomic_json(ART/'results/REPRODUCTION.json',receipt)
    print('REPRODUCTION PASS',str(logdir),flush=True)

if __name__=='__main__':main()
