"""Finite straight ribbon visibility from actual planar scene triangles.

Round014 exact-duplicate repair; round013 source remains unchanged.
No reference geometry, masks or areas enter this module. Fragments are convex,
interior-disjoint polygons. Constant-depth restrictions are deliberate.
"""
import round014_common
import numpy as np
from PIL import Image
import core
from area_coverage import straight_endpoints, clip_axis

PLANAR_EPS=1e-9
SEPARATION=.006
AREA_EPS=1e-12

class UnsupportedGeometry(ValueError):
    def __init__(self,code):
        self.code=code
        super().__init__(code)

def signed_area(poly):
    if len(poly)<3:return 0.
    p=poly-poly[0]
    return float(.5*np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)))

def canonical(poly):
    p=np.asarray(poly,float).copy()
    if signed_area(p)<0:p=p[::-1]
    i=min(range(len(p)),key=lambda i:tuple(p[i]))
    return np.roll(p,-i,axis=0)

def exact_triangle_key(vertices):
    """Exact full 3D geometry identity; no tolerance or projected quantization."""
    return tuple(sorted(tuple(row) for row in vertices))

def halfplane(poly,a,b,inside=True):
    """CCW cutter: keep left for inside; split exactly without dilation."""
    if len(poly)==0:return np.empty((0,2))
    d=b-a
    def side(p):return float(d[0]*(p[1]-a[1])-d[1]*(p[0]-a[0]))
    out=[];prev=poly[-1];sp=side(prev);ip=sp>=0 if inside else sp<=0
    for cur in poly:
        sc=side(cur);ic=sc>=0 if inside else sc<=0
        if ip!=ic:out.append(prev+(cur-prev)*(sp/(sp-sc)))
        if ic:out.append(cur)
        prev,sp,ip=cur,sc,ic
    return np.asarray(out,float).reshape(-1,2)

def intersect(subject,cutter):
    p=subject.copy()
    for a,b in zip(cutter,np.roll(cutter,-1,axis=0)):
        p=halfplane(p,a,b)
        if len(p)<3:return np.empty((0,2))
    return p

def difference(subject,cutter):
    """Emit disjoint outside pieces; only inside remainder reaches next edge."""
    remainder=subject.copy();out=[]
    for a,b in zip(cutter,np.roll(cutter,-1,axis=0)):
        outside=halfplane(remainder,a,b,False)
        if len(outside)>=3 and abs(signed_area(outside))>0:out.append(outside)
        remainder=halfplane(remainder,a,b,True)
        if len(remainder)<3 or abs(signed_area(remainder))==0:break
    return out

def integrate(fragments,size):
    out=np.zeros((size,size))
    for polygon in fragments:
        lo=np.maximum(0,np.ceil(polygon.min(axis=0)-.5).astype(int))
        hi=np.minimum(size-1,np.floor(polygon.max(axis=0)+.5).astype(int))
        for y in range(lo[1],hi[1]+1):
            for x in range(lo[0],hi[0]+1):
                p=polygon-np.array([x,y])
                for axis,bound,less in [(0,-.5,False),(0,.5,True),(1,-.5,False),(1,.5,True)]:
                    p=clip_axis(p,axis,bound,less)
                out[y,x]+=abs(signed_area(p))
    return out

def clean(a):
    b=a.copy();b[b<=AREA_EPS]=0.;b[b>=1-AREA_EPS]=1.;return b

def render(mesh,owner_faces,path,c,ink=.8,scale=2,width=2.,tolerance=SEPARATION):
    if tolerance!=SEPARATION:raise UnsupportedGeometry('fixed_depth_separation_required')
    v=np.asarray(mesh['vertices'],float);f=np.asarray(mesh['faces']);owners=np.asarray(owner_faces)
    if v.ndim!=2 or v.shape[1]!=3 or not np.isfinite(v).all():raise UnsupportedGeometry('invalid_vertices')
    if f.ndim!=2 or f.shape[1]!=3 or f.dtype.kind not in 'iu' or np.any(f<0) or np.any(f>=len(v)):raise UnsupportedGeometry('invalid_faces')
    if owners.ndim!=1 or owners.dtype.kind not in 'iu' or not len(owners) or len(set(owners.tolist()))!=len(owners) or np.any(owners<0) or np.any(owners>=len(f)):raise UnsupportedGeometry('invalid_owners')
    if not np.isfinite(ink) or not 0<=ink<=1 or not np.isfinite(width) or width<=0:raise UnsupportedGeometry('invalid_style')
    size=c['size']
    if not isinstance(size,(int,np.integer)) or size<=0 or scale<1 or size%scale:raise UnsupportedGeometry('invalid_resolution')
    uv,z=core.project(v,c)
    if not np.isfinite(uv).all() or not np.isfinite(z).all() or np.any(z<=0):raise UnsupportedGeometry('nonpositive_scene_depth')
    tz=z[f]
    if np.any(np.ptp(tz,axis=1)>PLANAR_EPS):raise UnsupportedGeometry('nonfrontoparallel_triangle')
    owner_z=float(tz[owners[0],0])
    if np.max(abs(tz[owners]-owner_z))>PLANAR_EPS:raise UnsupportedGeometry('noncoplanar_owners')
    owner_ids=set(owners.tolist());foreground=[];owner_tri=[];seen_foreground=set()
    for i,tri in enumerate(uv[f]):
        tri=canonical(tri)
        if abs(signed_area(tri))<=1e-12:raise UnsupportedGeometry('degenerate_projected_triangle')
        if i in owner_ids:owner_tri.append(tri)
        else:
            delta=float(tz[i,0]-owner_z)
            if abs(delta)<=SEPARATION:raise UnsupportedGeometry('ambiguous_nonowner_depth')
            if delta<0:
                identity=exact_triangle_key(v[f[i]])
                if identity not in seen_foreground:
                    seen_foreground.add(identity)
                    foreground.append(tri)
    # Geometry-based ordering makes face index, winding and duplicate order inert.
    key=lambda tri:tuple(tri.ravel())
    owner_tri=sorted(owner_tri,key=key);foreground=sorted(foreground,key=key)
    p,pz=core.project(np.asarray(path,float),c)
    if not np.isfinite(pz).all() or np.any(pz<=0) or np.max(abs(pz-owner_z))>PLANAR_EPS:raise UnsupportedGeometry('path_depth')
    a,b=straight_endpoints(p);d=b-a;n=np.array([-d[1],d[0]])*(width/(2*np.linalg.norm(d)))
    ribbon=canonical(np.array([a+n,a-n,b-n,b+n]));owned=[]
    for i,tri in enumerate(owner_tri):
        poly=intersect(ribbon,tri);pieces=[poly] if len(poly)>=3 and abs(signed_area(poly))>0 else []
        for previous in owner_tri[:i]:pieces=[q for piece in pieces for q in difference(piece,previous)]
        owned.extend(pieces)
    visible=owned
    for tri in foreground:visible=[q for piece in visible for q in difference(piece,tri)]
    raw_r=integrate([ribbon],size);raw_o=integrate(owned,size);raw_v=integrate(visible,size)
    raw={'ribbon':raw_r,'owned':raw_o,'visible':raw_v,'occluded':raw_o-raw_v,'unsupported':raw_r-raw_o}
    maps={k:clean(v) for k,v in raw.items()};high=maps['visible']*ink
    quantized=np.uint8(np.clip(high,0,1)*255)
    final=np.asarray(Image.fromarray(quantized).resize((size//scale,size//scale),Image.Resampling.LANCZOS))
    return {**maps,**{'raw_'+k:v for k,v in raw.items()},'high':high,'quantized_uint8':quantized,'final_uint8':final,'projected_path':p,
            'fragment_counts':np.array([len(owned),len(visible)],np.int64)}
