"""Read frozen science and replay one camera to a fresh unit-local folder.

This uses verified original-GS source/paper/S caches. The separate cold replay
receipt demonstrates the two actual original-GS renders; this CLI does not
pretend to rerender GS or produce native Gaussian ink.
"""
import os
import sys
from pathlib import Path
import argparse

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True)
    ap.add_argument('--kind',choices=['dev','arc'],default='dev');ap.add_argument('--index',type=int,default=1)
    ap.add_argument('--name',required=True);args=ap.parse_args()
    if '/' in args.name or args.name.startswith('.') or not args.name.startswith('replay_'):raise ValueError('fresh simple replay_ name required')
    unit=args.unit.resolve();allowed=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units')
    if unit.parent!=allowed:raise ValueError('v06 unit only')
    os.environ['V06_UNIT_DIR']=str(unit);sys.path.insert(0,str(unit/'source_snapshot'))
    import runtime
    import numpy as np
    from run_visibility_unit import protocol,match,asset,get_cache,fresh
    from visibility_intervals import compare_visibility
    from hybrid import compose
    from run_hybrid import read_npz,png,panel
    from runtime import js,sha,now
    p=protocol();m=match();v=[v for v in p['views'] if v['kind']==args.kind][args.index]
    a=get_cache(p,v);mesh,paths,meta=asset(p);r=compare_visibility(mesh,paths,meta['styles'],v['camera'])
    expected=read_npz(unit/args.kind/v['camera']['view']/'FRAME.npz');out=fresh(unit/args.name)
    images=[a['source'],a['paper']]
    for arm in ('legacy','interval'):
        np.testing.assert_array_equal(r['ink'][arm],expected[arm+'_ink'])
        image,alpha=compose(a['paper'],r['ink'][arm],a['support'],True,m['scales'][arm])
        np.testing.assert_array_equal(image,expected[arm+'_matched']);np.testing.assert_array_equal(alpha,expected[arm+'_matched_alpha'])
        png(out/(arm+'.png'),image);png(out/(arm+'_ink.png'),1-alpha);images.append(image)
    panel(out/'COMPARISON.png',images,['Original GS cache','Original-GS paper cache','Legacy / matched','Intervals / matched'],'Exact fixed-path cache replay; proxy ink, original-ID S',columns=2)
    js(out/'REPLAY.json',dict(utc=now(),camera=v['camera'],exact=True,GS_render_calls=0,cache=v['cache'],source_sha256=sha(__file__),scope=p['scope']))
    print('CACHE REPLAY EXACT',out,flush=True)

if __name__=='__main__':main()
