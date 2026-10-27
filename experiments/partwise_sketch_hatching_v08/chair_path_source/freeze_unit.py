import runtime
from runtime import js,sha
from pathlib import Path
import json,shutil
import numpy as np
from geometry import orbit_camera
from linked_asset import load_asset
from motion import select_samples
UNIT=runtime.ROOT/'units/unit_004'
def main():
    if (UNIT/'PROTOCOL.json').exists():raise FileExistsError('already frozen')
    copied=json.loads((UNIT/'INPUT_COPY_RECEIPT.json').read_text())
    for row in copied['files']:
        assert sha(row['source'])==row['sha256'] and sha(row['destination'])==row['sha256']
    asset=UNIT/'delivery/assets/whole_spacing';mesh,paths,meta,link,b=load_asset(asset)
    parent=json.loads((UNIT/'inputs/PARENT_SAMPLES.json').read_text())
    samples=dict(selection='Inherited unit003 six seat paths, three stored-segment arclength anchors; gaps not interpolated',
        selected_paths=[v for v in parent['selected_paths'] if v.startswith('4:')],anchors=[v for v in parent['anchors'] if v['region']==4])
    assert len(samples['selected_paths'])==6 and len(samples['anchors'])==18
    check=select_samples(mesh,paths,{4:6})
    assert check['anchors']==samples['anchors'] and check['selected_paths']==samples['selected_paths']
    samples.update(asset_manifest_sha256=sha(asset/'FILES.json'),path_file_sha256=sha(asset/'region_4.npz'),
        source_sha256=link['source_sha256'],source_count=link['source_count'],total_seat_paths=len(np.unique(paths[4]['stroke_id'])),
        scope='6 paths/18 anchors only; no full-curve or physical attachment certificate')
    js(UNIT/'delivery/SAMPLES.json',samples)
    cameras=[orbit_camera(a,e,5.1,384) for a,e in [(61,24),(241,24),(241,60)]]
    js(UNIT/'delivery/CAMERAS.json',cameras)
    protocol=dict(unit='unit_004',created_utc=runtime.now(),decision_sha256=sha(UNIT/'DECISION.json'),
        task='Queryable sampled new-path source evidence and persistent original-kernel highlight; application capability only',
        cameras=cameras,exposure='All cameras previously exposed; no GS-unseen claim',build_view=cameras[0]['view'],
        samples_sha256=sha(UNIT/'delivery/SAMPLES.json'),cameras_sha256=sha(UNIT/'delivery/CAMERAS.json'),
        source_count=256690,selected_region_rows=27873,unknown_rows=170281,
        sampling='All positive bilinear stencil weights. Unique integer render pixels, raw events per anchor CSR; full original T, no top-K. Duplicate events across anchors retained; highlight IDs unioned once per path.',
        eligibility=dict(continuous_proxy_depth_tolerance=.004,own_native_AA_ink_min=1/255,pixel_source_alpha_min=.5,
            pixel_source_median_proxy_depth_tolerance=.08,contributor_pixel_proxy_depth_tolerance=.06,
            pixel_proxy_region=4,original_region_strength_positive=True,
            scope='Ink tolerance inherited from current renderer; .08/.06 source consistency gates inherited from v05, not physical error bounds. No threshold tuning.'),
        highlight=dict(selection='For each path, union all original IDs with eligible positive-beta events at its three BUILD anchors. No minimum exposure/top-K or view-count claim; empty stays empty.',
            strength=.5,color=[.02,.4,1.],source='Only front61/24 BUILD selects IDs; same saved IDs/strength used on all cameras',
            operation='Full original GS evaluated-color override; no kernel filtering, opacity edits, T changes or image-overlay substitute'),
        invariants='All original rows/geometry/fullSH/opacity; binding/M1/UNKNOWN; all paths/IDs/face/bary/style; fixed global paper, S, AA2, depth rules',
        comparisons='Natural source/highlight before-after and unchanged full hybrid. No causal association superiority, no null or effect-budget matching.',
        verification='Targeted RED/GREEN; full-T alpha/RGB/S reconstruction<=1e-6; trace on/off all output arrays exact; baseline19 arrays recover saved results; cold query/highlight replay exact',
        preserved='v05 sparse failure; all v07 negatives/H crossing/zero_step_cycle; v08 own-ink dropouts,143/UNKNOWN',
        resources=dict(CPU=2,numeric_threads=1,serial=True,GPU=False),time_budget_minutes=35)
    inputs={r['source']:r['sha256'] for r in copied['files']}
    inputs.update({r['destination']:r['sha256'] for r in copied['files'] if not r['destination'].startswith(str(Path(__file__).parent))})
    inputs[str(UNIT/'DECISION.json')]=sha(UNIT/'DECISION.json')
    for f in ('SAMPLES.json','CAMERAS.json'):inputs[str(UNIT/'delivery'/f)]=sha(UNIT/'delivery'/f)
    js(UNIT/'INPUT_LOCK.json',inputs)
    code=Path(__file__).parent;files={f.name:sha(f) for f in code.iterdir() if f.is_file()}
    shutil.copytree(code,UNIT/'source_snapshot',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(code,UNIT/'delivery/code',ignore=shutil.ignore_patterns('__pycache__'))
    js(UNIT/'SOURCE_LOCK.json',dict(source=str(code),files=files))
    protocol.update(source_lock_sha256=sha(UNIT/'SOURCE_LOCK.json'),input_lock_sha256=sha(UNIT/'INPUT_LOCK.json'))
    js(UNIT/'PROTOCOL.json',protocol);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json')))
    print('Frozen',len(files),'source files,',len(inputs),'inputs,18 anchors and3 cameras',flush=True)
if __name__=='__main__':main()
