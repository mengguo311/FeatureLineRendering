"""Precompute immutable native mixtures; no local image evidence or fitting."""
import concurrent.futures,datetime,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];out=ROOT/'out/multiscene_foundation_corrected'
jobs=[]
for scene in ['lego','chair']:
    e=json.loads((out/f'scenes/{scene}/eligibility.json').read_text())
    assets=(['seed_2718'] if e['route_a'] else [])+(e['qualified_doses'] if e['route_b'] else [])
    jobs.extend((scene,a) for a in assets)
cpus=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,cpus[8:16])
def run(job):
    scene,asset=job;key=f'local_{scene}_{asset}_layers'
    output=out/f'local/{scene}/layers/{asset}'
    if (output/'complete.json').exists():return key,'already complete'
    trace=out/'setup'/f'{key}.strace';log=out/'setup'/f'{key}.log'
    command=['strace','-f','-qq','-yy','-s','4096','-e','trace=open,openat,openat2,creat','-o',str(trace),sys.executable,str(ROOT/'scripts/run_corrected_probe.py'),'--scene',scene,'--asset',asset,'--task','layers']
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_WAIT_POLICY='PASSIVE',PYTHONDONTWRITEBYTECODE='1')
    record=dict(command=command,cpu_affinity=sorted(os.sched_getaffinity(0)),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scheduler='independent native-layer precomputation');start=time.monotonic()
    with log.open('xb') as f:r=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
    record.update(exit_code=r.returncode,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start)
    with (out/'setup'/f'{key}_exit.json').open('x') as f:json.dump(record,f,sort_keys=True)
    if r.returncode:raise RuntimeError(key)
    return key,r.returncode
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for result in pool.map(run,jobs):print(result,flush=True)
