"""Offline TRAIN-only evidence for fixed 3D bridges; occlusion is not absence.

This module accepts explicit cameras/images/depth arrays, never opens data files.
The entry point enforces splits. Final rendering does not call this module.
"""
import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt, minimum_filter
from .common import project


DEFAULTS=dict(sigma=1.2,canny=[50,120],dt_px=2.,tangent_cos=.75,
              interior_fraction=.2,min_visible_samples=8,min_visible_fraction=.3,
              min_projected_length_px=2.,joint_support_fraction=.7,
              min_fit_views=3,min_view_support_rate=.6,min_camera_angle_deg=10.,
              depth_tolerance=.02,max_front_fraction=.1,max_depth_jump=.05)


def edge_field(bgr,cfg=None):
    cfg=DEFAULTS if cfg is None else cfg
    gray=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY)
    blur=cv2.GaussianBlur(gray,(0,0),cfg['sigma'])
    edge=cv2.Canny(blur,*cfg['canny'])>0
    if not edge.any():
        return np.full(gray.shape,1e6),np.zeros((*gray.shape,2))
    dt,indices=distance_transform_edt(~edge,return_indices=True)
    gx=cv2.Sobel(blur,cv2.CV_64F,1,0,ksize=3);gy=cv2.Sobel(blur,cv2.CV_64F,0,1,ksize=3)
    tangent=np.stack([-gy,gx],axis=-1)
    tangent/=np.maximum(np.linalg.norm(tangent,axis=-1,keepdims=True),1e-12)
    return dt,tangent[indices[0],indices[1]]


def depth_states(points,cam,depth,alpha,cfg=None):
    """0 out of view; 1 visible/supportable; 2 occluded; 3 foreground mismatch.

    Visibility uses the same 3x3 min and 2% tolerance as the existing renderer.
    In-front/background points are not accepted as surface support. They are a
    geometric veto in image scoring; hidden samples are neutral.
    """
    cfg=DEFAULTS if cfg is None else cfg
    uv,z=project(points,cam);xy=np.round(uv).astype(int)
    inside=(z>0)&(xy[:,0]>=0)&(xy[:,0]<cam.W)&(xy[:,1]>=0)&(xy[:,1]<cam.H)
    dmin=minimum_filter(np.nan_to_num(depth,posinf=1e9),size=3,mode='constant',cval=1e9)
    state=np.zeros(len(points),np.int8);sampled=np.full(len(points),np.nan)
    ii=np.flatnonzero(inside);x,y=xy[ii].T;d=dmin[y,x];sampled[ii]=d
    hidden=z[ii]>d+cfg['depth_tolerance']*z[ii]
    unsupported=(d>=1e8)|(alpha[y,x]<.2)|(z[ii]<d-cfg['depth_tolerance']*z[ii])
    state[ii]=np.where(hidden,2,np.where(unsupported,3,1))
    return state,uv,z,sampled


def view_score(points,cam,depth,alpha,dt,tangent,cfg=None):
    cfg=DEFAULTS if cfg is None else cfg
    state,uv,z,sd=depth_states(points,cam,depth,alpha,cfg)
    n=len(points);trim=int(np.ceil(n*cfg['interior_fraction']))
    middle=np.zeros(n,bool);middle[trim:n-trim]=True
    visible=middle&(state==1);nvis=int(visible.sum());nin=int(middle.sum())
    front=float(np.mean(state[middle]==3))
    length=float(np.linalg.norm(np.diff(uv,axis=0),axis=1).sum())
    row=dict(visible_samples=nvis,interior_samples=nin,occluded_samples=int(np.sum(middle&(state==2))),
        unsupported_samples=int(np.sum(middle&(state==3))),out_of_view_samples=int(np.sum(middle&(state==0))),
        front_fraction=front,projected_length_px=length,qualified=False,passed=False,
        dt_median=None,tangent_mean=None,joint_support_fraction=None,reason='insufficient_visible_support')
    # Only a jump between two actually visible neighboring samples is a depth
    # veto. An intervening hidden run must not be mislabeled a negative edge.
    adjacent=(state[:-1]==1)&(state[1:]==1)
    relative=np.abs(np.diff(sd))/np.maximum(np.minimum(z[:-1],z[1:]),1e-9)
    crossing=bool(np.any(adjacent&(relative>cfg['max_depth_jump'])))
    row['cross_depth_rejected']=crossing
    if front>cfg['max_front_fraction'] or crossing:
        row['reason']='cross_depth_or_background';return row
    if nvis<cfg['min_visible_samples'] or nvis/max(nin,1)<cfg['min_visible_fraction'] or length<cfg['min_projected_length_px']:
        return row
    xy=np.round(uv[visible]).astype(int);x,y=xy.T
    direction=np.gradient(uv,axis=0)[visible]
    direction/=np.maximum(np.linalg.norm(direction,axis=1,keepdims=True),1e-12)
    distance=dt[y,x];alignment=np.abs(np.sum(direction*tangent[y,x],axis=1))
    joint=float(np.mean((distance<=cfg['dt_px'])&(alignment>=cfg['tangent_cos'])))
    passed=joint>=cfg['joint_support_fraction']
    row.update(qualified=True,passed=passed,dt_median=float(np.median(distance)),tangent_mean=float(alignment.mean()),
        joint_support_fraction=joint,reason='visible_edge_support' if passed else 'visible_edge_contradiction')
    return row


def aggregate(rows,camera_centers,center,cfg=None):
    cfg=DEFAULTS if cfg is None else cfg
    qualified=[i for i,r in enumerate(rows) if r['qualified']]
    supported=[i for i in qualified if rows[i]['passed']]
    veto=[i for i,r in enumerate(rows) if r['reason']=='cross_depth_or_background']
    # Out-of-view/occluded/too-short views do not enter the support-rate denominator.
    rate=len(supported)/max(len(qualified),1)
    angle=0.
    if len(supported)>1:
        rays=np.asarray(camera_centers,dtype=float)[supported]-np.asarray(center,dtype=float)
        rays/=np.maximum(np.linalg.norm(rays,axis=1,keepdims=True),1e-12)
        angle=float(np.rad2deg(np.arccos(np.clip(rays@rays.T,-1,1))).max())
    reason='accepted'
    if veto:reason='cross_depth_or_background'
    elif len(supported)<cfg['min_fit_views']:reason='too_few_supported_views'
    elif rate<cfg['min_view_support_rate']:reason='visible_edge_contradiction'
    elif angle<cfg['min_camera_angle_deg']:reason='insufficient_camera_diversity'
    score=float(np.mean([rows[i]['joint_support_fraction'] for i in supported]))*rate if supported else 0.
    return dict(accepted=reason=='accepted',reason=reason,qualified_views=len(qualified),supported_views=len(supported),
        support_rate=rate,max_camera_angle_deg=angle,geometry_veto_views=veto,
        image_score=score if reason=='accepted' else 0.)
