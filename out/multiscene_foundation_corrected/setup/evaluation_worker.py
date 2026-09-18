"""Finish evaluation and diagnostics after every eligible scene's immutable fits."""
from pathlib import Path
import datetime,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[3];out=ROOT/'out/multiscene_foundation_corrected';queue=int(sys.argv[1])
scenes=['lego','drums'] if queue==0 else ['chair','ficus']
for scene in scenes:
 start=time.monotonic();eligible=out/f'scenes/{scene}/eligibility.json'
 while not eligible.exists():
  if time.monotonic()-start>36000:raise TimeoutError('eligibility waiting exceeded')
  time.sleep(10)
 e=json.loads(eligible.read_text())
 if not e['eligible']:continue
 while not (out/f'local/{scene}/execution_complete.json').exists():
  if time.monotonic()-start>36000:raise TimeoutError('local execution waiting exceeded')
  time.sleep(10)
 for task in ['machine','surface','visual']:
  if task=='visual':
   while int(subprocess.check_output(['nvidia-smi',f'--id={queue}','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip())<6144:time.sleep(30)
  key=f'evaluation_{scene}_{task}';trace=out/'setup'/f'{key}.strace';log=out/'setup'/f'{key}.log'
  script='render_corrected_diagnostics.py' if task=='visual' else 'evaluate_corrected_scene.py'
  command=['strace','-f','-qq','-yy','-s','4096','-e','trace=open,openat,openat2,creat','-o',str(trace),sys.executable,str(ROOT/'scripts'/script),'--scene',scene]
  if task!='visual':command+=['--task',task]
  env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=str(queue),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_WAIT_POLICY='PASSIVE',PYTHONDONTWRITEBYTECODE='1',CUDA_CACHE_DISABLE='1',CUDA_MODULE_LOADING='EAGER')
  record=dict(command=command,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());tick=time.monotonic()
  with log.open('xb') as f:r=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
  record.update(exit_code=r.returncode,elapsed_seconds=time.monotonic()-tick,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
  with (out/'setup'/f'{key}_exit.json').open('x') as f:json.dump(record,f,sort_keys=True)
  print(key,r.returncode,flush=True)
  if r.returncode:raise RuntimeError('diagnostic stage failed; retain attempt '+key)
