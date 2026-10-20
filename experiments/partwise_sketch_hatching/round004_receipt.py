"""Bounded serial execution; retain exact exit status and runtime log hash."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='2'
os.sched_setaffinity(0,[0,1])
import hashlib,json,subprocess,sys,time
from pathlib import Path
R=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_004')
name,*args=sys.argv[1:]
receipt=R/(name+'.json');log=R/'runtime'/(name.lower()+'.log')
assert not receipt.exists() and not log.exists()
cmd=['taskset','-c','0,1','timeout','600',sys.executable]+args
t=time.monotonic()
with log.open('w') as f: result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
obj={'argv':cmd,'returncode':result.returncode,'wall_seconds':time.monotonic()-t,
     'log':str(log),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),
     'cpu_affinity':[0,1],'threads_max':2,'GPU':False}
receipt.write_text(json.dumps(obj,indent=2)+'\n')
print(json.dumps(obj),flush=True)
sys.exit(result.returncode)
