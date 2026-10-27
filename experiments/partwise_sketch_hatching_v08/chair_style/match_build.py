"""Freeze one BUILD-only normalization of post-union hatch increments."""
import runtime
from runtime import js,sha
from pathlib import Path
import json
import numpy as np
from linked_asset import npz
from run_view import verify
UNIT=runtime.ROOT/'units/unit_006'
def contour_base(f):return f['paper']*(1-f['contour'][:,:,None])+.03*f['contour'][:,:,None]
def main():
    verify(UNIT)
    if (UNIT/'BUILD_MATCH.json').exists():raise FileExistsError('BUILD factors already frozen')
    c=json.loads((UNIT/'PROTOCOL.json').read_text())['cameras'][0]
    paths=dict(reference=UNIT/'inputs/reference/0/FRAME.npz',selective=UNIT/'renders/selective'/c['view']/'FRAME.npz')
    frames={k:npz(p) for k,p in paths.items()}
    for key in ('source','paper','source_alpha','support','contour','proxy_depth','regions'):
        np.testing.assert_array_equal(frames['reference'][key],frames['selective'][key])
    mass={k:float(np.abs(f['hybrid']-contour_base(f)).sum(dtype=np.float64)) for k,f in frames.items()}
    if min(mass.values())<=0:raise ValueError('no visible hatch increment to match')
    target=min(mass.values());factors={k:target/v for k,v in mass.items()}
    record=dict(utc=runtime.now(),build=c['view'],natural_increment_raw_L1=mass,target=target,factors=factors,
        rule='display=paper_plus_contour + scalar*(natural_hybrid-paper_plus_contour); contour unchanged; one BUILD scalar per arm; no pixel selection or DEV fitting',
        scope='Style/scope differs. Equal aggregate hatch increment is only an additional display diagnostic, not equal-task causal superiority.',
        files={str(p.relative_to(UNIT)):sha(p) for p in paths.values()})
    js(UNIT/'BUILD_MATCH.json',record);js(UNIT/'BUILD_LOCK.json',dict(match_sha256=sha(UNIT/'BUILD_MATCH.json')))
    print(json.dumps(record),flush=True)
if __name__=='__main__':main()
