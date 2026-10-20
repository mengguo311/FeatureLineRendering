"""Experimental straight finite ribbon pixel-square area, center-site visibility.

No oracle input. General bends/joins are intentionally outside this backend.
"""
import round011_common
import numpy as np
from PIL import Image
import core
import visibility_primitive as visibility

AREA_EPS=1e-12

def straight_endpoints(projected_path):
    p=np.asarray(projected_path,float)
    if p.ndim!=2 or p.shape[1]!=2 or len(p)<2 or not np.isfinite(p).all():
        raise ValueError('finite projected path (N>=2,2) required')
    if np.any(np.linalg.norm(np.diff(p,axis=0),axis=1)<=1e-12):
        raise ValueError('zero projected segment length')
    a,b=p[0].copy(),p[-1].copy()
    if tuple(a)>tuple(b): a,b=b,a;p=p[::-1]
    d=b-a;length=np.linalg.norm(d)
    if length<=1e-12:raise ValueError('zero projected endpoint length')
    q=p-a
    if np.max(abs(d[0]*q[:,1]-d[1]*q[:,0]))/length>1e-9:
        raise ValueError('only straight projected paths supported')
    along=q@d/length
    if np.any(np.diff(along)<-1e-9) or along.min()<-1e-9 or along.max()>length+1e-9:
        raise ValueError('backtracking projected path unsupported')
    return a,b

def clip_axis(poly,axis,bound,keep_less):
    if len(poly)==0:return poly
    output=[];prev=poly[-1];pi=prev[axis]<=bound if keep_less else prev[axis]>=bound
    for cur in poly:
        ci=cur[axis]<=bound if keep_less else cur[axis]>=bound
        if ci!=pi:
            t=(bound-prev[axis])/(cur[axis]-prev[axis]);hit=prev+t*(cur-prev);hit[axis]=bound;output.append(hit)
        if ci:output.append(cur)
        prev=cur;pi=ci
    return np.array(output,float).reshape(-1,2)

def ribbon_area(projected_path,size,width=2.):
    a,b=straight_endpoints(projected_path)
    if not np.isfinite(width) or width<=0:raise ValueError('positive finite width required')
    if not isinstance(size,(int,np.integer)) or size<=0:raise ValueError('positive integer size required')
    d=b-a;n=np.array([-d[1],d[0]])*(width/(2*np.linalg.norm(d)))
    polygon=np.array([a+n,a-n,b-n,b+n]);out=np.zeros((size,size))
    lo=np.maximum(0,np.ceil(polygon.min(axis=0)-.5).astype(int))
    hi=np.minimum(size-1,np.floor(polygon.max(axis=0)+.5).astype(int))
    for y in range(lo[1],hi[1]+1):
        for x in range(lo[0],hi[0]+1):
            poly=polygon-np.array([x,y])
            for axis,bound,less in [(0,-.5,False),(0,.5,True),(1,-.5,False),(1,.5,True)]:
                poly=clip_axis(poly,axis,bound,less)
            if len(poly)<3:continue
            area=.5*abs(np.sum(poly[:,0]*np.roll(poly[:,1],-1)-poly[:,1]*np.roll(poly[:,0],-1)))
            if area<=AREA_EPS:area=0.
            elif area>=1-AREA_EPS:area=1.
            out[y,x]=area
    return out

def render(mesh,owner_faces,path,c,ink=.8,scale=2,width=2.,tolerance=visibility.DEPTH_TOLERANCE):
    uv,z=core.project(path,c)
    if not np.isfinite(z).all() or np.any(z<=0):raise ValueError('positive finite endpoint optical depth required')
    coverage=ribbon_area(uv,c['size'],width);mask=coverage>0
    depth,parts=core.raster_surface(mesh,c);yy,xx=np.nonzero(mask)
    own,face=visibility.owner_depth(mesh,owner_faces,c,np.column_stack((xx,yy)))
    keep=visibility.visibility_gate(own,depth[yy,xx],tolerance)
    high=np.zeros(depth.shape);high[yy[keep],xx[keep]]=coverage[yy[keep],xx[keep]]*ink
    ownmap=np.full(depth.shape,np.inf);ownmap[yy,xx]=own
    facemap=np.full(depth.shape,-1,np.int32);facemap[yy,xx]=face
    gate=np.zeros(depth.shape,bool);gate[yy,xx]=keep
    quantized=np.uint8(np.clip(high,0,1)*255)
    final=np.asarray(Image.fromarray(quantized).resize((c['size']//scale,c['size']//scale),Image.Resampling.LANCZOS))
    return {'coverage':coverage,'footprint':coverage*ink,'owner_depth':ownmap,'owner_face':facemap,'scene_depth':depth,'scene_owner':parts,'gate':gate,'high':high,'quantized_uint8':quantized,'final_uint8':final,'projected_path':uv}
