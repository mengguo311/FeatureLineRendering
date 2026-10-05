"""Deterministic oracle target renderer. Geometry arrays are evaluator-only."""
import numpy as np
from pathlib import Path
from PIL import Image
from runtime import OUT, EXP, atomic_json, sha
from edge_profiles import linear_to_srgb

def camera(theta, elevation=5, radius=3.8):
    a,b=np.deg2rad([theta,elevation])
    eye=radius*np.array([np.sin(a)*np.cos(b),np.sin(b),np.cos(a)*np.cos(b)])
    back=eye/np.linalg.norm(eye);right=np.cross([0,1,0],back);right/=np.linalg.norm(right)
    up=np.cross(back,right)
    c=np.eye(4);c[:3,:3]=np.stack([right,up,back],axis=1);c[:3,3]=eye
    return c

def camera_splits(cfg):
    # All selected before images/models exist. Continuous [22,32] test arc is withheld.
    groups={'train':np.linspace(-28,18,24).tolist(),
            'val':[-26.7,-17.7,-8.7,.3,9.3,17.1],
            'test':[-25.5,-16.5,-7.5,1.5,10.5,16.5,22.,24.,26.,28.,30.,32.],
            'path':np.linspace(22.1,31.9,cfg['path_frames']).tolist()}
    return {g:[{'id':f'{g}_{i:03d}','theta_deg':float(t),
                 'elevation_deg':float(5+2*np.sin(np.deg2rad(t*3))),
                 'transform_matrix':camera(t,5+2*np.sin(np.deg2rad(t*3)),cfg['camera_radius']).tolist()}
               for i,t in enumerate(ts)] for g,ts in groups.items()}

def render_target(frame,scene,cfg,task='A'):
    n=cfg['resolution'];s=cfg['supersample'];h=n*s
    c=np.asarray(frame['transform_matrix']);f=n/(2*np.tan(cfg['camera_angle_x']/2))
    y,x=np.mgrid[:h,:h];dx=((x+.5)/s-n/2)/f;dy=-((y+.5)/s-n/2)/f
    ray=np.stack([dx,dy,-np.ones_like(dx)],axis=-1)@c[:3,:3].T;eye=c[:3,3]
    instance=np.zeros((h,h),np.uint8);depth=np.full((h,h),np.inf);point=np.zeros((h,h,3))
    surfaces=[(1,0.,-1,0.,-.8,.8),(2,0.,0.,1.,-.8,.8)]
    if scene=='far_background':surfaces=[(2,-3.,-4,4,-3,3),(1,0.,-.85,0.,-.8,.8)]
    for label,z,x0,x1,y0,y1 in surfaces:
        d=(z-eye[2])/ray[...,2];p=eye+d[...,None]*ray
        valid=(d>0)&(d<depth)&(p[...,0]>=x0)&(p[...,0]<x1)&(p[...,1]>=y0)&(p[...,1]<y1)
        instance[valid]=label;depth[valid]=d[valid];point[valid]=p[valid]
    a=np.array([.08,.16,.55]);b=np.array([.72,.25,.06])
    if scene=='panels_low':a=np.array([.4,.4,.4]);b=np.array([.401,.4,.4])
    color=np.zeros((h,h,3),np.float32);color[instance==1]=a;color[instance==2]=b
    if task=='B' and scene!='far_background':
        t=np.clip(point[...,0]/.1,-50,50);m=.5+.5*np.sin(4*np.pi*point[...,1])
        blend=1/(1+np.exp(-t));d=(b-a)*m[...,None]
        cfield=(a+b)/2+(blend-.5)[...,None]*d
        color[instance>0]=cfield[instance>0]
    def avg(v):return v.reshape(n,s,n,s,*v.shape[2:]).mean(axis=(1,3))
    rgb=avg(color).astype(np.float32)
    coverage=np.stack([avg((instance==i).astype(float)) for i in (0,1,2)],axis=-1).astype(np.float32)
    ids=np.argmax(coverage,axis=-1).astype(np.uint8)
    valid=np.isfinite(depth);safe_depth=np.where(valid,depth,0)
    z=avg(safe_depth)/np.maximum(avg(valid.astype(float)),1e-8)
    normals=np.zeros((n,n,3),np.float32);normals[ids>0,2]=1
    return {'rgb':rgb,'instance':ids,'coverage':coverage,'depth_ray_parameter':z.astype(np.float32),
            'normal':normals,'surface_points':avg(point).astype(np.float32)}

