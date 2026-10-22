"""Check cold CLI queries and preserve interrupted-run bytes separately."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,csv,json
import numpy as np
from run_transfer_unit import load
from run_path_unit import read_npz


def audit(unit):
    p=load(unit);queries={}
    for scene,s in p['scenes'].items():
        folder=unit/f'query_{scene}'
        receipt=json.loads((folder/'RECEIPT.json').read_text())
        ps=read_npz(unit/'results'/scene/receipt['camera']['view']/'path_support.npz')
        anchors=read_npz(folder/'ALL_ANCHORS.npz')
        for k,v in anchors.items():np.testing.assert_array_equal(v,ps[k])
        with (folder/'path_original_ID_support.csv').open() as f:rows=list(csv.DictReader(f))
        assert len(rows)==len(ps['weight'])==receipt['rows']
        np.testing.assert_array_equal([int(r['source_index']) for r in rows],ps['source_index'])
        np.testing.assert_array_equal([float(r['alpha_T']) for r in rows],ps['weight'])
        queries[scene]=dict(all_original_IDs_and_weights_exact=True,all_anchor_arrays_exact=True,
            rows=len(rows),anchors=len(ps['state']),unknown_anchors=int(ps['unknown'].sum()))
    before=unit/'interrupted_lego_view_0';after=unit/'results/lego'/p['scenes']['lego']['cameras'][0]['view']
    files={};count=0
    for f in sorted(before.iterdir()):
        if f.suffix=='.npz':
            a=read_npz(f);b=read_npz(after/f.name);assert set(a)==set(b)
            for k,v in a.items():np.testing.assert_array_equal(v,b[k])
            count+=1
        elif f.suffix=='.png':assert sha(f)==sha(after/f.name)
        files[f.name]=dict(sha256=sha(f),bytes=f.stat().st_size)
    result=dict(utc=now(),queries=queries,interrupted_recovery=dict(
        first_attempt_runner_returncode=None,outer_batch_exit_code=143,retry_returncode=0,
        comparable_npz_files=count,all_comparable_arrays_exact=True,all_PNGs_exact=True,
        first_attempt_not_counted_as_success=True,original_files=files),audit_code_sha256=sha(__file__))
    js(unit/'DELIVERY_VALIDATION.json',result);print(json.dumps(result,default=runtime.json_default),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True);audit(ap.parse_args().unit)
