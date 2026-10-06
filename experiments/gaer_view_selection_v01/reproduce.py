"""Run this stage's tests and genuine native verification, never the old reproduce.py."""
import argparse,json,subprocess,sys,time
from stage_runtime import ROOT,ART,EXP,OUT,PY,atomic_json,sha,guard

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--generate',action='store_true');args=ap.parse_args()
    guard('reproduce');run=OUT/'reproductions'/str(time.time_ns());run.mkdir(parents=True)
    steps=[]
    cmds=[[PY,'-B',str(EXP/'tests'/f)] for f in ('test_sparse.py','test_native_stage.py','test_causal.py')]
    if args.generate:cmds.append([PY,'-B',str(EXP/'run.py')])
    cmds.append([PY,'-B',str(EXP/'verify.py')])
    for i,cmd in enumerate(cmds):
        log=run/(str(i)+'.log');t=time.perf_counter()
        with log.open('w') as f:rc=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
        steps.append(dict(command=cmd,returncode=rc,seconds=time.perf_counter()-t,log=str(log),log_sha256=sha(log)))
        print('STEP',i,'rc',rc,flush=True)
        if rc:break
    result=dict(passed=len(steps)==len(cmds) and all(s['returncode']==0 for s in steps),steps=steps,
        scope='only new-stage writes; existing old native API/binaries read only; no rebuild')
    atomic_json(run/'RECEIPT.json',result);atomic_json(ART/'results/REPRODUCTION.json',result)
    raise SystemExit(0 if result['passed'] else 1)

if __name__=='__main__':main()
