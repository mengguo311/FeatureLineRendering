"""Compare actual full-build, exported-asset and relocated-package replay results."""
import runtime
from runtime import js, sha, now
from pathlib import Path
import argparse
import json
import numpy as np


def compare(a,b):
    if a.suffix=='.npz':
        with np.load(a) as x,np.load(b) as y:
            assert set(x.files)==set(y.files)
            for key in x.files:np.testing.assert_array_equal(x[key],y[key])
    assert sha(a)==sha(b),f'replay differs: {a} {b}'
    return dict(reference=str(a),replay=str(b),sha256=sha(a),exact=True)


def validate(unit,phase):
    unit=Path(unit);rows=[]
    if phase=='build':
        replay=unit/'replay_end_to_end_recovery'
        for name in ('mesh.npz','region_1.npz','region_2.npz','region_3.npz'):
            rows.append(compare(unit/'assets/baseline'/name,replay/'assets/baseline'/name))
        for name in ('image.png','arrays.npz'):
            rows.append(compare(unit/f'renders/first/frame_000_{name}',replay/f'renders/first/frame_000_{name}'))
        p=json.loads((unit/'PROTOCOL.json').read_text())
        rows.append(compare(Path(p['previous_unit'])/'proxy/mesh.npz',replay/'raw_source/proxy/mesh.npz'))
        receipt=json.loads((unit/'logs/end_to_end_recovery.receipt.json').read_text())
        assert receipt['returncode']==0
        result=dict(utc=now(),status='PASS',exact_files=rows,seconds=receipt['seconds'],
                    source='actual original PLY -> 24 CPU source renders -> TSDF -> bounded refinement -> paths -> PNG',
                    initial_outer_exit=143,initial_child_exit='UNKNOWN',initial_failure_retained=True)
    elif phase=='export':
        for name in ('image.png','arrays.npz'):
            rows.append(compare(unit/f'viewer_smoke/view_0006/frame_000_{name}',unit/f'exported_reload/preview/frame_000_{name}'))
        result=dict(utc=now(),status='PASS',exact_files=rows,
                    source='actual HTTP export ZIP unpacked and rendered in a fresh CLI process after server shutdown')
    else:
        outputs=sorted((unit/'portable_relocated/portable_demo/runs').glob('preview_*'))
        assert len(outputs)==1
        for name in ('image.png','arrays.npz'):
            rows.append(compare(unit/f'renders/static_edited/frame_000_{name}',outputs[0]/f'frame_000_{name}'))
        result=dict(utc=now(),status='PASS',exact_files=rows,
                    source='archive extracted to a different path; documented ./run.sh preview run cold; no original PLY needed')
    js(unit/'metrics'/f'{phase.upper()}_REPLAY.json',result)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True)
    p.add_argument('phase',choices=['build','export','portable']);a=p.parse_args();validate(a.unit,a.phase)
