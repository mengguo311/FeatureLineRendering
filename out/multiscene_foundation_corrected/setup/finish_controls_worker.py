"""Resume only missing controls after the preserved primary import failures."""
import concurrent.futures,datetime,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];out=ROOT/'out/multiscene_foundation_corrected'
def run(scene):
    status=out/f'setup/local_{scene}_seed_1729_primary_exit.json'
    while not status.exists():time.sleep(2)
    assert json.loads(status.read_text())['exit_code']==1
    key=f'local_{scene}_seed_1729_controls';trace=out/'setup'/f'{key}.strace';log=out/'setup'/f'{key}.log'
    command=['strace','-f','-qq','-yy','-s','4096','-e','trace=open,openat,openat2,creat','-o',str(trace),sys.executable,str(ROOT/'scripts/finish_corrected_F.py'),'--scene',scene]
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_WAIT_POLICY='PASSIVE')
    record=dict(command=command,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());start=time.monotonic()
    with log.open('xb') as f:r=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
    record.update(exit_code=r.returncode,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start)
    with (out/'setup'/f'{key}_exit.json').open('x') as f:json.dump(record,f,sort_keys=True)
    if r.returncode:raise RuntimeError(key)
    return scene,r.returncode
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    for result in pool.map(run,['lego','chair']):print(result,flush=True)
