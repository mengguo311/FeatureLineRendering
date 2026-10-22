"""Freeze the two-scene path control protocol before actual evaluation."""
import runtime
from runtime import js,sha,now,OUTPUT_ROOT,output_guard
from pathlib import Path
import argparse,json,shutil
import numpy as np
from geometry import orbit_camera

def freeze(unit):
    unit=output_guard(unit)
    if (unit/'PROTOCOL.json').exists():raise FileExistsError('protocol exists')
    prev=OUTPUT_ROOT/'units/unit_001'
    oldlock=json.loads((prev/'EVIDENCE_LOCK.json').read_text())
    errors=[name for name,v in oldlock['files'].items() if sha(prev/name)!=v['sha256']]
    assert not errors,errors
    js(unit/'PREVIOUS_SEAL_AUDIT.json',dict(utc=now(),members=len(oldlock['files']),mismatches=errors,
        evidence_lock_sha256=sha(prev/'EVIDENCE_LOCK.json'),unchanged_negative_evidence=True))
    scenes={}
    for scene,example,configs in [
        ('chair','chair_ink_preview',[('build',0,65,4.7),('build',180,65,4.7),('build',90,45,4.9),('build',-90,45,4.9),
                                     ('evaluation',43,28,4.9),('evaluation',133,28,4.9),('evaluation',223,28,4.9)]),
        ('lego','lego_bucket_cross',[('build',237,35,4.9),('build',327,35,4.9),('build',147,35,4.9),('build',57,35,4.9),
                                    ('evaluation',282,28,5.1),('evaluation',12,28,5.1),('evaluation',102,28,5.1)])]:
        asset=OUTPUT_ROOT/'baseline/portable_demo/examples'/example
        meta=json.loads((asset/'asset.json').read_text());source=Path(meta['original']['original_ply'])
        assert sha(source)==meta['original']['sha256']
        with source.open('rb') as f:
            for line in f:
                if line.startswith(b'element vertex'):n=int(line.split()[-1])
                if line.strip()==b'end_header':break
        with np.load(asset/'region_4.npz') as z:
            ids=np.unique(z['stroke_id']);chosen=ids[np.unique(np.linspace(0,len(ids)-1,min(24,len(ids)),dtype=int))]
            candidate=np.flatnonzero(np.isin(z['stroke_id'],chosen))
            segments=candidate[np.unique(np.linspace(0,len(candidate)-1,min(128,len(candidate)),dtype=int))]
            covered=np.unique(z['stroke_id'][segments])
        cams=[]
        for split,az,el,dist in configs:
            c=orbit_camera(az,el,dist,384);c['split']=split;cams.append(c)
        scenes[scene]=dict(scene=scene,asset=str(asset),asset_hashes={x.name:sha(x) for x in asset.iterdir() if x.is_file()},
            source=meta['original'],source_count=n,target_name=meta['regions']['4'],region_id=4,
            cameras=cams,selected_stroke_ids=chosen,selected_segment_indices=segments,represented_stroke_ids=covered,
            path_scope='24 uniform saved stroke IDs then at most 128 uniform original segment indices; only sampled segments are the controlled path set',
            camera_disclosure='BUILD uses frozen authored proxy masks; evaluation excluded from binding/matching only. Chair evaluation was exposed in unit001. Lego historical exposure and underlying GS training view overlap not audited. Not blind semantic evaluation.')
    p=dict(unit='unit_002',frozen_utc=now(),scenes=scenes,region_id=4,
        question='Can a fixed sampled authored path set drive real original-kernel color and opacity controls, and does the same recipe execute on Lego?',
        source_ID_universe='all original PLY rows i=0..N-1, explicit IDs through culling and sort; no checkpoint write/reorder/filter',
        sampling=dict(grid_stride=3,grid_offset=1,grid_weight=1.,path_segments=128,max_events_per_view=3_000_000,
                      trace='all accepted alpha*T events, no topK; raw anchor CSR retains rejected and UNKNOWN; duplicate pixel/source events counted once per view for selection'),
        membership=dict(sample_alpha_min=.5,sample_proxy_source_z_tolerance=.08,contributor_proxy_z_tolerance=.06,
            path_proxy_z_tolerance=.02,min_exposure=.02,min_views=2,min_fraction=.7,view_mass=.002,
            channels='0 UNKNOWN; 1..5 authored regions, Lego unused channel5=0; no calibrated semantic probability'),
        path_selection=dict(min_accepted_mass=.02,min_views=2,view_mass=.002,min_retained_fraction=.7,
            strength='fraction * min(accepted_mass/.1,1), only supported region4; remaining rows UNKNOWN for this path query',
            mask='visible radius3px capsules of exactly the frozen sampled 3D segments; proxy depth tolerance .02; fixed AA band2px'),
        diagnostic=dict(tint=[.02,.4,1.],aa_band_pixels=2,
            tint_operation='blend evaluated full-SH3 color with tint; original SH untouched; residual view dependence scaled 1-strength',
            opacity_operation='COPY opacity_i * (1-scale*path_strength_i); original full SH3/geometry/order kept; rerender complete model and recompute T/acceptance/back layers',
            arms=['path_linked','nearest_path','shuffled'],
            spatial_control='same number of original kernels with smallest Euclidean distance to frozen segment midpoints, stable original-ID tiebreak; diagnostic spatial control, not surface attachment',
            shuffle_control='seed1729 permutation of path strengths within ten BUILD region-exposure rank bins',
            tint_matching='.85 * minimum full-strength BUILD fixed-grid RGB L1; exact linear scales, held fixed on evaluation',
            opacity_matching='.7 * minimum actual BUILD L1 at scale .85; ten bisection evaluations per arm, closest observed scale; max relative target error <=1%; failure remains invalid; no evaluation adjustment',
            locality_gate=dict(target_mean_L1_min=.02,far_non_target_fraction_max=.02),
            minimum_nonzero_target_mean_L1=.0001,
            evaluation='report both narrow path capsule intent and full authored-region intent, effect and leakage; no independent semantic truth'),
        engineering_gates=dict(trace_equality='bitwise all5 arrays vs uninstrumented CPU and trace-off',mass_RGB_max_abs=1e-6,
            original_ids='acceptance/cull/sort/T chain + row array invariance',save_load='all rows and source SHA, exact replay',
            opacity='actual new accepted traces must reconstruct edited RGB and alpha; do not reuse baseline T'),
        prior=dict(unit=str(prev),evidence_lock_sha256=sha(prev/'EVIDENCE_LOCK.json'),raw_audit_sha256=sha(unit/'PREVIOUS_RAW_AUDIT.json'),
            limitations='nearest-proxy also passed unit001 region gates; weak rear 67/256 anchors; native per-ID unavailable; historical depth discrepancies and Ficus negative preserved'),
        scientific_scope='UNCERTIFIED_CPU_MAPPING. Engineering partial, no native/physical/semantic/H1/H2/H3 certification.',
        resource_limits=dict(serial=True,cpu_affinity=2,numeric_threads=1,GPU=False,no_nested_models=True,
            unit_deadline_jst='2026-10-22T18:02:03+09:00',no_new_science_jst='21:20',wrap_jst='21:45',hardstop_jst='22:00'))
    src=Path(__file__).parent;snap=unit/'source_snapshot';shutil.copytree(src,snap,ignore=shutil.ignore_patterns('__pycache__'))
    p['source_hashes']={x.name:sha(x) for x in snap.iterdir() if x.is_file()}
    p['brief_sha256']=sha(OUTPUT_ROOT/'orchestration/BRIEF.md')
    js(unit/'PROTOCOL.json',p);js(unit/'PROTOCOL_LOCK.json',dict(sha256=sha(unit/'PROTOCOL.json'),frozen_utc=p['frozen_utc']))
    print(json.dumps(dict(protocol=str(unit/'PROTOCOL.json'),sha256=sha(unit/'PROTOCOL.json'),
                         scenes={k:dict(source_count=v['source_count'],segments=len(v['selected_segment_indices'])) for k,v in scenes.items()})))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--unit',required=True,type=Path);freeze(parser.parse_args().unit)
