"""Freeze protocol and then all prepared inputs, before any camera evaluation."""
import runtime
from runtime import js,sha
from pathlib import Path
import argparse,json,shutil
from geometry import orbit_camera

UNIT=runtime.ROOT/'units/unit_005'
CODE=Path(__file__).parent
def main(stage):
    if stage=='protocol':
        if (UNIT/'PROTOCOL.json').exists():raise FileExistsError('protocol already frozen')
        cameras=[orbit_camera(a,e,5.1,384) for a,e in ((61,24),(241,24),(241,60))]
        p=dict(unit='unit_005',decision_sha256=sha(UNIT/'DECISION.json'),frozen_utc=runtime.now(),cameras=cameras,
            task='Application capability: selectable seat/upper-back editing, saved proxy angle change and separate original-source region tint',
            history='Exact unit004 whole_spacing asset and verified historical camera arrays; shown only as reused context',
            common_control=dict(region=5,angle=-25.,spacing=.045,length=.22,width=1.,ink_strength=.45,plane='xz',visibility_mask=32,
                preparation='Explicit regeneration of inherited 208-path / mask40 region; kept separate from angle comparison'),
            edit=dict(region=5,angle=25.,other_style_unchanged=True,new_identities=True),
            source_control=dict(region=5,mix=.5,color=[.02,.4,1.],selection='Frozen original region_id=5 and not UNKNOWN; multiply original membership by mix',
                trace='All accepted full-T events on fixed 8-pixel native lattice, including background; no top-K or camera reselection'),
            fixed=dict(original_rows=256690,unknown_rows=170281,seat_rows=27873,upper_back_rows=11576,global_paper=[.95,.95,.95],
                seat_S_unchanged=True,upper_back_ink='proxy-only',non_target_regions=[1,2,3,4],supersample=2,depth_tolerance=.004,evaluation_band_pixels=2),
            scope='Natural-budget parameter edit; not an equal-budget quality/mechanism comparison. No new path certificate, video, semantic labeling or physical ownership claim.',
            cameras_exposed=True,source_training_unseen_claim=False,
            falsification=json.loads((UNIT/'DECISION.json').read_text())['falsification'])
        js(UNIT/'PROTOCOL.json',p)
        for i,c in enumerate(cameras):js(UNIT/'delivery/cameras'/f'{i}.json',c)
        files={}
        for f in sorted(CODE.iterdir()):
            if f.is_file():
                files[f.name]=sha(f)
                for dst in (UNIT/'source_snapshot',UNIT/'delivery/code'):
                    dst.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst/f.name)
        js(UNIT/'SOURCE_LOCK.json',files)
        js(UNIT/'PROTOCOL_LOCK.json',dict(decision=sha(UNIT/'DECISION.json'),protocol=sha(UNIT/'PROTOCOL.json'),source=sha(UNIT/'SOURCE_LOCK.json')))
    else:
        if (UNIT/'INPUT_LOCK.json').exists():raise FileExistsError('inputs already frozen')
        files={}
        for sub in ('inputs','delivery/data','delivery/assets','delivery/controls','delivery/cameras'):
            for f in sorted((UNIT/sub).rglob('*')):
                if f.is_file():files[str(f.relative_to(UNIT))]=sha(f)
        js(UNIT/'INPUT_LOCK.json',files)
        js(UNIT/'INPUT_SEAL.json',dict(inputs=sha(UNIT/'INPUT_LOCK.json'),protocol_lock=sha(UNIT/'PROTOCOL_LOCK.json'),utc=runtime.now()))
    print('Frozen',stage,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['protocol','inputs']);main(p.parse_args().stage)
