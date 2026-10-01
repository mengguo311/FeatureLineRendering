#!/usr/bin/env python3
"""Single-launch bounded training supervisor; writes durable failure evidence."""
import json,os,subprocess,sys,time,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; A=ROOT/'artifacts/independent_rgbd_asset_probe'; O=ROOT/'out/independent_rgbd_asset_probe'
if (A/'TRAINING_LAUNCH.json').exists() or (A/'TRAINING_EXIT.json').exists(): raise RuntimeError('single launch already consumed')
env=dict(os.environ,CUDA_VISIBLE_DEVICES='0',OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1')
cmd=[sys.executable,str(ROOT/'scripts/independent_rgbd_probe.py'),'train']; start=time.time(); reason='completed'
with (A/'TRAIN.log').open('x') as log:
 p=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
 while p.poll() is None:
  size=sum(f.stat().st_size for base in [A,O] for f in base.rglob('*') if f.is_file()); free=shutil.disk_usage(O).free
  with (A/'TRAIN_RESOURCES.jsonl').open('a') as f: f.write(json.dumps(dict(elapsed=time.time()-start,new_bytes=size,free_bytes=free))+'\n')
  if size>=8*2**30 or free<12*2**30 or time.time()-start>2700:
   reason='resource/time STOP'; p.terminate()
   try:p.wait(timeout=15)
   except subprocess.TimeoutExpired:p.kill();p.wait()
   break
  time.sleep(10)
result=dict(command=cmd,exit_code=p.returncode,seconds=time.time()-start,reason=reason,model_sealed=(A/'MODEL_SEAL.json').exists(),status='TRAINED' if p.returncode==0 and (A/'MODEL_SEAL.json').exists() else 'ENGINEERING_BLOCKED')
(A/'TRAINING_EXIT.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result),flush=True)
