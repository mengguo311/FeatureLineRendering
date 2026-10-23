"""Post-result diagnosis of tiny nonzero far pixels; no render or parameter change."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,now
import numpy as np
from scipy import ndimage
from run_contour_unit import protocol
from run_hybrid import read_npz

p=protocol();records=[]
for v in (v for v in p['views'] if v['kind']!='build'):
    root=UNIT/v['kind']/v['camera']['view'];f=read_npz(root/'FRAME.npz');r=read_npz(root/'RASTER.npz')
    far=~ndimage.binary_dilation(f['regions']==4,iterations=2)
    delta=np.abs(f['outlined_matched']-f['hatch_raw']).sum(2)
    pixels=[]
    for y,x in np.argwhere(far&(delta>0)):
        rr=r['regions_hi'][2*y:2*y+2,2*x:2*x+2]
        cc=r['contour_hi'][2*y:2*y+2,2*x:2*x+2]
        pixels.append(dict(x=int(x),y=int(y),low_region=int(f['regions'][y,x]),raw_RGB_L1=float(delta[y,x]),
            high_regions=rr.tolist(),high_contour=cc.tolist(),contains_high_target=bool((rr==4).any()),
            contour_confined_to_high_target=bool(np.all(cc[rr!=4]==0))))
    records.append(dict(kind=v['kind'],view=v['camera']['view'],changed_far_pixels=len(pixels),pixels=pixels))
js(UNIT/'FAR_READBACK.json',dict(utc=now(),records=records,
    all_far_pixels_contain_target_subpixel=all(q['contains_high_target'] and q['contour_confined_to_high_target'] for r in records for q in r['pixels']),
    interpretation='High-resolution target contour survives resolve in pixels whose sampled low-resolution region4 mask has no nearby target. Fixed evaluation mask and measured far damage remain unchanged. This is not independent semantic ownership proof.'))
print([(r['view'],r['changed_far_pixels']) for r in records],flush=True)
