"""Verify inherited files against their saved locks before copying exact bytes."""
import runtime
from runtime import sha,js
from pathlib import Path
import json
import shutil

UNIT=runtime.ROOT/'units/unit_001'
CODE=Path(__file__).parent
V05=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05')
V06=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_001')
V07=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/delivery_final_20261025')

def main():
    records=[]
    def copy(src,dst,expected):
        actual=sha(src)
        if actual!=expected:raise ValueError('inherited hash mismatch: '+str(src))
        if dst.exists():raise FileExistsError(dst)
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
        assert sha(dst)==actual
        records.append(dict(source=str(src),destination=str(dst),sha256=actual))
    locks=json.loads((V06/'DELIVERY_SOURCE_LOCK.json').read_text())
    names=['base_model.py','geometry.py','hatching.py','render.py','display_settings.py','membership.py','hybrid.py','link_renderer.py','sh_utils_cpu.py','source_ewa_baseline.cpp','source_ewa_link.cpp']
    for name in names:copy(V06/'delivery_source'/name,CODE/name,locks[name])
    package=V05/'baseline/portable_demo'
    plock=json.loads((package/'PACKAGE_FILES.json').read_text())['files']
    asset=package/'examples/chair_ink_preview'
    for f in sorted(asset.iterdir()):
        if f.is_file():copy(f,UNIT/'inputs/historical_asset'/f.name,plock[str(f.relative_to(package))])
    copy(package/'source/demo.py',UNIT/'inputs/provenance/demo_v04.py',plock['source/demo.py'])
    m=json.loads((V07/'MANIFEST.json').read_text())['files']
    for name in ('runtime.py','linked_source_cli.py'):
        key='portable/cold_baseline/code/'+name
        copy(V07/key,UNIT/'inputs/provenance'/('v07_'+name),m[key])
    p=json.loads((V06/'PROTOCOL.json').read_text());s=p['scenes']['chair']
    data=UNIT/'delivery/data/chair'
    copy(Path(s['source']['original_ply']),data/'source.ply',s['source']['sha256'])
    copy(Path(s['binding']),data/'SOURCE_BINDING.npz',p['input_hashes'][s['binding']])
    b=json.loads((V06/'results/chair/BINDING_LOCK.json').read_text())
    copy(V06/'results/chair/SELECTION.npz',UNIT/'inputs/SELECTION_v06.npz',b['files']['SELECTION.npz'])
    js(UNIT/'INPUT_COPY_RECEIPT.json',dict(files=records,decision_sha256=sha(UNIT/'DECISION.json'),utc=runtime.now(),old_files_read_only=True))
    print('Verified and copied',len(records),'files')

if __name__=='__main__':main()
