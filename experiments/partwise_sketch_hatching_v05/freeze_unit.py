import runtime
from runtime import js,sha,now,output_guard,OUTPUT_ROOT
from pathlib import Path
import json,shutil,argparse
from geometry import orbit_camera

def freeze(unit):
    unit=output_guard(unit)
    if (unit/'PROTOCOL.json').exists():raise FileExistsError('protocol already frozen')
    asset=OUTPUT_ROOT/'baseline/portable_demo/examples/chair_ink_preview'
    meta=json.loads((asset/'asset.json').read_text())
    source=Path(meta['original']['original_ply'])
    assert sha(source)==meta['original']['sha256']
    with source.open('rb') as f:
        for line in f:
            if line.startswith(b'element vertex'):n=int(line.split()[-1])
            if line.strip()==b'end_header':break
    old=Path(__file__).parent.parent/'partwise_sketch_hatching_v04'
    delivered=OUTPUT_ROOT/'baseline/portable_demo/source'
    verified={}
    for name in ('model_adapter.py','source_ewa.cpp','geometry.py','hatching.py','render.py','runtime.py','demo.py','region_tools.py'):
        assert sha(old/name)==sha(delivered/name),name
        verified[name]=sha(old/name)
    configs=[('build',0,65,4.7),('build',180,65,4.7),('build',90,45,4.9),('build',-90,45,4.9),
             ('evaluation',43,28,4.9),('evaluation',133,28,4.9),('evaluation',223,28,4.9)]
    cams=[]
    for split,az,el,dist in configs:
        c=orbit_camera(az,el,dist,384);c['split']=split;cams.append(c)
    calib=json.loads((Path('/mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_001/PROTOCOL.json')).read_text())
    src=Path(__file__).parent;snap=unit/'source_snapshot';shutil.copytree(src,snap)
    p=dict(unit='unit_001',frozen_utc=now(),scene='chair',asset=str(asset),region_id=4,
        target_name=meta['regions']['4'],source=meta['original'],source_count=n,
        source_index='zero-based original PLY row i, full universe 0..N-1; never traversal index',
        asset_hashes={p.name:sha(p) for p in asset.iterdir() if p.is_file()},
        delivered_code_hashes=verified,source_hashes={p.name:sha(p) for p in snap.iterdir() if p.is_file()},
        cameras=cams,camera_disclosure='BUILD projects saved authored regions, including two original authoring angles. Evaluation orbit views held out from this binding only; 43/28 historical exposed. No independent semantic labels; original-GS training view coverage not audited.',
        calibration=dict(camera=calib['static_cameras'][0],cache=calib['input_cache_probe'],cache_sha256=sha(calib['input_cache_probe']),scope='historical CPU source-only replay; not native CUDA per-ID calibration'),
        sampling=dict(grid_stride=3,grid_offset=1,grid_weight=1.,path_segments=256,path_rule='uniform linspace over saved region_4 segment order; midpoint face/bary anchor; all attempted samples retained',max_events_per_view=3_000_000,trace='ALL accepted contributors; no top-K; overflow is failure'),
        membership=dict(sample_alpha_min=.5,sample_proxy_source_z_tolerance=.08,contributor_proxy_z_tolerance=.06,
                        path_proxy_z_tolerance=.02,min_exposure=.02,min_views=2,min_fraction=.7,view_mass=.002,
                        view_conflict='two views with >=.02 total exposure, >=.8 confident different known region; conflict remains UNKNOWN',
                        channels='0 UNKNOWN/rejected/background, 1..5 exact authored proxy region IDs',
                        meaning='accepted alpha*T exposure fractions, not calibrated semantic or physical-surface probabilities'),
        diagnostic=dict(tint=[.02,.4,1.],operation='per-original-row blend AFTER original full SH3 + lower clamp; retain (1-strength) of all SH view dependence. Original arrays/checkpoint unchanged; copy colors per view.',
            controls=['nearest proxy face centroid region (spatial control, not true surface)','seed1729 source-ID shuffle within exposure deciles'],
            proposed='supported region_id==4 times soft q4; all UNKNOWN left unchanged',
            matching='single scalar per arm: .85 * minimum full-strength BUILD sampled-grid RGB-L1 budget / own full-strength budget; locked for all evaluation cameras. Same tint; no count-only matching.',
            aa_band_pixels=2,locality_gate=dict(target_mean_L1_min=.02,far_non_target_fraction_max=.02),
            locality_scope='intent/self-consistency relative to same authored proxy; independent semantics not measured',
            selected_only='opacity zero for unselected in copy; recomputed T, explicitly NOT original contribution'),
        engineering_gates=dict(trace_on_off='bitwise equal all five baseline CPU arrays',original_cpp='bitwise equal all five arrays',sample_mass_max_abs=1e-6,sample_SH_rgb_max_abs=1e-6,
                               source_order='explicit IDs survive near cull, depth sort and save/load',minimum_nonzero_target_mean_L1=1e-4),
        scientific_scope='UNCERTIFIED_CPU_MAPPING. No native per-ID validation, no H1/H2/H3 claim; proxy attachment not physical identity.',
        prior_negative=dict(ficus_original_rows=284835,ficus_supported_rows=357,reserved_nonunknown=[0,1],lesson='do not confuse sparse source IDs with usable visible control; preserve coverage and UNKNOWN'),
        resource_limits=dict(cpu_affinity=2,numeric_threads=1,cuda=False,serial=True,unit_deadline_jst='2026-10-22T17:28:39+09:00'))
    js(unit/'PROTOCOL.json',p)
    js(unit/'PROTOCOL_LOCK.json',dict(sha256=sha(unit/'PROTOCOL.json'),frozen_utc=p['frozen_utc']))
    print(json.dumps(dict(protocol=str(unit/'PROTOCOL.json'),sha256=sha(unit/'PROTOCOL.json'),source_count=n)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);freeze(p.parse_args().unit)
