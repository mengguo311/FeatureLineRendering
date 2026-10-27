"""Copy only hash-verified unit003 assets and explicitly selected runtime modules."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import hashlib,json,shutil,datetime,subprocess
ROOT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08')
UNIT=ROOT/'units/unit_004';OLD=ROOT/'units/unit_003';CODE=Path(__file__).parent
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def main():
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-gaussian-link-v08'
    assert not (UNIT/'INPUT_COPY_RECEIPT.json').exists()
    assert shutil.disk_usage('/').free>=2**30 and shutil.disk_usage(ROOT).free>=10*2**30
    package=OLD/'delivery';manifest=json.loads((package/'MANIFEST.json').read_text())['files'];records=[]
    def copy(src,dst,h):
        assert sha(src)==h,str(src)
        if dst.exists():raise FileExistsError(dst)
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(dst)==h
        records.append(dict(source=str(src),destination=str(dst),sha256=h))
    names='runtime.py base_model.py geometry.py hatching.py render.py display_settings.py membership.py hybrid.py link_renderer.py sh_utils_cpu.py source_ewa_baseline.cpp source_ewa_link.cpp linked_asset.py whole_asset.py motion.py run_motion.py'.split()
    for name in names:copy(package/'code'/name,CODE/name,manifest['code/'+name])
    for rel,h in manifest.items():
        if rel.startswith(('assets/whole_baseline/','assets/whole_spacing/','data/chair/')):copy(package/rel,UNIT/'delivery'/rel,h)
    copy(package/'SAMPLES.json',UNIT/'inputs/PARENT_SAMPLES.json',manifest['SAMPLES.json'])
    source_lock=json.loads((OLD/'SOURCE_LOCK.json').read_text())['files']
    copy(OLD/'source_snapshot/run_logged.py',CODE/'run_logged.py',source_lock['run_logged.py'])
    refs=[OLD/'renders/orbit/000',OLD/'renders/orbit/060',ROOT/'units/unit_002/renders/orbit_241_60_5.1/whole_spacing']
    for i,src in enumerate(refs):
        r=json.loads((src/'RENDER_RECEIPT.json').read_text())
        copy(src/'FRAME.npz',UNIT/'inputs/reference'/str(i)/'FRAME.npz',r['files']['FRAME.npz'])
        copy(src/'RENDER_RECEIPT.json',UNIT/'inputs/reference'/str(i)/'RENDER_RECEIPT.json',sha(src/'RENDER_RECEIPT.json'))
    result=dict(started_utc=started,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=records,
        decision_sha256=sha(UNIT/'DECISION.json'),parent_manifest_sha256=sha(package/'MANIFEST.json'),completed=True)
    (UNIT/'INPUT_COPY_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Verified and copied',len(records),'files')
if __name__=='__main__':main()
