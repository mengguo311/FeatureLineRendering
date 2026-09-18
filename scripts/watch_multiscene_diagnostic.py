#!/usr/bin/env python3
"""Durable nonconfirmatory diagnostic queue, after GPU1 training completes."""
import fcntl,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import verified_json,freeze_json
from src.multiscene_training import free_memory,utc
root=ROOT/'out/multiscene_foundation';cfg=verified_json(root/'config.json',(root/'config.json.sha256').read_text().strip())
logs=root/'setup/diagnostic';logs.mkdir(exist_ok=False)
while not (root/'setup/worker_gpu1_exit.json').exists():time.sleep(60)
with (root/'setup/gpu1.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 statuses=[]
 for scene in cfg['scene_order']:
  for seed in cfg['training']['seeds']:
   done=root/'training'/scene/f'seed_{seed}'/'completion.json'
   while not done.exists():time.sleep(60)
   if not json.loads(done.read_text())['complete']:raise RuntimeError('no complete registered posterior')
   deadline=time.monotonic()+21600
   while free_memory(1)<6144:
    if time.monotonic()>deadline:raise TimeoutError('diagnostic GPU wait exhausted')
    time.sleep(60)
   cmd=['strace','-f','-qq','-yy','-s','4096','-e','trace=open,openat,openat2,creat','-o',str(logs/f'{scene}_{seed}.strace'),
    sys.executable,str(ROOT/'scripts/run_multiscene_resolution_diagnostic.py'),'--scene',scene,'--seed',str(seed)]
   row=dict(scene=scene,seed=seed,command=cmd,started_utc=utc())
   env=dict(os.environ,CUDA_VISIBLE_DEVICES='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',
    PYTHONDONTWRITEBYTECODE='1',CUDA_CACHE_DISABLE='1',CUDA_MODULE_LOADING='EAGER')
   print(json.dumps(row),flush=True)
   with (logs/f'{scene}_{seed}.log').open('x') as log:
    try:code=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=7200).returncode
    except subprocess.TimeoutExpired:code=124
   row.update(exit_code=code,finished_utc=utc());statuses.append(row)
   freeze_json(logs/f'{scene}_{seed}_exit.json',row)
 freeze_json(logs/'exit_status.json',dict(stages=statuses,finished_utc=utc()))
