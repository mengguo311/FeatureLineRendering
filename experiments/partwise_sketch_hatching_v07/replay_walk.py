"""Rerasterize saved A/B paths using verified GS layers, into an explicit new directory.

This is a cached-GS / actual-new-ink replay. The separate portable CLI performs
full cold original-GS replay; this command does not pretend to rerender GS.
"""
import runtime
from runtime import ACTIVE_UNIT as UNIT,sha,js,output_guard
import argparse,json
from pathlib import Path
import numpy as np
from run_unit import protocol,check_assets,compute,matched,png,save,npz
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--view',default='orbit_241_24_5.3');args=ap.parse_args()
    out=output_guard(args.out);out.mkdir(parents=True,exist_ok=False)
    p=protocol();check_assets();v=next(v for v in p['views'] if v['kind']=='dev' and v['camera']['view']==args.view)
    inputs=json.loads((UNIT/'INPUT_LOCK.json').read_text())['files'];assert sha(v['cache'])==inputs[v['cache']]
    scales=json.loads((UNIT/'BUILD_MATCH.json').read_text())['scales'];f=matched(compute(v),scales);ref=npz(UNIT/'dev'/args.view/'FRAME.npz')
    errors={key:float(np.max(np.abs(value-ref[key]))) for key,value in f.items()};assert max(errors.values())==0
    save(out/'FRAME.npz',**f)
    for key in ('source','paper','A_linked_matched','B_linked_matched','B_ungated_matched'):png(out/(key+'.png'),f[key])
    js(out/'REPLAY_RECEIPT.json',dict(scope='Verified cached original GS source/paper/S; saved A/B paths actually rerasterized; not cold GS',
       cache=v['cache'],cache_sha256=sha(v['cache']),array_max_errors=errors,all_equal=True,source_sha256=sha(__file__)))
    print(json.dumps(errors),flush=True)
if __name__=='__main__':main()
