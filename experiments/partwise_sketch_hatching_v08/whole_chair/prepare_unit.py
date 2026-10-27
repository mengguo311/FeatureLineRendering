import runtime
from runtime import sha,js
from pathlib import Path
import json,shutil
from whole_asset import save_preset,PRESET

UNIT=runtime.ROOT/'units/unit_002'
CODE=Path(__file__).parent
def main():
    if (UNIT/'PROTOCOL.json').exists():raise FileExistsError('protocol frozen')
    copies=json.loads((UNIT/'INPUT_COPY_RECEIPT.json').read_text())
    assert sha(UNIT/'DECISION.json')==copies['decision_sha256']
    locks={}
    for row in copies['files']:
        for key in ('source','destination'):
            assert sha(row[key])==row['sha256'],row[key];locks[row[key]]=row['sha256']
    for state in ('baseline','spacing'):save_preset(UNIT/'delivery/assets'/state,UNIT/'delivery/assets'/('whole_'+state))
    sources={p.name:sha(p) for p in sorted(CODE.iterdir()) if p.is_file()}
    for name in sources:
        target=UNIT/'source_snapshot'/name;target.parent.mkdir(exist_ok=True);shutil.copy2(CODE/name,target)
    cli_names=['runtime.py','linked_asset.py','whole_asset.py','base_model.py','geometry.py','hatching.py','render.py','display_settings.py','membership.py','hybrid.py','link_renderer.py','sh_utils_cpu.py','source_ewa_baseline.cpp','source_ewa_link.cpp']
    for name in cli_names:
        target=UNIT/'delivery/code'/name;target.parent.mkdir(exist_ok=True);shutil.copy2(CODE/name,target)
    cameras=[json.loads((UNIT/'cameras'/(view+'.json')).read_text()) for view in ('orbit_61_24_5.1','orbit_241_24_5.1','orbit_241_60_5.1')]
    for f in (UNIT/'cameras').iterdir():locks[str(f)]=sha(f)
    for state in ('whole_baseline','whole_spacing'):
        for f in (UNIT/'delivery/assets'/state).iterdir():
            if f.is_file():locks[str(f)]=sha(f)
    locks[str(UNIT/'DECISION.json')]=sha(UNIT/'DECISION.json')
    js(UNIT/'SOURCE_LOCK.json',dict(source=str(CODE),files=sources,cli_files={n:sources[n] for n in cli_names}))
    js(UNIT/'INPUT_LOCK.json',locks)
    protocol=dict(unit='unit_002',created_utc=runtime.now(),decision_sha256=sha(UNIT/'DECISION.json'),preset=PRESET,
        task='Whole-object presentation capability with saved seat-spacing edit, not a generator/gating superiority test',
        cameras=cameras,states=['whole_baseline','whole_spacing'],operations='Reuse saved .045 and .0675 layouts, no path regeneration',
        references='Same-camera freshly rasterized conventional proxy black ink; hash-verified unit001 patch shown as historical scope reference',
        original_source='Chair256690 complete original rows, frozen geometry/covariance/opacity/fullSH/order; all-row evaluated-color override only',
        target='Authored region4, not semantic GT; weights27873 and UNKNOWN170281 fixed',
        invariants='No geometric/style/seed/angle/width/length changes. Non-target path bytes, source binding and mesh identical. Existing arclength phase confound retained.',
        visibility=dict(AA=2,depth_tolerance=.004,boundary_band_pixels=2,seat_mask=16,other_masks='unchanged inherited sibling support'),
        controls='Global base identical across seat edit; global source difference is intentional, not local leakage. Source/alpha/S and seat pre-S checked against unit001.',
        comparisons='Natural effects and coverage disclosed; scope/budget differ. No equal-task causal claim, no parameter fitting or scans.',
        falsification='Check full-object legs, arm holes, foreground hiding, contour/GS misalignment and visible seat edit at all fixed views. If conventional proxy is simpler/clearer, keep it as application reference; no white-strength scan.',
        resource=dict(CPU=2,numeric_threads=1,CUDA_VISIBLE_DEVICES='',serial=True),
        source_lock_sha256=sha(UNIT/'SOURCE_LOCK.json'),input_lock_sha256=sha(UNIT/'INPUT_LOCK.json'),
        preserved_failures='v05 sparse; all v07 negatives/H crossing/zero_step_cycle; unit001 outer143 and controller UNKNOWN; no new-path ID certificate or video')
    js(UNIT/'PROTOCOL.json',protocol);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json'),utc=runtime.now()))
    print('Frozen protocol',sha(UNIT/'PROTOCOL.json'),'inputs',len(locks),'sources',len(sources))
if __name__=='__main__':main()
