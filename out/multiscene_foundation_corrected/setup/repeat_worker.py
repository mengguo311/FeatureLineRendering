"""Complete independent C/posterior jobs after the repaired F seal."""
import concurrent.futures,datetime,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];out=ROOT/'out/multiscene_foundation_corrected';queue=int(sys.argv[1]);scene=['lego','chair'][queue]
cpus=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,cpus[16+queue*24:40+queue*24])
cfg=json.loads((out/'config.json').read_text());elig=json.loads((out/f'scenes/{scene}/eligibility.json').read_text())
assets=['seed_1729']+(['seed_2718'] if elig['route_a'] else [])+(elig['qualified_doses'] if elig['route_b'] else [])
earliest=min(datetime.datetime.fromisoformat(json.loads(p.read_text())['started_utc']) for p in (out/'setup').rglob(f'local_{scene}_seed_1729_*_exit.json'))
def elapsed():return (datetime.datetime.now(datetime.timezone.utc)-earliest).total_seconds()
def wait_file(path):
    while not path.exists():
        if elapsed()>cfg['budget']['probe_seconds_per_scene']:raise TimeoutError('total scene wall budget exhausted including prior attempts')
        time.sleep(2)
controls=out/f'setup/local_{scene}_seed_1729_controls_exit.json';wait_file(controls)
assert json.loads(controls.read_text())['exit_code']==0
assert (out/f'local/{scene}/F/frozen.json').exists()
def run(job):
    task,asset=job
    if task=='repeat':wait_file(out/f'local/{scene}/layers/{asset}/complete.json')
    if elapsed()>cfg['budget']['probe_seconds_per_scene']:raise TimeoutError('scene wall budget exhausted')
    key=f'local_{scene}_{asset}_{task}';trace=out/'setup'/f'{key}.strace';log=out/'setup'/f'{key}.log'
    command=['strace','-f','-qq','-yy','-s','4096','-e','trace=open,openat,openat2,creat','-o',str(trace),sys.executable,str(ROOT/'scripts/run_corrected_probe.py'),'--scene',scene,'--asset',asset,'--task',task]
    env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(queue),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_WAIT_POLICY='PASSIVE',PYTHONDONTWRITEBYTECODE='1')
    record=dict(command=command,cpu_affinity=sorted(os.sched_getaffinity(0)),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scheduler='four independent C/posterior jobs; unchanged per-arm inference')
    tick=time.monotonic()
    with log.open('xb') as f:r=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
    record.update(exit_code=r.returncode,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-tick,scene_elapsed_seconds=elapsed())
    with (out/'setup'/f'{key}_exit.json').open('x') as f:json.dump(record,f,sort_keys=True)
    print(key,r.returncode,flush=True)
    if r.returncode:raise RuntimeError('preserved failed stage '+key)
jobs=[('cross','seed_1729')]+[('repeat',asset) for asset in assets[1:]]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for unused in pool.map(run,jobs):pass
with (out/f'local/{scene}/execution_complete.json').open('x') as f:json.dump(dict(assets=assets,elapsed_seconds=elapsed(),includes_prior_attempts=True,first_local_stage_utc=earliest.isoformat(),primary_control_repair='F/control_completion/complete.json',all_jobs=jobs),f)
print('scene local complete',scene,elapsed(),flush=True)
