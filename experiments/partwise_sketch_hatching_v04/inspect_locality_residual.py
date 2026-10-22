"""Describe retained strict-locality residual pixels without changing scores or masks."""
import runtime
from runtime import js,now
from pathlib import Path
import argparse,json
import numpy as np
from demo import load_asset
from geometry import ray_surface,resize_camera

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);u=p.parse_args().unit
    protocol=json.loads((u/'PROTOCOL.json').read_text())
    validation=json.loads((u/'metrics/VALIDATION.json').read_text())
    mesh,_,_=load_asset(u/'assets/baseline');rows=[]
    for i,row in enumerate(validation['static']):
        if not row['far_changed_pixel_yx']:continue
        _,_,labels,_=ray_surface(mesh,resize_camera(protocol['static_cameras'][i],512),2)
        with np.load(u/f'renders/static_baseline/frame_{i:03d}_arrays.npz') as b,np.load(u/f'renders/static_edited/frame_{i:03d}_arrays.npz') as e:
            for y,x in row['far_changed_pixel_yx']:
                sub=labels[2*y:2*y+2,2*x:2*x+2]
                rows.append(dict(view=row['view'],pixel_yx=[y,x],saved_center_label=int(b['regions'][y,x]),
                    four_subpixel_labels=sub.tolist(),target_subpixel_count=int((sub==2).sum()),
                    image_before=float(b['image'][y,x]),image_after=float(e['image'][y,x]),
                    layers_before={str(k):float(b[f'layer_{k}'][y,x]) for k in (1,2,3)},
                    layers_after={str(k):float(e[f'layer_{k}'][y,x]) for k in (1,2,3)}))
    js(u/'metrics/LOCALITY_RESIDUAL_DIAGNOSTIC.json',dict(utc=now(),pixels=rows,
        scope='Same proxy reraycast at original 2x AA samples. Descriptive diagnosis only; original center-label scores and fixed 2px band remain unchanged. Not independent semantic truth.'))
    print(json.dumps(rows))
