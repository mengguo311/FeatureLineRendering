"""Copy only hash-verified unit007 package inputs into new unit008 paths."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib,json,shutil,datetime
ROOT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08')
UNIT=ROOT/'units/unit_008';OLD=ROOT/'units/unit_007';CODE=Path(__file__).parent
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def main():
    assert shutil.disk_usage('/').free>2**30 and shutil.disk_usage(ROOT).free>10*2**30
    manifest=json.loads((OLD/'delivery/MANIFEST.json').read_text())['files'];records=[]
    def copy(src,dst,expected):
        assert sha(src)==expected,str(src)
        if dst.exists():raise FileExistsError(dst)
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(dst)==expected
        records.append(dict(source=str(src),destination=str(dst),sha256=expected))
    for key,h in manifest.items():
        if key.startswith('code/'):copy(OLD/'delivery'/key,CODE/Path(key).name,h)
        elif key.startswith(('data/chair/','assets/on/','assets/off/','cameras/')):copy(OLD/'delivery'/key,UNIT/'delivery'/key,h)
    source_lock=json.loads((OLD/'SOURCE_LOCK.json').read_text())
    copy(CODE.parent/'chair_structure/run_logged.py',CODE/'run_logged.py',source_lock['run_logged.py'])
    for view in ('orbit_241_24_5.1','orbit_196_36_5.1','orbit_151_36_5.1','orbit_61_24_5.1'):
        for arm in ('on','off'):
            key=f'evidence/renders/{arm}/{view}/FRAME.npz'
            copy(OLD/'delivery'/key,UNIT/'inputs/reference'/arm/view/'FRAME.npz',manifest[key])
    (UNIT/'INPUT_COPY_RECEIPT.json').write_text(json.dumps(dict(files=records,decision_sha256=sha(UNIT/'DECISION.json'),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),old_files_read_only=True),indent=2)+'\n')
    print('Verified/copied',len(records),flush=True)
if __name__=='__main__':main()
