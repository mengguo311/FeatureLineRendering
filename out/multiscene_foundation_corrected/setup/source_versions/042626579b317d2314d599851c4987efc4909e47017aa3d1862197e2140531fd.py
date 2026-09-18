"""Compatibility graph on immutable 3D linelet centers (no geometric supervision).

Image support is an OFFLINE visibility-conditioned measurement. Hidden samples are
unevaluable, not negative examples. Image intersections never create 3D vertices.
"""
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import distance_transform_edt
import cv2
from .common import project


def geometry_graph(p,t,l,cfg):
    n=len(p); unit=float(np.median(l)); tree=cKDTree(p)
    dist,nb=tree.query(p,k=min(cfg['neighbors']+1,n),workers=1)
    pairs=np.sort(np.c_[np.repeat(np.arange(n),nb.shape[1]-1),nb[:,1:].ravel()],axis=1)
    pairs=np.unique(pairs,axis=0);a,b=pairs.T;delta=p[b]-p[a]
    length=np.linalg.norm(delta,axis=1);u=delta/np.maximum(length[:,None],1e-12)
    ci=np.abs(np.sum(t[a]*u,axis=1));cj=np.abs(np.sum(t[b]*u,axis=1))
    agreement=np.abs(np.sum(t[a]*t[b],axis=1))
    local=np.clip((l[a]+l[b])/2,.5*unit,2*unit)
    endpoint_gap=np.maximum(0,length-l[a]*ci-l[b]*cj)/local
    # Chords must stay in the union of existing linelet support balls. This does
    # not certify a surface; it prevents arbitrary empty-space gap filling.
    samples=p[a,None]+np.linspace(0,1,cfg['samples'])[None,:,None]*delta[:,None]
    sd,si=tree.query(samples.reshape(-1,3),workers=1)
    tube=(sd/np.clip(l[si],.5*unit,2*unit)).reshape(len(a),-1).max(1)
    reason=np.full(len(a),'allowed',dtype='<U24')
    reason[(ci<cfg['min_col'])|(cj<cfg['min_col'])]='parallel_or_sideways'
    reason[endpoint_gap>cfg['endpoint_gap']]='endpoint_gap'
    reason[tube>cfg['tube_radius']]='unsupported_chord'
    reason[(length>cfg['gap_units']*unit)|(length<1e-9)]='distance'
    allowed=reason=='allowed'
    return dict(pairs=pairs,allowed=allowed,reason=reason,length=length,local=local,
                gap=endpoint_gap,tube=tube,continuation=(ci+cj)/2,
                tangent_agreement=agreement,corner=agreement<np.cos(np.deg2rad(35)),unit=unit)


def edge_field(image):
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    edge=cv2.Canny(gray,50,150)>0
    dt,nearest=distance_transform_edt(~edge,return_indices=True)
    gx=cv2.Sobel(gray,cv2.CV_64F,1,0,ksize=3);gy=cv2.Sobel(gray,cv2.CV_64F,0,1,ksize=3)
    tangent=np.stack([-gy,gx],axis=-1);tangent/=np.maximum(np.linalg.norm(tangent,axis=-1,keepdims=True),1e-12)
    return dt,tangent[nearest[0],nearest[1]],edge


def visible_evidence(points,direction,cam,depth,alpha,field,cfg):
    uv,z=project(points,cam);uv2,_=project(points+direction*.001,cam)
    xy=np.round(uv).astype(int);inside=(z>0)&(xy[:,0]>=0)&(xy[:,0]<cam.W)&(xy[:,1]>=0)&(xy[:,1]<cam.H)
    x=np.clip(xy[:,0],0,cam.W-1);y=np.clip(xy[:,1],0,cam.H-1)
    # Match the runtime's 3x3 conservative z-min, with an explicit coverage mask.
    zmin=cv2.erode(np.nan_to_num(depth,posinf=1e9).astype('float32'),np.ones((3,3),np.uint8))
    visible=inside&(alpha[y,x]>=.5)&(z<=zmin[y,x]+.02*z)
    dt,tangent,_=field;v=uv2-uv;v/=np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1e-12)
    alignment=np.abs(np.sum(v*tangent[y,x],axis=1));distance=dt[y,x]
    support=np.exp(-.5*(distance/cfg['dt_px'])**2)*alignment
    support[~visible]=0
    return visible,support,uv,z,distance,alignment


def measure_view(p,pairs,cam,depth,alpha,field,cfg):
    a,b=pairs.T;delta=p[b]-p[a];samples=p[a,None]+np.linspace(0,1,cfg['samples'])[None,:,None]*delta[:,None]
    direction=np.repeat(delta,cfg['samples'],axis=0)
    vis,support,uv,z,dt,align=visible_evidence(samples.reshape(-1,3),direction,cam,depth,alpha,field,cfg)
    vis=vis.reshape(len(a),-1);support=support.reshape(len(a),-1)
    count=vis.sum(1);evaluated=count>=cfg['min_visible_samples']
    score=support.sum(1)/np.maximum(count,1);score[~evaluated]=0
    # A near-coincident projection at very different depths is evidence of layers,
    # not a junction. It is a geometric guard shared by all arms, not RGB evidence.
    uv=uv.reshape(len(a),-1,2);z=z.reshape(len(a),-1)
    depth_layer=(np.linalg.norm(uv[:,0]-uv[:,-1],axis=1)<cfg['layer_px']) & \
        (np.abs(z[:,0]-z[:,-1])>cfg['layer_rel']*np.minimum(z[:,0],z[:,-1]))
    length_px=np.linalg.norm(uv[:,-1]-uv[:,0],axis=1)
    return evaluated,score,depth_layer,length_px*vis.mean(1)


def whole_path_witness(edge_ids,evaluated,support,length_px,minimum_fraction=.3,threshold=.6):
    """Same-view support of an entire path, not a bag of unrelated edge votes."""
    e=np.asarray(edge_ids,int)
    if not len(e):return 0.,[],[]
    w=length_px[:,e]*evaluated[:,e];available=w.sum(1)
    fraction=(evaluated[:,e]).mean(1)
    quality=(w*support[:,e]).sum(1)/np.maximum(available,1e-12)
    eligible=(fraction>=minimum_fraction)&(available>0)
    witnesses=np.flatnonzero(eligible&(quality>=threshold))
    # A path hidden in all but one view cannot receive a multi-view path prize.
    score=float(quality[eligible].mean()*min(len(witnesses)/3,1)) if eligible.any() else 0.
    return score,witnesses.tolist(),quality.tolist()


def components(n,pairs):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    a,b=np.asarray(pairs).reshape(-1,2).T
    graph=coo_matrix((np.ones(len(a)*2),(np.r_[a,b],np.r_[b,a])),shape=(n,n))
    count,labels=connected_components(graph,directed=False)
    return int(count),np.bincount(labels)
