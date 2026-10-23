"""Cold original-GS + fixed proxy-path replay at one frozen arc camera."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha
import argparse
import numpy as np
from run_layer_ablation import protocol,match,asset,actual_source,fresh
from layer_ablation import render_pair
from hybrid import compose
from run_hybrid import read_npz,png

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--index',type=int,default=2);ap.add_argument('--name',default='cold_replay_001');args=ap.parse_args()
    if '/' in args.name or args.name.startswith('.'):raise ValueError('simple new directory name required')
    p=protocol();m=match();c=p['arc_cameras'][args.index];out=fresh(UNIT/args.name)
    a,provenance=actual_source(p,c,out);mesh,paths,meta=asset(p);pair,_=render_pair(mesh,paths,meta,c)
    expected=read_npz(UNIT/'arc'/c['view']/'FRAME.npz');checks={}
    for key in ('source','paper','support'):
        np.testing.assert_array_equal(a[key],expected[key]);checks[key]=True
    for arm in ('cross','base'):
        np.testing.assert_array_equal(pair[arm],expected[arm+'_ink'])
        image,alpha=compose(a['paper'],pair[arm],a['support'],True,m['scales'][arm],p['ink_color'])
        np.testing.assert_array_equal(image,expected[arm+'_matched']);np.testing.assert_array_equal(alpha,expected[arm+'_matched_alpha'])
        checks[arm+'_ink_and_hybrid_and_alpha']=True;png(out/(arm+'_matched.png'),image)
    js(out/'REPLAY.json',dict(camera=c,exact=checks,provenance=provenance,source_script_sha256=sha(__file__)))
    print('COLD REPLAY EXACT',c['view'],checks,flush=True)

if __name__=='__main__':main()
