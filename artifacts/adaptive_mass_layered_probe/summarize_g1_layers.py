"""Descriptive report aggregation of saved, frozen primary G1 layer arrays."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];run=ROOT/'out/adaptive_mass_layered_probe/g1_run'
rows={}
for scene in ['lego','chair','drums','ficus']:
    for view in [1,27,53,79]:
        with np.load(run/'raw'/f'{scene}_{view}_full.npz') as raw,np.load(run/'native'/f'{scene}_{view}.npz') as native:
            alpha=native['native_alpha'];roi=alpha>=.5;A=raw['diagnostics.A'];retained=raw['layers.retained_mass'].sum(-1);overflow=raw['layers.overflow_mass']
            counts=raw['layers.layer_count'];K=np.diff(raw['events.offsets']).reshape(alpha.shape)
            rows[f'{scene}:{view}']=dict(foreground_pixels=int(roi.sum()),prefix_capture=float(A[roi].sum()/alpha[roi].sum()),reached_90=float(np.mean(A[roi]>=.9*alpha[roi])),retained_four_capture=float(retained[roi].sum()/alpha[roi].sum()),overflow_fraction_of_prefix=float(overflow[roi].sum()/A[roi].sum()),layer_count_p50_p95_p99_max=np.percentile(counts[roi],[50,95,99,100]).tolist(),K_p50_p95_p99_max=np.percentile(K[roi],[50,95,99,100]).tolist(),conservation_max_error=float(np.max(np.abs(retained+overflow-A))))
result=dict(scope='Descriptive primary tau90 Kmax128 G1 TRAIN layer summary; not a new gate or threshold.',script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),views=rows)
(ROOT/'artifacts/adaptive_mass_layered_probe/G1_LAYER_SUMMARY.json').write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
for key,r in rows.items():print(key,'prefix',round(r['prefix_capture'],6),'retained4',round(r['retained_four_capture'],6),'overflow/prefix',round(r['overflow_fraction_of_prefix'],6),'layer p50/p95/p99/max',r['layer_count_p50_p95_p99_max'])
