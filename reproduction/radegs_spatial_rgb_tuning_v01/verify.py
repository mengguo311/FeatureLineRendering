import json,time,csv
import numpy as np
from PIL import Image
from common import *
from detector import *
from run import metrics
start=time.time();registry=json.loads((T/'REGISTRY.json').read_text())['views'];ps=json.loads((T/'PRESETS.json').read_text())['presets']
records=[];replay=[];baseline=[];readback=[]
for entry in registry:
    scene=entry['scene'];v=entry['view'];root=T/'scenes'/scene/v
    d=json.loads((root/'COMPLETE.json').read_text());assert d['complete_presets']==len(ps)
    with np.load(entry['path']) as z:rgb=rgb_from_npz(z)
    w,h=rgb.shape[1],rgb.shape[0]
    fields={kind:dict(np.load(root/f'fields_{kind}.npz')) for kind in SCALES}
    for p in ps:
        pr=root/'presets'/p['id'];a=dict(np.load(pr/'maps.npz'))
        r=candidate(mix_fields(fields[p['analysis']],p['detail_lambda']),p['threshold'])
        for key in r:
            np.testing.assert_array_equal(a[key],r[key])
            assert a[key].shape==(h,w) and np.isfinite(a[key]).all()
        for name,key in [('candidate','candidate_darkness'),('marked','marked'),('skeleton','skeleton')]:
            im=Image.open(pr/f'{name}.png');assert im.size==(w,h)
            expected=np.uint8(np.clip(1-a[key].astype(np.float32),0,1)*255+.5)
            np.testing.assert_array_equal(np.asarray(im)[...,0],expected)
        stat=metrics(a);saved=json.loads((pr/'metrics.json').read_text())
        for k,val in stat.items():assert saved[k]==val
        records.append(saved);readback.append(dict(scene=scene,view=v,preset=p['id'],bitexact=True))
    # Every view's unchanged union and A20 candidates equal previous pipeline cache.
    old=B/'depth_guided_native_dtu_v01'/'scenes'/scene/'detector'/f'{v}.npz'
    if old.exists():
        with np.load(old) as z, np.load(root/'presets'/'A20'/'maps.npz') as a:
            for key in ['union','darkness','marked']:
                np.testing.assert_array_equal(z[key],fields['native']['union'] if key=='union' else a[key])
        baseline.append(dict(scene=scene,view=v,previous_cache=str(old),sha256=sha(old),union_darkness_marked_bitexact=True))
    # Re-run actual RGB analyze on one fixed representative for each input condition.
    if v in ['0000','train_r_80']:
        f=analyze_rgb(rgb,'native')
        for key in ['union','detail','structural']:np.testing.assert_array_equal(f[key],fields['native'][key])
        replay.append(dict(scene=scene,view=v,analyze_replay_bitexact=True))
    # Native threshold nesting on actual images, not just synthetic control.
    masks=[np.load(root/'presets'/id/'maps.npz')['marked'] for id in ['A10','A15','A20','A30','A40','A50']]
    assert all(not np.any(b&~a) for a,b in zip(masks,masks[1:]))
assert len(records)==176 and len(readback)==176 and len(baseline)==10 and len(replay)==3
with open(T/'METRICS.csv','w') as f:
    writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
write(T/'METRICS.json',dict(rows=records,definitions=dict(marked_pixels='number of darkness>T pixels',skeleton_pixels='number of skeletonize(marked) pixels, not physical stroke arc length',components_8='connected components of candidate mask under 8-neighborhood',skeleton_endpoints_degree1='skeleton pixels with exactly one of 8 neighbors',skeleton_junction_pixels_degree_ge3='pixels, not consolidated graph junctions; diagonal adjacency can inflate this',mean_candidate_darkness='whole-frame mean darkness after gate; not SNR'),not_ground_truth_signal_to_noise=True))
write(T/'REPLAY.json',dict(utc=utc(),readback=readback,analyze_replay=replay,previous05_equivalence=baseline,seconds=time.time()-start))
sources=json.loads((T/'SOURCE_FREEZE.json').read_text())['files'];after={p:sha(p) for p in sources};assert after==sources
original=C.parent/'radegs_depth_guided_native_dtu_v01'/'boundary.py'
assert sha(original)==sha(C/'boundary.py')=='11bbb41a762f252d9eeb4ea3f0a8399ed026139d9490bb8cf161bc815e05dd30'
write(T/'SOURCE_AFTER.json',dict(utc=utc(),files=after,all_unchanged=True,original_boundary_path=str(original),original_boundary_sha256=sha(original)))
counts=dict(expected_views=11,completed_views=len(list((T/'scenes').glob('*/*/COMPLETE.json'))),expected_presets=16,preset_units=len(list((T/'scenes').glob('*/*/presets/*/maps.npz'))),native_candidate_png=len(list((T/'scenes').glob('*/*/presets/*/candidate.png'))),native_binary_png=len(list((T/'scenes').glob('*/*/presets/*/marked.png'))),native_skeleton_png=len(list((T/'scenes').glob('*/*/presets/*/skeleton.png'))),analysis_npz=len(list((T/'scenes').glob('*/*/fields_*.npz'))),new_3d_models=0,source_hashes_unchanged=len(after))
assert counts['completed_views']==11 and counts['preset_units']==176 and counts['native_candidate_png']==176 and counts['native_binary_png']==176 and counts['native_skeleton_png']==176 and counts['analysis_npz']==33
write(T/'COUNTS.json',counts)
write(T/'TESTRESULTS.json',dict(unit_tests=16,unit_passed=16,red_log='logs/TEST_RED.log',green_log='logs/TEST_GREEN.log',tolerance_relaxed=False,readback_units=176,readback_bitexact=True,previous05_bitexact_views=10,fresh_analyze_replays=3,source_unchanged=True,synthetic_control='analytic/RESULTS.json',scope='detector mechanism/readback verification; no real-scene GT quality or 3D benefit test'))
status('VERIFIED_AWAITING_REPORT',children=[],completed_views=11,completed_units=176,next_action='Finish actual visual review, Chinese report, packages')
print(json.dumps(counts))
