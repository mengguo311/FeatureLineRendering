"""Describe fixed-mask locality residuals; do not change the original scores."""
import runtime
from runtime import js,now
import numpy as np
from scipy.ndimage import binary_dilation,binary_erosion
from unit019_run import U,protocol
from demo import load_asset
from geometry import ray_surface,orbit_camera

def main():
    p=protocol();mesh,_,_=load_asset(U/'assets/refined');records=[]
    for i,values in enumerate(p['static_camera_values']):
        with np.load(U/f'renders/refined/frame_{i:03d}_arrays.npz') as z:a={k:z[k] for k in z.files}
        with np.load(U/f'renders/style_probe/frame_{i:03d}_arrays.npz') as z:b={k:z[k] for k in z.files}
        mask=a['regions']==2;band=binary_dilation(mask,iterations=2)&~binary_erosion(mask,iterations=2)
        far=(a['regions']>0)&~mask&~band
        pixels=np.argwhere(far&(np.abs(a['image']-b['image'])>0))
        if not len(pixels):continue
        _,_,sub,_=ray_surface(mesh,orbit_camera(**values),2)
        for y,x in pixels:
            labels=sub[2*y:2*y+2,2*x:2*x+2]
            records.append(dict(camera=values,pixel_yx=[int(y),int(x)],saved_sample_label=int(a['regions'][y,x]),
                four_AA_labels=labels.tolist(),target_AA_samples=int((labels==2).sum()),
                image_before=float(a['image'][y,x]),image_after=float(b['image'][y,x]),
                target_layer_before=float(a['layer_2'][y,x]),target_layer_after=float(b['layer_2'][y,x])))
    js(U/'metrics/LOCALITY_RESIDUAL.json',dict(utc=now(),pixels=records,
        unchanged_scores='Original fixed2px center-sampled mask scores remain authoritative; this same-proxy AA diagnosis does not certify independent semantics.'))
    print(records)

if __name__=='__main__':main()
