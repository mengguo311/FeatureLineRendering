import runtime
from runtime import js,sha
from pathlib import Path
import json,shutil
from linked_asset import load_asset
from structure import load_structure
from structure_motion import trajectory,select_curve_samples
UNIT=runtime.ROOT/'units/unit_008';CODE=Path(__file__).parent
def main():
    mesh,paths,meta,link,b=load_asset(UNIT/'delivery/assets/on');curve,config=load_structure(UNIT/'delivery/assets/on',mesh)
    assert len(curve['face'])==169 and sum(len(set(paths[r]['stroke_id'])) for r in (4,5))==178
    js(UNIT/'delivery/TRAJECTORY.json',trajectory());js(UNIT/'delivery/SAMPLES.json',select_curve_samples(curve))
    copied=json.loads((UNIT/'INPUT_COPY_RECEIPT.json').read_text())
    inputs={r['destination']:r['sha256'] for r in copied['files'] if not Path(r['destination']).is_relative_to(CODE)}
    for key in ('TRAJECTORY.json','SAMPLES.json'):inputs[str(UNIT/'delivery'/key)]=sha(UNIT/'delivery'/key)
    js(UNIT/'INPUT_LOCK.json',inputs)
    protocol=dict(schema='unit008_structure_motion_v1',utc=runtime.now(),decision_sha256=sha(UNIT/'DECISION.json'),
        input_lock_sha256=sha(UNIT/'INPUT_LOCK.json'),trajectory='delivery/TRAJECTORY.json',samples='delivery/SAMPLES.json',
        comparison='Current saved structure OFF/ON; fixed selective whole-Chair style. Application feasibility, not matched-budget superiority.',
        fixed=dict(original_rows=256690,unknown=170281,seat_support_rows=27873,active_regions=[4,5],paths=178,curve_segments=169,aa=2,width=1,depth_tolerance=.004,paper=.95),
        observation='64 fixed world-arclength midpoints; continuous same-proxy first hit without region gate; bilinear own structure only; own ink and raw RGB increment threshold 1/255 descriptive, not acceptance gate.',
        retained='v05 sparse failure; v07 whole-object negatives and zero_step_cycle; v08 143/UNKNOWN, old temporal drops and empty source sets; unit007 scheduling deviation.',
        limits='serial CPU <=2, no GPU, no new unit after12:25, complete/wrap by12:45, hardstop13:00 JST',
        scope='New camera rendering of saved current asset; no source association or semantic/physical/temporal guarantee; no authoring changes')
    js(UNIT/'PROTOCOL.json',protocol);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json')))
    js(UNIT/'SOURCE_LOCK.json',{f.name:sha(f) for f in sorted(CODE.iterdir()) if f.suffix in ('.py','.cpp')})
    dest=UNIT/'delivery/code';dest.mkdir()
    for f in CODE.iterdir():
        if f.suffix in ('.py','.cpp') and f.name not in ('setup_unit.py','freeze_unit.py','test_motion.py'):shutil.copy2(f,dest/f.name)
    print('Frozen',len(inputs),'inputs and 61 cameras before evaluation',flush=True)
if __name__=='__main__':main()
