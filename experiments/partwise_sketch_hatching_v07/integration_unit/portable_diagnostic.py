"""Package-only cached-GS / actual-proxy-ink replay. No cold GS claim."""
import runtime
from pathlib import Path
import argparse,json
import numpy as np
from PIL import Image
from geometry import mesh_data
from fixed_render import _coverage
from hybrid import compose
PACKAGE=Path(__file__).resolve().parent.parent

def npz(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);ap.add_argument('--view',default='orbit_241_24_5.3');args=ap.parse_args()
    manifest=json.loads((PACKAGE/'MANIFEST.json').read_text())
    for name,h in manifest['files'].items():
        if runtime.sha(PACKAGE/name)!=h:raise ValueError('package hash changed: '+name)
    cameras=json.loads((PACKAGE/'data/CAMERAS.json').read_text());c=cameras[args.view]
    reference=npz(PACKAGE/'data/frames'/(args.view+'.npz'));t=npz(PACKAGE/'data/TARGET.npz')
    meshes=[mesh_data(t['vertices'],t['faces'],t[k]) for k in ('old_face_regions','face_regions')]
    meta=json.loads((PACKAGE/'data/asset.json').read_text());scales=json.loads((PACKAGE/'data/BUILD_MATCH.json').read_text())['scales']
    f={k:reference[k].copy() for k in ('source','paper','support','regions','old_regions')}
    for arm in ('A','B','D'):
        rasters=[]
        for part,m in zip(('old','added'),meshes):
            paths=npz(PACKAGE/'data/paths'/(arm+'_'+part+'.npz'))
            rasters.append(_coverage(m,{4:paths},meta['styles'],c,2,occluder=m))
        strength=meta['styles']['4'].get('ink_strength',.8)
        high=np.maximum(*[np.maximum.reduce(list(r['coverage'][4].values())).astype(np.float32)*strength for r in rasters])
        f[arm+'_preS']=high.reshape(c['height'],2,c['width'],2).mean((1,3))
        for key,r in zip(('old_regions','regions'),rasters):np.testing.assert_array_equal(r['regions'],f[key])
        f[arm+'_fragment_diagnostics']=np.asarray([[r['diagnostics']['4'][k] for k in ('covered_fragments','accepted_fragments','region_rejected','depth_rejected')] for r in rasters],np.int64)
        for link in ('linked','ungated'):
            for mode,factor in [('natural',1.),('matched',scales[arm+'_'+link])]:
                key=arm+'_'+link+'_'+mode
                f[key],f[key+'_alpha']=compose(f['paper'],f[arm+'_preS'],f['support'],link=='linked',factor)
    for key in f:np.testing.assert_array_equal(f[key],reference[key],err_msg=key)
    out=runtime.configure_output(args.out)
    np.savez_compressed(runtime.output_guard(out/'FRAME.npz'),**f)
    for key in ('source','paper','A_linked_matched','B_linked_matched','D_linked_matched'):
        Image.fromarray(np.uint8(np.clip(f[key],0,1)*255+.5)).save(runtime.output_guard(out/(key+'.png')))
    receipt=dict(view=args.view,all_equal=True,arrays=len(f),package_hashes_checked=len(manifest['files']),actual_ink_rasterization=True,cold_original_GS=False,
        scope='Package-local proxy paths on original O with cached original-GS source/paper/S; no external historical output dependencies for this replay; no per-path Gaussian ownership or cross-platform certification.')
    runtime.js(out/'REPLAY_RECEIPT.json',receipt);print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
