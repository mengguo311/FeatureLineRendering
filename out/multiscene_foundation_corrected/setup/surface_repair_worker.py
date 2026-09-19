"""Rerun the preserved diagnosis with the registered P90 aggregation."""
import concurrent.futures,datetime,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];out=ROOT/'out/multiscene_foundation_corrected'
def run(scene):
    key=f'evaluation_{scene}_surface';trace=out/'setup'/f'{key}.strace';log=out/'setup'/f'{key}.log'
    command=['strace','-f','-qq','-yy','-s','4096','-e','trace=open,openat,openat2,creat','-o',str(trace),sys.executable,str(ROOT/'scripts/evaluate_corrected_scene.py'),'--scene',scene,'--task','surface']
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_WAIT_POLICY='PASSIVE')
    record=dict(command=command,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),repair='Use frozen adjacent-scale P90, preserving original attempt');start=time.monotonic()
    with log.open('xb') as f:r=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
    record.update(exit_code=r.returncode,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start)
    with (out/'setup'/f'{key}_exit.json').open('x') as f:json.dump(record,f,sort_keys=True)
    if r.returncode:raise RuntimeError(key)
    return scene,r.returncode
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    for result in pool.map(run,['lego','chair']):print(result,flush=True)
