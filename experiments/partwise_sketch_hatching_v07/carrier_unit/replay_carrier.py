"""Actual A/C ink replay with immutable cached original-GS source/paper/S."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,sha,js
import argparse
from pathlib import Path
import numpy as np
from run_carrier import protocol,check_assets,compute,matched,npz,save,fresh,png
import json
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--view',default='orbit_241_24_5.3');args=ap.parse_args()
    p=protocol();check_assets();v=next(v for v in p['views'] if v['kind']=='dev' and v['camera']['view']==args.view)
    scales=json.loads((UNIT/'BUILD_MATCH.json').read_text())['scales'];f=matched(compute(v),scales);ref=npz(UNIT/'dev'/args.view/'FRAME.npz')
    for key in f:np.testing.assert_array_equal(f[key],ref[key],err_msg=key)
    out=fresh(Path(args.out));save(out/'FRAME.npz',**f)
    for key in ('A_linked_matched','C_linked_matched','C_ungated_matched'):png(out/(key+'.png'),f[key])
    js(out/'REPLAY_RECEIPT.json',dict(all_equal=True,view=args.view,arrays=len(f),actual_ink_rasterization=True,cold_original_GS=False,
        scope='Verified cached original-GS source/paper/S plus actual new A/C proxy raster; not a second cold GS bootstrap.',
        replay_source_sha256=sha(__file__)))
    print('ALL ARRAYS EXACT',len(f),flush=True)
if __name__=='__main__':main()
