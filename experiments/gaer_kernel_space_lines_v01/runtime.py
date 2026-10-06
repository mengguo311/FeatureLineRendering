"""New stage IO/resources only. Never import any old stage runtime."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
STAGE='gaer_kernel_space_lines_v01'
ART=ROOT/'artifacts'/STAGE
OUT=ROOT/'out'/STAGE
EXP=ROOT/'experiments'/STAGE
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def utc():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def scoped(path):
    p=Path(path).resolve()
    if not any(p.is_relative_to(base) for base in [ART,OUT,EXP]):raise ValueError('outside authorized stage')
    return p
def write_json(path,value):
    p=scoped(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def rel(path):return str(Path(path).resolve().relative_to(ROOT))
def guard(unit,record=True):
    shared=subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip()
    shared=(ROOT/shared).resolve()
    used=sum(p.stat().st_size for base in [ART,OUT,EXP] if base.exists() for p in base.rglob('*') if p.is_file())
    r=dict(unit=unit,utc=utc(),root_free=shutil.disk_usage('/').free,shared_git_free=shutil.disk_usage(shared).free,stage_bytes=used,cpu_threads=2,gpu_used=False)
    assert r['root_free']>=4*1024**3 and r['shared_git_free']>=int(1.5*1024**3) and used<=2*1024**3,r
    if record:
        with scoped(ART/'RESOURCES.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
    return r
