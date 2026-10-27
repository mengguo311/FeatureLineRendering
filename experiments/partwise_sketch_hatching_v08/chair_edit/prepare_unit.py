import runtime
from runtime import sha,js
from pathlib import Path
import json
import shutil
import numpy as np
from geometry import orbit_camera
from linked_asset import initialize,SAMPLES,npz

UNIT=runtime.ROOT/'units/unit_001'
V06=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_001')

def main():
    if (UNIT/'PROTOCOL.json').exists():raise FileExistsError('protocol already frozen')
    decision=json.loads((UNIT/'DECISION.json').read_text());assert decision['action']=='continue'
    copies=json.loads((UNIT/'INPUT_COPY_RECEIPT.json').read_text())
    for row in copies['files']:
        assert sha(row['source'])==row['sha256'] and sha(row['destination'])==row['sha256']
    cameras=[dict(orbit_camera(a,e,5.1,384),azimuth=a,elevation=e,distance=5.1,split='exposed_DEV') for a,e in [(61.,24.),(241.,24.),(241.,60.)]]
    oldlocks=json.loads((V06/'ARTIFACT_LOCK.json').read_text())['files'];extra=[]
    for c in cameras:
        rel='results/chair/'+c['view']+'/FRAME.npz';src=V06/rel
        assert sha(src)==oldlocks[rel]
        dst=UNIT/'inputs/v06_frames'/c['view']/'FRAME.npz';dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
        extra.append(dict(source=str(src),destination=str(dst),sha256=oldlocks[rel]))
        js(UNIT/'cameras'/(c['view']+'.json'),c)
    code=Path(__file__).parent;delivery=UNIT/'delivery/code'
    shutil.copytree(code,delivery,ignore=shutil.ignore_patterns('__pycache__'))
    source_hashes={f.name:sha(f) for f in sorted(code.iterdir()) if f.is_file()}
    js(UNIT/'SOURCE_LOCK.json',dict(source=str(code),delivery=str(delivery),files=source_hashes))
    inputs={row['source']:row['sha256'] for row in copies['files']+extra}
    inputs.update({row['destination']:row['sha256'] for row in copies['files']+extra})
    inputs[str(UNIT/'DECISION.json')]=sha(UNIT/'DECISION.json')
    js(UNIT/'INPUT_LOCK.json',inputs)
    protocol=dict(unit='unit_001',created_utc=runtime.now(),decision_sha256=sha(UNIT/'DECISION.json'),
        source_lock_sha256=sha(UNIT/'SOURCE_LOCK.json'),input_lock_sha256=sha(UNIT/'INPUT_LOCK.json'),
        task='Parameterized linked Chair seat edit/save/cold reload/actual camera output; application capability, no quality-superiority claim',
        baseline=dict(angle=95.,spacing=.045,length=.22,width=1.,ink_strength=.35,paper_effect=1.),
        operations=dict(spacing=dict(spacing=.0675),paper_half=dict(paper_effect=.5)),
        cameras=cameras,trace_pixels_384=SAMPLES,trace_rule='Fixed grid plus background pixel, no output-dependent selection; all accepted full-T original-ID events, no top-K',
        visibility=dict(policy='region4 owner-only 16 in baseline and regenerated edit',legacy_mask=20,depth_tolerance=.004,AA=2,
            disclosure='Inherited transferred paths use parent arclength phase; regeneration includes boundary phase restart. Separate historical cap change; not isolated spacing algorithm gain.'),
        comparison='Natural strength only: intentional user density/source-paper edits, not matched-budget mechanism comparison. Fixed paper for spacing; fixed paths/S for paper effect.',
        masks=dict(target='saved authored proxy region4, not semantic GT',boundary_band_pixels=2),
        invariant='256690 original rows, PLY, means, covariance, opacity, fullSH, mesh, region labels, UNKNOWN170281, non-target region path bytes fixed',
        checks=['actual RED then GREEN edit isolation/identity/roundtrip','actual original-GS paper and full-T trace reconstruction <=1e-6','fresh-process cold spacing and paper reload arrays exact','all camera static outputs, no camera-dependent regeneration','all PNG full decode and SHA'],
        inherited_negatives='v05 sparse far8.044%, eroded31px, whole-region change4.49%; v07 no whole-object winner, H cross collapse and zero_step_cycle; no native Gaussian hatch or path ownership certification',
        resources=dict(CPU=2,numeric_threads=1,CUDA_VISIBLE_DEVICES='',serial=True),evaluation_started=False)
    js(UNIT/'PROTOCOL.json',protocol);js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json'),utc=runtime.now()))
    initialize(UNIT/'inputs/historical_asset',UNIT/'delivery/data/chair',UNIT/'delivery/assets/baseline')
    weights=npz(UNIT/'delivery/assets/baseline/SOURCE_LINK.npz')
    legacy=npz(UNIT/'inputs/SELECTION_v06.npz')
    np.testing.assert_array_equal(weights['paper_strength'],legacy['primary'])
    np.testing.assert_array_equal(weights['ink_strength'],legacy['primary'])
    positive=np.flatnonzero(weights['paper_strength']>0)
    unknown=np.flatnonzero(weights['unknown'])
    js(UNIT/'QUERY_IDS.json',dict(ids=[0,int(positive[0]),int(positive[len(positive)//2]),int(unknown[0]),256689],selection='deterministic original-row inventory, not selected by rendered effect'))
    js(UNIT/'PREPARATION.json',dict(source_copy_files=len(source_hashes),inputs=len(inputs),region_rows=len(positive),unknown=int(weights['unknown'].sum()),baseline=str(UNIT/'delivery/assets/baseline'),old_v06_weights_equal=True))
    print('Frozen protocol',sha(UNIT/'PROTOCOL.json'),'and baseline asset')

if __name__=='__main__':main()
