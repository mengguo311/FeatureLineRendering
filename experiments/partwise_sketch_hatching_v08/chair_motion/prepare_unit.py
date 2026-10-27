import runtime
from runtime import sha,js
from pathlib import Path
import json,shutil
from linked_asset import load_asset
from motion import trajectory,save_trajectory,select_samples
UNIT=runtime.ROOT/'units/unit_003';CODE=Path(__file__).parent
def main():
    if (UNIT/'PROTOCOL.json').exists():raise FileExistsError('protocol frozen')
    copies=json.loads((UNIT/'INPUT_COPY_RECEIPT.json').read_text());assert sha(UNIT/'DECISION.json')==copies['decision_sha256']
    locks={}
    for row in copies['files']:
        assert sha(row['source'])==row['sha256'];locks[row['source']]=row['sha256']
        # render.py has an observational addition in the new copy only.
        if Path(row['destination']).parent!=CODE:assert sha(row['destination'])==row['sha256'];locks[row['destination']]=row['sha256']
    mesh,paths,meta,link,b=load_asset(UNIT/'delivery/assets/whole_spacing')
    assert meta['styles']['4']['spacing']==.0675
    save_trajectory(UNIT/'delivery/TRAJECTORY.json',trajectory())
    samples=select_samples(mesh,paths);js(UNIT/'delivery/SAMPLES.json',samples)
    for name in ('TRAJECTORY.json','SAMPLES.json'):locks[str(UNIT/'delivery'/name)]=sha(UNIT/'delivery'/name)
    locks[str(UNIT/'DECISION.json')]=sha(UNIT/'DECISION.json')
    sources={p.name:sha(p) for p in sorted(CODE.iterdir()) if p.is_file()}
    for name in sources:
        for directory in (UNIT/'source_snapshot',UNIT/'delivery/code'):
            directory.mkdir(parents=True,exist_ok=True);shutil.copy2(CODE/name,directory/name)
    js(UNIT/'SOURCE_LOCK.json',dict(source=str(CODE),files=sources));js(UNIT/'INPUT_LOCK.json',locks)
    protocol=dict(unit='unit_003',created_utc=runtime.now(),decision_sha256=sha(UNIT/'DECISION.json'),
        task='Fixed whole-Chair finite motion usability, not style or gating superiority',trajectory_sha256=sha(UNIT/'delivery/TRAJECTORY.json'),
        samples_sha256=sha(UNIT/'delivery/SAMPLES.json'),selected_paths=samples['selected_paths'],sample_anchors=len(samples['anchors']),
        observation='Continuous proxy-ray visibility at fixed material anchors; actual own-stroke AA2 raster sampled bilinearly before/after S. No borrowing other ink. Occlusions, offscreen, no-hit, label rejection all retained.',
        thresholds=dict(depth_tolerance=.004,ink_descriptive_threshold=1/255,AA=2),
        invariants='Original256690 rows/fullSH/geometry/opacity; weights27873; UNKNOWN170281; every path/face/bary/ID, style, .95 global paper and all original visibility rules fixed.',
        source_scope='Seat regional alpha*T S only; other regions/contours proxy-only; no new path-source certification',
        comparison='Natural hybrid and conventional proxy at identical cameras; unequal ink and paper budgets; no causal quality-superiority claim',
        reuse='Only same-camera completed outputs with all payload hashes checked; reverse zoom explicitly maps to forward frames',
        media='12fps APNG or installed video encoder; PNG sequence retained; all-frame decode; no frame interpolation',
        before_after='Render unchanged whole_baseline at exposed first/last cameras for actual same-camera spacing pair; not a new style experiment',
        falsification='Persistent-visible own-ink unexplained disappearance, foreground penetration, erased openings/legs or disruptive flicker => PARTIAL/negative. Proxy correspondence not physical GT. Full half orbit not360 certification.',
        source_lock_sha256=sha(UNIT/'SOURCE_LOCK.json'),input_lock_sha256=sha(UNIT/'INPUT_LOCK.json'),
        resources=dict(CPU=2,numeric_threads=1,GPU=False,serial=True),
        preserved='v05 sparse failures, all v07 negatives/H crossing/zero_step_cycle, unit001/002 143 and UNKNOWN raw receipts')
    js(UNIT/'PROTOCOL.json',protocol);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json')))
    print('Frozen',len(locks),'inputs',len(sources),'sources',len(samples['anchors']),'material anchors',flush=True)
if __name__=='__main__':main()
