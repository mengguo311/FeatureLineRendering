import hashlib,json,os
from pathlib import Path
from datetime import datetime,timezone
B=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
T=B/'spatial_rgb_tuning_v01'
C=Path(__file__).resolve().parent
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for block in iter(lambda:f.read(2**20),b''):h.update(block)
    return h.hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def write(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n');os.replace(q,p)
def status(phase,**kw):
    p=T/'STATUS.json';d=json.loads(p.read_text()) if p.exists() else {}
    d.update(phase=phase,utc=utc(),new_3d_models=0,no_automatic_continuation=True,**kw);write(p,d)
