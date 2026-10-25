"""Bounded serial commands with durable raw stdout/stderr and exit receipts."""
import os, sys, json, time, subprocess, signal
from pathlib import Path
ROOT = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07')
UNIT = ROOT/'units/unit_008'
def main():
    label, limit, *cmd = sys.argv[1:]
    assert '/' not in label and cmd
    logs=UNIT/'logs'; logs.mkdir(parents=True,exist_ok=True)
    receipt=logs/(label+'.json')
    if receipt.exists(): raise FileExistsError(receipt)
    os.environ['CUDA_VISIBLE_DEVICES']=''
    for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[k]='1'
    os.environ['PYTHONDONTWRITEBYTECODE']='1'
    os.environ['TMPDIR']=str(UNIT/'scratch')
    os.environ['XDG_CACHE_HOME']=str(ROOT/'cache')
    (UNIT/'scratch').mkdir(exist_ok=True); (ROOT/'cache').mkdir(exist_ok=True)
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
    start=time.time(); timed_out=False
    with open(logs/(label+'.stdout'),'x') as out,open(logs/(label+'.stderr'),'x') as err:
        p=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True)
        try: rc=p.wait(timeout=float(limit))
        except subprocess.TimeoutExpired:
            timed_out=True; os.killpg(p.pid,signal.SIGTERM)
            try: rc=p.wait(timeout=5)
            except subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL); rc=p.wait()
    result=dict(argv=cmd,child_returncode=rc,timed_out=timed_out,elapsed_seconds=time.time()-start,
                started_unix=start,cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,GPU=False)
    receipt.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result),flush=True)
    sys.exit(rc if rc>=0 else 128-rc)
if __name__=='__main__': main()
