"""Durable, serial per-GPU queues; no training and no signal to unrelated jobs."""
from pathlib import Path
import datetime,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[3];out=ROOT/'out/multiscene_foundation_corrected';gpu=int(sys.argv[1])
scenes=['lego','drums'] if gpu==0 else ['chair','ficus']
for scene in scenes:
 for stage,seed in [('quality',1729),('quality',2718),('controlled',1729)]:
  key=f'{scene}_{seed}_{stage}';log=out/'setup'/f'{key}.log';trace=out/'setup'/f'{key}.strace'
  start=time.monotonic()
  while True:
   free=int(subprocess.check_output(['nvidia-smi',f'--id={gpu}','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip())
   if free>=6144:break
   if time.monotonic()-start>21600:raise TimeoutError('GPU unavailable')
   time.sleep(60)
  env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=str(gpu),OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1',CUDA_CACHE_DISABLE='1',CUDA_MODULE_LOADING='EAGER')
  command=['strace','-f','-qq','-yy','-s','4096','-e','trace=open,openat,openat2,creat','-o',str(trace),sys.executable,str(ROOT/'scripts/run_corrected_qualification.py'),'--scene',scene,'--seed',str(seed),'--stage',stage]
  record=dict(command=command,env={k:env[k] for k in ['CUDA_VISIBLE_DEVICES','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','PYTHONDONTWRITEBYTECODE','CUDA_CACHE_DISABLE','CUDA_MODULE_LOADING']},gpu=gpu,free_mib=free,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
  with log.open('xb') as f:r=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
  record.update(exit_code=r.returncode,elapsed_seconds=time.monotonic()-start,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
  with (out/'setup'/f'{key}_exit.json').open('x') as f:json.dump(record,f,sort_keys=True)
  print(key,r.returncode,flush=True)
  if r.returncode:raise RuntimeError(key+' failed; preserve attempt for repair')
