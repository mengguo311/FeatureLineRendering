"""Copy verified unit002 inputs only; historical producers are never imported."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import hashlib,json,shutil,datetime
ROOT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08')
UNIT=ROOT/'units/unit_003';OLD=ROOT/'units/unit_002';CODE=Path(__file__).parent
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def main():
    if (UNIT/'INPUT_COPY_RECEIPT.json').exists():raise FileExistsError('already copied')
    assert shutil.disk_usage('/').free>=2**30 and shutil.disk_usage(ROOT).free>=10*2**30
    package=OLD/'delivery';manifest=json.loads((package/'MANIFEST.json').read_text())['files'];records=[]
    def copy(src,dst,h):
        assert sha(src)==h,str(src)
        if dst.exists():raise FileExistsError(dst)
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(dst)==h
        records.append(dict(source=str(src),destination=str(dst),sha256=h))
    for rel,h in manifest.items():
        if rel.startswith('code/'):copy(package/rel,CODE/Path(rel).name,h)
        if rel.startswith(('assets/whole_baseline/','assets/whole_spacing/','data/chair/')):copy(package/rel,UNIT/'delivery'/rel,h)
    oldsource=json.loads((OLD/'SOURCE_LOCK.json').read_text())['files']
    copy(OLD/'source_snapshot/run_logged.py',CODE/'run_logged.py',oldsource['run_logged.py'])
    for view in ('orbit_61_24_5.1','orbit_241_24_5.1'):
        for state in ('whole_baseline','whole_spacing'):
            src=OLD/'renders'/view/state;receipt=json.loads((src/'RENDER_RECEIPT.json').read_text())
            for name in ('FRAME.npz','hybrid.png'):
                copy(src/name,UNIT/'inputs/reference'/view/state/name,receipt['files'][name])
    out=dict(files=records,decision_sha256=sha(UNIT/'DECISION.json'),parent_manifest_sha256=sha(package/'MANIFEST.json'),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (UNIT/'INPUT_COPY_RECEIPT.json').write_text(json.dumps(out,indent=2)+'\n')
    print('Verified and copied',len(records),'files',flush=True)
if __name__=='__main__':main()
