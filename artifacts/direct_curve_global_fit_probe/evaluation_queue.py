"""Administrative scheduler: evaluation is dependent on immutable fit seals."""
import os,time,subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
root=Path.cwd();py='/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python';out=root/'out/direct_curve_global_fit_probe'
def worker(pair):
    run,scene=pair;seal=out/run/scene/'fit/SEAL.json.sha256'
    while not seal.exists():time.sleep(30)
    env=dict(os.environ,PYTHONPATH='.:tests',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='0' if scene in ['lego','drums'] else '1',CUBLAS_WORKSPACE_CONFIG=':4096:8',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    trace=out/'setup'/f'{scene}_{"eval" if run=="run" else "rerun_eval"}.strace'
    cmd=[py,'artifacts/direct_curve_global_fit_probe/record.py',f'EVALUATE_{run}_{scene}','strace','-f','-yy','-e','trace=open,openat,openat2,creat','-o',str(trace),py,'scripts/run_direct_curve_probe.py','--scene',scene,'--stage','evaluate','--run',run]
    with (out/'setup'/f'queue_{run}_{scene}.log').open('wb') as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
    print(run,scene,'evaluation exit',r.returncode,flush=True);return r.returncode
with ThreadPoolExecutor(max_workers=8) as pool:codes=list(pool.map(worker,[(r,s) for r in ['run','rerun'] for s in ['lego','chair','drums','ficus']]))
raise SystemExit(any(codes))
