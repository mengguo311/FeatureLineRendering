"""Bounded CPU-only round013 I/O. No writes to historical rounds."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='2'
os.sched_setaffinity(0,[0,1])
import datetime,hashlib,json,shutil,subprocess,time
from pathlib import Path
W=Path(__file__).resolve().parents[2]
R=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_013')
P=R.parent/'round_012'
D=W/'docs/partwise_sketch_hatching/round_013'
START=time.monotonic()
DEADLINE=datetime.datetime.fromisoformat('2026-10-21T07:06:26.478639+09:00')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def write(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix('.tmp');t.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n');t.replace(p)
def status(stage,**kw):
    obj=json.loads((R/'STATUS.json').read_text());obj.update(stage=stage,updated_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**kw);write(R/'STATUS.json',obj)
def resources():
    root=shutil.disk_usage('/').free;hdd=shutil.disk_usage('/mnt/hdd1').free
    used=sum(p.stat().st_size for p in R.parent.parent.rglob('*') if p.is_file())
    deps=sum(p.stat().st_size for p in (W/'.runtime_p0').rglob('*') if p.is_file())
    assert root>=2**30 and hdd>=10*2**30 and used+deps<12*2**30
    assert time.monotonic()-START<590 and datetime.datetime.now(datetime.timezone.utc)<DEADLINE
    assert sorted(os.sched_getaffinity(0))==[0,1]
    return {'root_free_bytes':root,'hdd_free_bytes':hdd,'task_bytes':used,'dependency_bytes':deps,'cpu_affinity':[0,1],'threads_max':2,'GPU':False}
def verify_prior():
    seal=json.loads((P/'SEAL.json').read_text());m=json.loads((P/'SHA256_MANIFEST.json').read_text())
    assert sha(P/'SHA256_MANIFEST.json')==seal['manifest_sha256']
    for f in m['files']:
        p=(W if f['root']=='worktree' else P)/f['path'];assert sha(p)==f['sha256'] and p.stat().st_size==f['bytes'],str(p)
    return {'verified_files':len(m['files']),'seal_sha256':sha(P/'SEAL.json')}
def verify_lock():
    assert subprocess.check_output(['git','branch','--show-current'],cwd=W,text=True).strip()=='partwise-sketch-hatching-p0p1-v01'
    lock=json.loads((D/'ASSET_LOCK.json').read_text())
    for p,h in lock['sources'].items():assert sha(W/p)==h,p
    for p,h in lock['inputs'].items():assert sha(p)==h,p
    rel=str((D/'ASSET_LOCK.json').relative_to(W));subprocess.run(['git','ls-files','--error-unmatch',rel],cwd=W,capture_output=True,check=True)
    assert not subprocess.check_output(['git','diff','HEAD','--',rel],cwd=W)
    return lock
