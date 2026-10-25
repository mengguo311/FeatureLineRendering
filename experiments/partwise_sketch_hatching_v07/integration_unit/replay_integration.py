"""Replay saved A/B/D through actual rasterization, with verified cached GS layers."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,sha,js
from run_integration import protocol,check_assets,compute,matched,npz,save,fresh,png
from pathlib import Path
import argparse,json
import numpy as np

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--view',default='orbit_241_24_5.3');a=ap.parse_args()
    p=protocol();check_assets();v=next(v for v in p['views'] if v['kind']=='dev' and v['camera']['view']==a.view)
    scales=json.loads((UNIT/'BUILD_MATCH.json').read_text())['scales'];f=matched(compute(v,rerender_all=True),scales);ref=npz(UNIT/'dev'/a.view/'FRAME.npz')
    for key in f:np.testing.assert_array_equal(f[key],ref[key],err_msg=key)
    out=fresh(Path(a.out));save(out/'FRAME.npz',**f)
    for key in ('A_linked_matched','B_linked_matched','D_linked_matched'):png(out/(key+'.png'),f[key])
    receipt=dict(all_equal=True,view=a.view,arrays=len(f),actual_ink_rasterization=True,all_three_arms_rerasterized=True,cold_original_GS=False,
        scope='Hash-fixed cached original-GS layers plus actual A/B/D proxy ink; not a repeat cold GS bootstrap.',source_sha256=sha(__file__))
    js(out/'REPLAY_RECEIPT.json',receipt);print(json.dumps(receipt),flush=True)

if __name__=='__main__':main()
