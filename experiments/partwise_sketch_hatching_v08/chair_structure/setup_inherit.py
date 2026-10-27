"""Verify and copy the completed unit006 package; never run its producers."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib,json,shutil,datetime
ROOT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08')
UNIT=ROOT/'units/unit_007';OLD=ROOT/'units/unit_006';CODE=Path(__file__).parent
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
    names=['runtime.py','run_logged.py','base_model.py','geometry.py','hatching.py','render.py','display_settings.py','membership.py','hybrid.py','link_renderer.py','sh_utils_cpu.py','source_ewa_baseline.cpp','source_ewa_link.cpp','linked_asset.py','whole_asset.py','parts_asset.py']
    for name in names:copy(OLD/'delivery/code'/name,CODE/name,manifest['code/'+name])
    for key,h in manifest.items():
        if key.startswith('data/chair/'):copy(OLD/'delivery'/key,UNIT/'delivery'/key,h)
        elif key.startswith('assets/selective/'):copy(OLD/'delivery'/key,UNIT/'delivery/assets/base'/Path(key).name,h)
    for view in ('orbit_61_24_5.1','orbit_241_24_5.1','orbit_241_60_5.1','orbit_151_36_5.1'):
        receipt=OLD/'renders/selective'/view/'RENDER_RECEIPT.json'
        key='evidence/renders/selective/'+view+'/RENDER_RECEIPT.json'
        assert sha(receipt)==manifest[key]
        record=json.loads(receipt.read_text())
        for name in ('FRAME.npz','source.png','RENDER_RECEIPT.json'):
            copy(receipt.parent/name,UNIT/'inputs/reference'/view/name,manifest[key] if name.endswith('.json') else record['files'][name])
    (UNIT/'INPUT_COPY_RECEIPT.json').write_text(json.dumps(dict(files=records,decision_sha256=sha(UNIT/'DECISION.json'),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),old_files_read_only=True),indent=2)+'\n')
    print('Verified/copied',len(records),flush=True)
if __name__=='__main__':main()
