"""One authored image polyline, projected once onto first-hit proxy triangles.

Triangle-projected intervals are split at coverage and depth-order changes.
Each retained segment has its own face/bary coordinates; gaps are never joined.
This is an authored proxy detail, not recovered geometry or Gaussian ownership.
"""
import runtime
import json
from pathlib import Path
import numpy as np
from geometry import project,ray_surface

def validate_curve(mesh,p):
    f=np.asarray(p['face']);b=np.asarray(p['bary']);x=np.asarray(p['points']);n=len(f)
    if f.dtype.kind not in 'iu' or f.shape!=(n,) or b.shape!=(n,2,3) or x.shape!=(n,2,3):raise ValueError('bad curve shapes')
    if (f<0).any() or (f>=len(mesh['faces'])).any():raise ValueError('invalid face')
    if not np.isfinite(x).all() or not np.isfinite(b).all():raise ValueError('nonfinite curve')
    if n and (b.min() < -1e-8 or b.max()>1+1e-8):raise ValueError('invalid barycentrics')
    if not np.allclose(b.sum(-1),1,atol=1e-10,rtol=0):raise ValueError('barycentric mass')
    if not np.allclose(x,np.einsum('nij,njk->nik',b,mesh['tri'][f]),atol=1e-10,rtol=0):raise ValueError('curve not on saved triangle')
    if p['curve_id'].shape!=(n,) or p['curve_id'].dtype.kind not in 'iu':raise ValueError('invalid curve IDs')

def project_curve(mesh,camera,controls,curve_id):
    controls=np.asarray(controls,float)
    if controls.ndim!=2 or controls.shape[1]!=2 or not 2<=len(controls)<=24 or not np.isfinite(controls).all():raise ValueError('2..24 finite control points required')
    if (controls<0).any() or (controls[:,0]>=camera['width']).any() or (controls[:,1]>=camera['height']).any():raise ValueError('controls outside author camera')
    uv,z=project(mesh['vertices'],camera);tri=uv[mesh['faces']];zz=z[mesh['faces']]
    e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0]
    det=e1[:,0]*e2[:,1]-e1[:,1]*e2[:,0]
    valid=(zz>.2).all(1)&(np.abs(det)>1e-12)
    def bary2(q):
        d=q-tri[:,0];b1=np.divide(d[:,0]*e2[:,1]-d[:,1]*e2[:,0],det,out=np.zeros(len(det)),where=valid)
        b2=np.divide(e1[:,0]*d[:,1]-e1[:,1]*d[:,0],det,out=np.zeros(len(det)),where=valid)
        return np.column_stack([1-b1-b2,b1,b2])
    faces=[];barys=[];points=[];edges=[];ts=[];unsupported=[];discontinuities=[]
    total=0.;lost=0.;last=None;max_gap=0.
    for edge,(start,end) in enumerate(zip(controls[:-1],controls[1:])):
        length=float(np.linalg.norm(end-start));total+=length
        if length<1e-10:raise ValueError('duplicate consecutive controls')
        b0=bary2(start);bd=bary2(end)-b0
        lo=np.zeros(len(det));hi=np.ones(len(det));ok=valid.copy()
        for j in range(3):
            slope=bd[:,j];constant=np.abs(slope)<1e-14
            ok &= ~(constant&(b0[:,j]<-1e-12))
            t=np.divide(-b0[:,j],slope,out=np.zeros(len(det)),where=~constant)
            lo=np.where(slope>1e-14,np.maximum(lo,t),lo)
            hi=np.where(slope< -1e-14,np.minimum(hi,t),hi)
        ids=np.flatnonzero(ok&(hi-lo>1e-10));cuts=[0.,1.]
        cuts.extend(lo[ids]);cuts.extend(hi[ids])
        # Inverse camera-z is affine over projected triangles; pair crossings
        # cover depth-order changes even for overlapping/intersecting surfaces.
        iz0=np.sum(b0/zz,axis=1);izd=np.sum(bd/zz,axis=1)
        for k,i in enumerate(ids):
            other=ids[k+1:];den=izd[i]-izd[other]
            crossing=np.divide(iz0[other]-iz0[i],den,out=np.full(len(other),np.nan),where=np.abs(den)>1e-14)
            keep=(crossing>np.maximum(lo[i],lo[other])+1e-10)&(crossing<np.minimum(hi[i],hi[other])-1e-10)
            cuts.extend(crossing[keep])
        cuts=np.unique(np.clip(cuts,0,1));runs=[]
        for a,b in zip(cuts[:-1],cuts[1:]):
            if b-a<=1e-10:continue
            mid=(a+b)/2;cover=ids[(lo[ids]<=mid)&(hi[ids]>=mid)]
            face=int(cover[np.argmax(iz0[cover]+mid*izd[cover])]) if len(cover) else -1
            if runs and runs[-1][2]==face and abs(runs[-1][1]-a)<1e-9:runs[-1][1]=float(b)
            else:runs.append([float(a),float(b),face])
        for a,b,face in runs:
            if face<0:
                unsupported.append(dict(author_edge=edge,t=[a,b],reason='no_frontmost_triangle',screen_length=(b-a)*length))
                lost+=(b-a)*length;last=None;continue
            screenb=b0[face]+np.array([a,b])[:,None]*bd[face]
            bary=screenb/zz[face];bary/=bary.sum(1)[:,None]
            x=bary@mesh['tri'][face]
            if last is not None:
                gap=float(np.linalg.norm(x[0]-last));max_gap=max(max_gap,gap)
                if gap>1e-7:discontinuities.append(dict(before_segment=len(faces),world_gap=gap,reason='first_hit_surface_discontinuity; no connecting segment'))
            faces.append(face);barys.append(bary);points.append(x);edges.append(edge);ts.append([a,b]);last=x[1]
    n=len(faces)
    p=dict(face=np.asarray(faces,np.int64),bary=np.asarray(barys,float).reshape(n,2,3),points=np.asarray(points,float).reshape(n,2,3),
           curve_id=np.full(n,curve_id,np.int64),author_edge=np.asarray(edges,np.int32),author_t=np.asarray(ts,float).reshape(n,2))
    validate_curve(mesh,p)
    report=dict(segments=n,curve_id=curve_id,author_controls=len(controls),author_screen_length=total,unsupported_screen_length=lost,
                unsupported=unsupported,discontinuities=discontinuities,max_endpoint_gap_world=max_gap,
                world_length=float(np.linalg.norm(p['points'][:,1]-p['points'][:,0],axis=1).sum()),
                method='Exact projected-triangle interval clipping and frontmost inverse-z envelope, perspective-correct face/bary; no bridge across uncovered or depth-discontinuous intervals',
                open_authored_polyline=True,automatic_closure=False)
    return p,report

def raster_structure(mesh,p,camera,aa=2):
    validate_curve(mesh,p)
    depth,_,_,c=ray_surface(mesh,camera,aa);ink=np.zeros_like(depth,dtype=np.float32)
    E=np.asarray(c['extrinsic']);R=E[:3,:3];nc=mesh['normals']@np.linalg.inv(R)
    plane=np.einsum('ij,ij->i',nc,mesh['tri'][:,0]@R.T+E[:3,3]);radius=aa*.5
    accepted=0;covered_count=0;segments_visible=0
    for points,face in zip(p['points'],p['face']):
        uv,z=project(points,c)
        if (z<=.2).any():continue
        d=uv[1]-uv[0];l2=float(d@d)
        if l2<1e-14:continue
        lo=np.maximum(0,np.ceil(uv.min(0)-radius)).astype(int);hi=np.minimum([c['width']-1,c['height']-1],np.floor(uv.max(0)+radius)).astype(int)
        if (hi<lo).any():continue
        y,x=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        t=np.clip(((x-uv[0,0])*d[0]+(y-uv[0,1])*d[1])/l2,0,1)
        covered=(x-uv[0,0]-t*d[0])**2+(y-uv[0,1]-t*d[1])**2<=radius**2
        n=nc[face];den=n[0]*(x-c['cx'])/c['fx']+n[1]*(y-c['cy'])/c['fy']+n[2]
        zline=np.divide(plane[face],den,out=np.full_like(den,np.inf),where=np.abs(den)>1e-12)
        dd=depth[lo[1]:hi[1]+1,lo[0]:hi[0]+1];delta=np.full_like(dd,np.inf)
        np.subtract(zline,dd,out=delta,where=np.isfinite(zline)&np.isfinite(dd))
        visible=covered&np.isfinite(dd)&(np.abs(delta)<=.004)
        ink[lo[1]:hi[1]+1,lo[0]:hi[0]+1][visible]=.85
        accepted+=int(visible.sum());covered_count+=int(covered.sum());segments_visible+=int(visible.any())
    return ink,dict(accepted_fragments=accepted,covered_fragments=covered_count,segments_with_visible_ink=segments_visible,
        total_segments=len(p['face']),native_ink_mass=float(ink.sum()/aa**2),visibility='same fixed proxy first-hit; .004 tolerance, no region/S gate')

def combine_structure(paper,base_aa,structure_aa,enabled,aa=2):
    if type(enabled) is not bool:raise ValueError('enabled must be boolean')
    h,w=paper.shape[:2]
    if base_aa.shape!=(h*aa,w*aa) or structure_aa.shape!=base_aa.shape:raise ValueError('unaligned AA layers')
    low=lambda a:a.reshape(h,aa,w,aa).mean((1,3))
    structure=structure_aa if enabled else np.zeros_like(structure_aa)
    combined=low(np.maximum(base_aa,structure))
    return dict(structure=low(structure),combined_ink=combined,hybrid=paper*(1-combined[:,:,None])+.03*combined[:,:,None])

def load_structure(asset,mesh):
    asset=Path(asset);m=json.loads((asset/'STRUCTURE.json').read_text())
    if m['schema']!='chair_authored_structure_v1' or type(m['enabled']) is not bool:raise ValueError('invalid structure configuration')
    if m['width']!=1. or m['strength']!=.85 or m['ink_color']!=.03 or m['aa']!=2 or m['depth_tolerance']!=.004:raise ValueError('frozen curve style changed')
    if runtime.sha(asset/'structure.npz')!=m['path_sha256'] or runtime.sha(asset/'mesh.npz')!=m['mesh_sha256']:raise ValueError('structure asset identity mismatch')
    with np.load(asset/'structure.npz',allow_pickle=False) as z:p={k:z[k] for k in z.files}
    validate_curve(mesh,p)
    return p,m
