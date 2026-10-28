"""Exact-camera cache contract for the frozen elevation experiment."""
import runtime
import numpy as np
from geometry import orbit_camera

def validate_cache(camera,saved_camera,arrays):
    for key in ('width','height','fx','fy','cx','cy','extrinsic'):
        if not np.array_equal(camera[key],saved_camera[key]):raise ValueError('cache camera mismatch: '+key)
    h,w=camera['height'],camera['width']
    for key,shape in [('source',(h,w,3)),('paper',(h,w,3)),('support',(h,w))]:
        a=arrays[key]
        if a.shape!=shape or not np.isfinite(a).all():raise ValueError('invalid cache array: '+key)

def elevation_plan(previous):
    old={r['key']:r['camera'] for r in previous};rows=[]
    specs=[('BUILD','BUILD',151,36,None,'BUILD'),('BACK','000',196,36,None,'000')]
    specs += [(f'{i:03d}',f'{24+i:03d}',241,24+3*i,i,'024' if i==0 else ('HIGH' if i==12 else None)) for i in range(13)]
    for key,prior,az,el,index,reference in specs:
        expected=orbit_camera(az,el,5.1,384);c=old[prior]
        for field in ('width','height','fx','fy','cx','cy','extrinsic'):
            if not np.array_equal(c[field],expected[field]):raise ValueError('unexpected planned camera: '+prior)
        row=dict(key=key,prior_key=prior,camera=c,azimuth=az,elevation=el,h1_reference=reference,
                 role='frozen elevation evaluation; exposed camera' if index is not None else 'static fidelity check')
        if index is not None:row['index']=index
        rows.append(row)
    return rows
