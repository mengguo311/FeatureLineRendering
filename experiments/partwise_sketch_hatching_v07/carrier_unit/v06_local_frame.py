"""BUILD-only macroscopic tangent frame; fixed source geometry and slicing phase.

Normal signs use dyads. Position moments integrate each triangle uniformly,
so triangulation density does not substitute for surface area. No camera fit.
"""
import runtime
import numpy as np
from hatching import generate_layers,visibility_masks
from target_completion import extend_paths

def canonical(v):
    v=np.asarray(v,float)
    return -v if v[np.argmax(np.abs(v))]<0 else v

def face_areas(mesh):
    tri=mesh['tri']
    return .5*np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)

def fit_frame(mesh,face_ids):
    ids=np.unique(np.asarray(face_ids,np.int64));areas=face_areas(mesh)
    if len(ids)==0 or (ids<0).any() or (ids>=len(areas)).any():raise ValueError('nonempty valid BUILD faces required')
    w=areas[ids];tri=mesh['tri'][ids];normal=mesh['normals'][ids]
    if not np.isfinite(tri).all() or w.sum()<=1e-12:raise ValueError('degenerate BUILD surface')
    w=w/w.sum();scatter=np.einsum('n,ni,nj->ij',w,normal,normal)
    eig,vec=np.linalg.eigh(scatter)
    if eig[-1]-eig[-2]<=1e-6*max(eig[-1],1e-12):raise ValueError('no unique dominant normal; no frame search allowed')
    n=canonical(vec[:,-1]);s=tri.sum(1);center=np.einsum('n,ni->i',w,s/3)
    second=np.einsum('n,nij->ij',w,(np.einsum('nki,nkj->nij',tri,tri)+np.einsum('ni,nj->nij',s,s))/12)
    covariance=second-np.outer(center,center);projector=np.eye(3)-np.outer(n,n)
    val,axes=np.linalg.eigh(projector@covariance@projector)
    fallback=val[-1]-val[-2]<=1e-6*max(val[-1],1e-12)
    u=projector[:,np.argmax(np.diag(projector))] if fallback else projector@axes[:,-1]
    if np.linalg.norm(u)<=1e-12:raise ValueError('degenerate tangent axis')
    u=canonical(u/np.linalg.norm(u));v=np.cross(n,u);v/=np.linalg.norm(v)
    return dict(basis=np.stack([u,v]).tolist(),normal=n.tolist(),normal_eigenvalues=eig.tolist(),
        tangent_eigenvalues=val.tolist(),tangent_axis_fallback=bool(fallback),visible_face_count=len(ids),
        visible_area=float(areas[ids].sum()),centroid_diagnostic_only=center.tolist(),
        slicing_origin=[0.,0.,0.],sign_rule='largest absolute component positive for normal and long axis; v=n cross u',
        degeneracy_rule='normal relative eigengap<=1e-6 refuses; tangent tie uses largest world-axis projection, x/y/z first tie',
        position_moment='exact area integral on triangles; no vertex/centroid sampling bias')

def frame_normals(basis,angles):
    basis=np.asarray(basis,float);a=np.deg2rad(angles)
    return np.cos(a)[:,None]*basis[0]+np.sin(a)[:,None]*basis[1]

def direction_diagnostic(mesh,ids,basis):
    ids=np.unique(np.asarray(ids,int));w=face_areas(mesh)[ids];normals=frame_normals(basis,[35.,95.])
    t=np.cross(mesh['normals'][ids,None,:],normals[None,:,:]);s=np.linalg.norm(t,axis=2)
    good=(s>1e-12).all(1);angle=np.full(len(ids),-1.)
    angle[good]=np.rad2deg(np.arccos(np.clip(np.abs(np.einsum('ni,ni->n',t[good,0],t[good,1])/(s[good,0]*s[good,1])),0,1)))
    summary=dict(cutting_normals=normals.tolist(),faces=len(ids),area=float(w.sum()),
        layer_area_fraction_sin_below={str(x):((w[:,None]*(s<x)).sum(0)/w.sum()).tolist() for x in (.1,.25,.5)},
        valid_angle_area_fraction=float(w[good].sum()/w.sum()),
        area_weighted_cross_angle=float(np.average(angle[good],weights=w[good])) if good.any() else None,
        angle_area_bins={str(lo)+'_'+str(hi):float(w[good&(angle>=lo)&(angle<hi)].sum()/w.sum()) for lo,hi in [(0,15),(15,30),(30,45),(45,60),(60,75),(75,90.0001)]})
    return dict(face_ids=ids,area=w,tangent_sine=s,cross_angle_degrees=angle),summary

def regenerate_partitions(oldmesh,newmesh,old,added,style,basis,revision=True):
    style=dict(style,cutting_basis=np.asarray(basis).tolist())
    base,_=generate_layers(oldmesh,4,style)
    if 'visibility_mask' in old:
        unique=np.unique(visibility_masks(old,4))
        if len(unique)!=1:raise ValueError('nonuniform legacy visibility requires explicit transfer')
        base['visibility_mask']=np.full(len(base['points']),unique[0],dtype=old['visibility_mask'].dtype)
    ids=np.flatnonzero((newmesh['regions']==4)&(oldmesh['regions']!=4))
    _,extra=extend_paths(oldmesh,base,ids,style)
    if 'visibility_mask' in added:
        unique=np.unique(visibility_masks(added,4))
        if len(unique)!=1:raise ValueError('nonuniform added visibility requires explicit transfer')
        extra['visibility_mask']=np.full(len(extra['points']),unique[0],dtype=added['visibility_mask'].dtype)
    if revision:
        base['stroke_id']=base['stroke_id']+10_000_000_000
        extra['stroke_id']=extra['stroke_id']+10_000_000_000
    return base,extra
