"""Project immutable world curves; camera never changes their controls/topology."""
import numpy as np
import cv2
from .core import project,visibility

def samples(curve, spacing=.005):
    points=np.array(curve['points']); segments=[]
    for a,b in curve['edges']:
        n=max(2,int(np.ceil(np.linalg.norm(points[b]-points[a])/spacing))+1)
        segments.append(points[a]+np.linspace(0,1,n)[:,None]*(points[b]-points[a]))
    return segments

def compile_asset(asset):
    points=[];links=[];widths=[];point_curve=[];offset=0
    for ci,curve in enumerate(asset['curves']):
        for p in samples(curve):
            points.append(p);links.extend([[offset+j,offset+j+1] for j in range(len(p)-1)])
            widths.extend([curve['width']]*(len(p)-1));point_curve.extend([ci]*len(p));offset+=len(p)
    return dict(points=np.concatenate(points) if points else np.empty((0,3)),
                links=np.array(links,dtype=int).reshape(-1,2),widths=np.array(widths),
                point_curve=np.array(point_curve,dtype=int),ids=[c['id'] for c in asset['curves']])

def render_asset(asset,K,c2w,occluder,compiled=None):
    # Compile once in the video driver. Batched projection preserves the exact world samples.
    data=compile_asset(asset) if compiled is None else compiled
    mask=np.zeros(occluder.shape,np.uint8)
    uv,z=project(data['points'],K,c2w);label=visibility(uv,z,occluder)
    finite=np.isfinite(uv).all(1)&(z>0);ij=np.zeros((len(z),2),int);ij[finite]=np.rint(uv[finite]).astype(int)
    inside=finite&(ij[:,0]>=0)&(ij[:,0]<mask.shape[1])&(ij[:,1]>=0)&(ij[:,1]<mask.shape[0])
    counts={key:int(((label==key)&inside).sum()) for key in ['consistent','occluded','contradiction','unknown']}
    vis=inside&(label!='occluded');pairs=data['links'];keep=vis[pairs[:,0]]&vis[pairs[:,1]]
    for (a,b),width in zip(pairs[keep],data['widths'][keep]):
        thickness=max(1,int(round(K[0,0]*width/((z[a]+z[b])*.5))))
        cv2.line(mask,tuple(ij[a]),tuple(ij[b]),255,thickness,lineType=cv2.LINE_8)
    seen=np.bincount(data['point_curve'][vis],minlength=len(data['ids']))
    ids=[identity for identity,count in zip(data['ids'],seen) if count]
    return mask,dict(ids=ids,counts=counts,ink_fraction=float((mask>0).mean()))
