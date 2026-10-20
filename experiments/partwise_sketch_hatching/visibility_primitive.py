"""Visibility-only finite owner-patch primitive; no analytic oracle inputs.

Not integrated into the lamp renderer. The inherited deposition and even width
stencil are intentionally retained. Owner IDs designate faces, not part labels.
"""
import round006_common
import numpy as np
from scipy import ndimage
from PIL import Image
import core

DEPTH_TOLERANCE = .006
GEOMETRY_EPS = 1e-9


def visibility_gate(owner_z, scene_z, tolerance=DEPTH_TOLERANCE):
    owner_z=np.asarray(owner_z);scene_z=np.asarray(scene_z)
    finite=np.isfinite(owner_z)&np.isfinite(scene_z)&(owner_z>0)&(scene_z>0)
    result=np.zeros(np.broadcast_shapes(owner_z.shape,scene_z.shape),bool)
    result[finite]=owner_z[finite]<=scene_z[finite]+tolerance
    return result


def owner_depth(mesh, owner_faces, c, uv):
    """Query explicit finite triangles at actual sample rays; refuse multivalued ownership.

    Optical-z rays are unnormalized. Shared triangle-edge hits within numerical
    epsilon are a single surface hit. Different positive depths are ambiguous.
    No use of the analytic plane coefficients or evaluator depth arrays.
    """
    ids=np.asarray(owner_faces,dtype=int)
    if ids.ndim!=1 or len(ids)==0 or len(set(ids.tolist()))!=len(ids):
        raise ValueError('owner faces must be a nonempty unique explicit list')
    if np.any(ids<0) or np.any(ids>=len(mesh['tri'])):raise ValueError('invalid owner face ID')
    uv=np.asarray(uv,float)
    ray=np.column_stack(((uv-c['center'])/c['focal'],np.ones(len(uv))))@c['R']
    best=np.full(len(uv),np.inf);face=np.full(len(uv),-1,np.int32)
    for fi in sorted(ids):
        tri=mesh['tri'][fi];e1=tri[1]-tri[0];e2=tri[2]-tri[0]
        h=np.cross(ray,e2);det=h@e1
        usable=abs(det)>1e-12
        inv=np.divide(1.,det,out=np.zeros(len(det)),where=usable)
        s=c['eye']-tri[0];u=(h@s)*inv;q=np.cross(s,e1)
        v=(ray@q)*inv;z=float(e2@q)*inv
        hit=usable&(u>=-GEOMETRY_EPS)&(v>=-GEOMETRY_EPS)&(u+v<=1+GEOMETRY_EPS)&np.isfinite(z)&(z>0)
        both=hit&np.isfinite(best)
        if np.any(abs(z[both]-best[both])>GEOMETRY_EPS):
            raise ValueError('ambiguous owner patch: multiple distinct depths at a raster site')
        first=hit&~np.isfinite(best);face[first]=fi
        best[hit]=np.minimum(best[hit],z[hit])
    return best,face


def render(mesh, owner_faces, path, c, ink=.8, scale=2, width=2, dense_step=.45, tolerance=DEPTH_TOLERANCE):
    depth,parts=core.raster_surface(mesh,c)
    points=core.dense_path(path,c,dense_step);uv,z=core.project(points,c)
    pixels=np.rint(uv).astype(int);size=c['size']
    inside=(z>0)&(pixels[:,0]>=0)&(pixels[:,0]<size)&(pixels[:,1]>=0)&(pixels[:,1]<size)
    pre=np.zeros(depth.shape);p=pixels[inside]
    np.maximum.at(pre,(p[:,1],p[:,0]),ink)
    footprint=ndimage.maximum_filter(pre,size=width)
    # Visibility is evaluated AFTER the unchanged expansion, at its exact sites.
    yy,xx=np.nonzero(footprint>0);query=np.column_stack((xx,yy))
    own,face=owner_depth(mesh,owner_faces,c,query)
    keep=visibility_gate(own,depth[yy,xx],tolerance)
    high=np.zeros(depth.shape);high[yy[keep],xx[keep]]=footprint[yy[keep],xx[keep]]
    ownmap=np.full(depth.shape,np.inf);ownmap[yy,xx]=own
    facemap=np.full(depth.shape,-1,np.int32);facemap[yy,xx]=face
    gate=np.zeros(depth.shape,bool);gate[yy,xx]=keep
    quantized=np.uint8(np.clip(high,0,1)*255)
    final=np.asarray(Image.fromarray(quantized).resize((size//scale,size//scale),Image.Resampling.LANCZOS))
    return {'pre_z':pre,'footprint':footprint,'owner_depth':ownmap,'owner_face':facemap,
            'scene_depth':depth,'scene_owner':parts,'gate':gate,'high':high,
            'quantized_uint8':quantized,'final_uint8':final,'point_xyz':points,
            'point_uv':uv,'point_z':z,'point_pixel':pixels,'point_inside':inside}
