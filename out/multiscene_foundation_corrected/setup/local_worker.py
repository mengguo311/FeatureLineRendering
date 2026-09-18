"""Complete every eligible scene's registered local arms, independent of peers."""
from pathlib import Path
import datetime,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from src.corrected_execution import prepare_eligibility
out=ROOT/'out/multiscene_foundation_corrected';queue=int(sys.argv[1]);cfg=json.loads((out/'config.json').read_text())
scenes=['lego','drums'] if queue==0 else ['chair','ficus']
cpus=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,cpus[16+queue*8:24+queue*8])
for scene in scenes:
 waiting=time.monotonic()
 required=[out/f'quality/{scene}/seed_{seed}/stage_complete.json' for seed in [1729,2718]]+[out/f'controlled/{scene}/stage_complete.json']
 while not all(p.exists() for p in required):
  if time.monotonic()-waiting>21600:raise TimeoutError('qualification did not complete')
  time.sleep(10)
 eligibility=json.loads((out/f'scenes/{scene}/eligibility.json').read_text()) if (out/f'scenes/{scene}/eligibility.json').exists() else prepare_eligibility(out,scene,cfg);print('eligibility',scene,eligibility,flush=True)
 if not eligibility['eligible']:continue
 start=time.monotonic();assets=['seed_1729']+(['seed_2718'] if eligibility['route_a'] else [])+(eligibility['qualified_doses'] if eligibility['route_b'] else [])
 jobs=[('layers','seed_1729'),('primary','seed_1729'),('cross','seed_1729')]+[(task,asset) for asset in assets[1:] for task in ['layers','repeat']]
 for task,asset in jobs:
  if task=='layers' and (out/f'local/{scene}/layers/{asset}/complete.json').exists():continue
  if time.monotonic()-start>cfg['budget']['probe_seconds_per_scene']:raise TimeoutError('scene local budget exhausted')
  key=f'local_{scene}_{asset}_{task}';log=out/'setup'/f'{key}.log';trace=out/'setup'/f'{key}.strace'
  env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=str(queue),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_WAIT_POLICY='PASSIVE',PYTHONDONTWRITEBYTECODE='1')
  command=['strace','-f','-qq','-yy','-s','4096','-e','trace=open,openat,openat2,creat','-o',str(trace),sys.executable,str(ROOT/'scripts/run_corrected_probe.py'),'--scene',scene,'--asset',asset,'--task',task]
  record=dict(command=command,cpu_affinity=sorted(os.sched_getaffinity(0)),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
  with log.open('xb') as f:r=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
  record.update(exit_code=r.returncode,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scene_elapsed_seconds=time.monotonic()-start)
  with (out/'setup'/f'{key}_exit.json').open('x') as f:json.dump(record,f,sort_keys=True)
  print(key,r.returncode,flush=True)
  if r.returncode:raise RuntimeError('preserved failing local stage '+key)
 with (out/f'local/{scene}/execution_complete.json').open('x') as f:json.dump(dict(assets=assets,elapsed_seconds=time.monotonic()-start),f)
