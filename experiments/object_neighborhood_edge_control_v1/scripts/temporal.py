"""Evaluation-only GT-visible reprojection of task-A residuals along heldout path."""
import json
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import OUT,EXP,atomic_json,resource_guard,sha

def temporal(scene,method):
    import numpy as np
    from scipy.ndimage import map_coordinates,binary_erosion
    cfg=json.loads((EXP/'configs/pilot.json').read_text());size=cfg['resolution'];f=size/(2*np.tan(cfg['camera_angle_x']/2))
    frames=json.loads((EXP/'data/manifests/cameras.json').read_text())['splits']['path']
    path=OUT/'renders'/scene/method/'path';rows=[]
    for i in range(len(frames)-1):
        a=frames[i];b=frames[i+1]
        with np.load(OUT/'data'/scene/'path'/a['id']/'A_target.npz') as r:
            points=r['surface_points'];ids=r['instance'];coverage=r['coverage']
        with np.load(OUT/'data'/scene/'path'/b['id']/'A_target.npz') as r:
            nextid=r['instance'];nextdepth=r['depth_ray_parameter']
        c=np.array(b['transform_matrix']);c[:3,1:3]*=-1;w2c=np.linalg.inv(c)
        homogeneous=np.concatenate([points,np.ones((*points.shape[:2],1))],axis=-1)
        p=homogeneous@w2c.T;z=p[...,2];safe=np.maximum(z,1e-8)
        x=f*p[...,0]/safe+size/2-.5;y=f*p[...,1]/safe+size/2-.5
        id2=map_coordinates(nextid,[y,x],order=0,mode='constant',cval=0)
        depth2=map_coordinates(nextdepth,[y,x],order=1,mode='constant',cval=0)
        valid=(ids>0)&(ids==id2)&(coverage.max(-1)>.999)&(z>0)&(x>=1)&(x<size-2)&(y>=1)&(y<size-2)&(np.abs(z-depth2)<.02)
        valid &=binary_erosion(ids>0,iterations=2)
        ra=np.load(path/f'{i:04d}_linear.npz')['residual'];rb=np.load(path/f'{i+1:04d}_linear.npz')['residual']
        warped=np.stack([map_coordinates(rb[...,ch],[y,x],order=1,mode='constant',cval=0) for ch in range(3)],axis=-1)
        value=float(((ra[valid]-warped[valid])**2).mean()) if valid.any() else None
        rows.append({'from':a['id'],'to':b['id'],'valid_pixels':int(valid.sum()),'reprojected_residual_change_mse':value})
    result={'scene':scene,'method':method,'task':'A','scope':'36-frame heldout continuous arc, one pilot seed',
        'definition':'change in I_render-I_reference after GT-surface reprojection, jointly visible same instance only',
        'oracle_provenance':'analytic supersampled surface_points and depth, evaluator only',
        'mean':float(np.mean([r['reprojected_residual_change_mse'] for r in rows if r['reprojected_residual_change_mse'] is not None])),
        'rows':rows,'test_freeze_sha256':sha(EXP/'results/manifests/test_freeze.json')}
    atomic_json(EXP/f'results/tables/{scene}_{method}_temporal.json',result)
    return result

if __name__=='__main__':
    resource_guard(gpu=False)
    p=argparse.ArgumentParser();p.add_argument('scene');p.add_argument('method');a=p.parse_args();temporal(a.scene,a.method)
