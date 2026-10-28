"""Copy only hash-pinned delivered inputs; never execute the old package."""
import hashlib, json, shutil, datetime
from pathlib import Path

ROOT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09')
UNIT=ROOT/'units/unit_001'
BASE=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/delivery_final_20261027')
CODE=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert shutil.disk_usage('/').free>=2**30 and shutil.disk_usage(ROOT).free>=10*2**30
    manifest=json.loads((BASE/'CONTENTS.json').read_text())['files']; records=[]
    def copy(src,dst):
        key=str(src.relative_to(BASE)); expected=manifest[key]['sha256']
        assert sha(src)==expected, key
        dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists(): raise FileExistsError(dst)
        shutil.copyfile(src,dst); assert sha(dst)==expected
        records.append(dict(source=str(src),destination=str(dst),sha256=expected))
    pkg=BASE/'packages/unit_008'
    for folder,target in [('code',CODE),('assets/on',UNIT/'inputs/assets/on'),('data/chair',UNIT/'inputs/data/chair'),('cameras',UNIT/'inputs/cameras')]:
        for src in sorted((pkg/folder).iterdir()):
            if src.is_file():copy(src,target/src.name)
    views={'orbit_151_36_5.1':'030','orbit_196_36_5.1':'015','orbit_241_24_5.1':'000','orbit_61_24_5.1':'060'}
    for view,index in views.items():
        copy(pkg/f'evidence/renders/{index}/on/FRAME.npz',UNIT/f'inputs/cache/{view}/FRAME.npz')
    # Unit007 high-rear is outside unit008's finite half-orbit; provenance is separate.
    old=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/units/unit_007/renders/on/orbit_241_60_5.1/FRAME.npz')
    dst=UNIT/'inputs/cache/orbit_241_60_5.1/FRAME.npz';dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old,dst)
    records.append(dict(source=str(old),destination=str(dst),sha256=sha(old),verification='copy SHA equality; outside delivered CONTENTS; later original-GS cold check'))
    runtime=CODE/'runtime.py';runtime.write_text(runtime.read_text().replace('partwise_sketch_hatching_gaussian_link_v08','partwise_sketch_hatching_gaussian_link_v09').replace('new v08','new v09').replace('a v08','a v09'))
    # Reuse pure adjacency/walker helpers only; their runtime import resolves here.
    oldcode=CODE.parents[1]/'partwise_sketch_hatching_v07/placement_unit'
    for name in ('base_walk.py','line_field.py'):
        src=oldcode/name;dst=CODE/name;shutil.copyfile(src,dst)
        records.append(dict(source=str(src),destination=str(dst),sha256=sha(src),verification='read-only workspace helper SHA'))
    (UNIT/'IMPORT.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),decision_sha256=sha(UNIT/'DECISION.json'),files=records),indent=2)+'\n')
    print(json.dumps(dict(files=len(records),unit=str(UNIT))))
if __name__=='__main__':main()
