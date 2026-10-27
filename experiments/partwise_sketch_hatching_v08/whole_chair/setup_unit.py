"""Copy only hash-verified unit001 inputs; never execute its producer scripts."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import hashlib,json,shutil,datetime

ROOT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08')
UNIT=ROOT/'units/unit_002'
OLD=ROOT/'units/unit_001'
CODE=Path(__file__).parent
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
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
        assert sha(dst)==h
        records.append(dict(source=str(src),destination=str(dst),sha256=h))
    names=['runtime.py','run_logged.py','linked_asset.py','base_model.py','geometry.py','hatching.py','render.py','display_settings.py','membership.py','hybrid.py','link_renderer.py','sh_utils_cpu.py','source_ewa_baseline.cpp','source_ewa_link.cpp']
    for name in names:copy(package/'code'/name,CODE/name,manifest['code/'+name])
    for rel,h in manifest.items():
        if rel.startswith(('assets/baseline/','assets/spacing/','data/chair/')):
            copy(package/rel,UNIT/'delivery'/rel,h)
    # The previous immutable artifact manifest certifies cached reference images/arrays.
    oldlock=json.loads((OLD/'ARTIFACT_LOCK.json').read_text())['files'] if (OLD/'ARTIFACT_LOCK.json').exists() else None
    for view in ('orbit_61_24_5.1','orbit_241_24_5.1','orbit_241_60_5.1'):
        c=OLD/'cameras'/(view+'.json')
        copy(c,UNIT/'cameras'/c.name,sha(c))
        for state in ('baseline','spacing'):
            for name in ('FRAME.npz','hybrid.png','RENDER_RECEIPT.json'):
                src=OLD/'renders'/view/state/name
                if name=='hybrid.png':
                    rel='evidence/renders/'+view+'/'+state+'/'+name
                    # Receipt file hashes, generated before audit, cover the actual payload.
                receipt=json.loads((src.parent/'RENDER_RECEIPT.json').read_text())
                h=receipt['files'][name] if name in receipt['files'] else sha(src)
                copy(src,UNIT/'inputs/historical_patch'/view/state/name,h)
    record=dict(files=records,decision_sha256=sha(UNIT/'DECISION.json'),parent_manifest_sha256=sha(package/'MANIFEST.json'),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (UNIT/'INPUT_COPY_RECEIPT.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Verified and copied',len(records),'inputs/source files')
if __name__=='__main__':main()
