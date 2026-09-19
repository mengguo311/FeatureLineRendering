"""Cell-held-out sample-semantic diagnosis. Never imported by the generator."""
import ctypes,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from .multiscene_probe import axial_angle


def contribution_weights(state,height=800,width=800):
    library=Path(__file__).resolve().parents[1]/'out/multiscene_foundation_corrected/setup/surface.so'
    lib=ctypes.CDLL(str(library));fn=lib.contribution_weights
    fn.argtypes=[ctypes.c_int]*2+[ctypes.c_void_p]*5;fn.restype=None
    arrays=[np.ascontiguousarray(state[k],d) for k,d in [('means2D','f4'),('conic','f4'),('point_list','u4'),('ranges','u4')]]
    weights=np.zeros(len(state['depths']),'f8')
    fn(height,width,*[a.ctypes.data for a in arrays],weights.ctypes.data)
    return weights


def plane(points,weights):
    weights=np.asarray(weights,float);weights=weights/max(weights.sum(),1e-30)
    center=np.sum(points*weights[:,None],axis=0);d=points-center
    values,vectors=np.linalg.eigh((d*weights[:,None]).T@d)
    return center,vectors,values


def _models(points,weights,train,held,h,cfg):
    p,w=points[train],weights[train];v=points[held]
    center,axes,values=plane(p,w);normal=axes[:,0]
    residual=np.abs((v-center)@normal)
    coordinates=(p-center)@axes;test=(v-center)@axes
    def design(q):
        x,y=q[:,1],q[:,2];return np.c_[np.ones(len(q)),x,y,x*x,x*y,y*y]
    beta=np.linalg.lstsq(design(coordinates)*np.sqrt(w[:,None]),coordinates[:,0]*np.sqrt(w),rcond=None)[0]
    x,y=test[:,1],test[:,2]
    gradx=beta[1]+2*beta[3]*x+beta[4]*y;grady=beta[2]+beta[4]*x+2*beta[5]*y
    quadratic=np.abs(test[:,0]-design(test)@beta)/np.sqrt(1+gradx**2+grady**2)
    # Three train-only deterministic starts, ten assignments each. Held-out data
    # never selects a model, axis, fit, sample or threshold.
    candidates=[]
    for axis in range(3):
        label=coordinates[:,axis]>=np.median(coordinates[:,axis]);models=None
        for _ in range(10):
            if min(label.sum(),(~label).sum())<3:models=None;break
            models=[plane(p[label==k],w[label==k])[:2] for k in [False,True]]
            d=np.stack([abs((p-c)@a[:,0]) for c,a in models],axis=1);label=d[:,1]<d[:,0]
        if models is not None:candidates.append((float(np.average(d.min(1)**2,weights=w)),models,label.copy()))
    pair=None
    if candidates:
        _,models,label=min(candidates,key=lambda q:q[0]);testd=np.stack([abs((v-c)@a[:,0]) for c,a in models],axis=1)
        normals=np.array([a[:,0] for c,a in models]);angle=float(axial_angle(*normals))
        intersection=np.linalg.lstsq(normals,np.array([np.dot(c,a[:,0]) for c,a in models]),rcond=None)[0]
        # Both finite support patches must reach the putative intersection line.
        tangent=np.cross(*normals);norm=np.linalg.norm(tangent)
        distances=[]
        for k in [0,1]:
            diff=p[label==bool(k)]-intersection
            distances.append(float(np.min(np.linalg.norm(diff-(diff@(tangent/max(norm,1e-30)))[:,None]*(tangent/max(norm,1e-30)),axis=1))))
        pair=dict(p90_h=float(np.quantile(testd.min(1),.9)/h),angle=angle,fit_cells_per_side=[int((~label).sum()),int(label.sum())],intersection_distance=distances,normals=normals.tolist())
    rng=np.random.default_rng(cfg['queries']['seed']);angles=[]
    for _ in range(cfg['surface']['bootstrap_samples']):
        idx=rng.integers(0,len(p),len(p));_,a,_=plane(p[idx],w[idx]);angles.append(float(axial_angle(normal,a[:,0])))
    return dict(plane_p90_h=float(np.quantile(residual,.9)/h),quadratic_p90_h=float(np.quantile(quadratic,.9)/h),volume_p90_h=float(np.quantile(np.linalg.norm(v-center,axis=1),.9)/h),normal=normal.tolist(),center=center.tolist(),spread=float(values[1]/max(values[2],1e-30)),normal_bootstrap_p90=float(np.quantile(angles,.9)),two_plane=pair)


def fit_neighborhood(points,weights,location,delta,h,cfg):
    points=np.asarray(points,float);weights=np.asarray(weights,float)
    cells=np.floor(points/(delta*cfg['surface']['cell_delta'])).astype('i8')
    unique,inverse=np.unique(cells,axis=0,return_inverse=True);n=len(unique)
    ids=[hashlib.sha256((':'.join(map(str,c))).encode()).hexdigest() for c in unique]
    train=np.array([int(s[:8],16)%2==0 for s in ids],dtype=bool);held=~train
    result=dict(gaussians=len(points),occupied_cells=n,fit_cells=int(train.sum()),heldout_cells=int(held.sum()),fit_cell_ids=[s for s,t in zip(ids,train) if t],heldout_cell_ids=[s for s,t in zip(ids,train) if not t],radius=h,location=np.asarray(location).tolist(),sheet_local=False,crease_local=False,bucket='sparse')
    if min(train.sum(),held.sum())<6:return result
    count=np.bincount(inverse);representatives=np.stack([np.bincount(inverse,weights=points[:,j])/count for j in range(3)],axis=1)
    mass=np.bincount(inverse,weights=weights);mass=np.maximum(mass,1e-30)
    result['equal_cell']=_models(representatives,np.ones(n),train,held,h,cfg)
    # All original center contributions pooled within their indivisible cell.
    weighted=np.stack([np.bincount(inverse,weights=points[:,j]*weights)/mass for j in range(3)],axis=1)
    weighted[mass<=1e-29]=representatives[mass<=1e-29]
    result['contribution_weighted']=_models(weighted,mass,train,held,h,cfg)
    m=result['equal_cell'];s=cfg['surface'];pair=m['two_plane']
    result['sheet_local']=bool(n>=s['min_sheet_cells'] and min(m['plane_p90_h'],m['quadratic_p90_h'])<=s['p90_h_max'] and m['spread']>=s['plane_spread_min'] and m['normal_bootstrap_p90']<=s['normal_p90_max'])
    if pair:
        best=min(m['plane_p90_h'],m['quadratic_p90_h']);gain=1-pair['p90_h']/best if best>1e-12 else None;pair['heldout_gain']=gain
        result['crease_local']=bool(min(pair['fit_cells_per_side'])>=s['min_plane_cells'] and gain is not None and gain>=s['twoplane_gain_min'] and pair['angle']>=s['twoplane_angle_min'] and max(pair['intersection_distance'])<=delta)
    result['bucket']='plausible_crease_candidate' if result['crease_local'] else ('sheet_candidate' if result['sheet_local'] else ('multilayer' if pair and pair['angle']<s['twoplane_angle_min'] and pair['p90_h']<=s['p90_h_max'] else 'blob_or_unstable'))
    return result


def audit_asset(asset,weights,locations,delta,cfg):
    tree=cKDTree(asset['mu']);result=[]
    for location in locations:
        scales=[]
        for factor in cfg['surface']['radii_delta']:
            h=delta*factor;idx=tree.query_ball_point(location['point'],h)
            record=fit_neighborhood(asset['mu'][idx],weights[idx],location['point'],delta,h,cfg)
            if 'equal_cell' in record and idx:
                from .common import quat_to_rotmat
                R=quat_to_rotmat(asset['quat'][idx]);short=asset['scale'][idx].argmin(1)
                normals=R[np.arange(len(idx)),:,short];angles=axial_angle(normals,record['equal_cell']['normal'])
                ratio=asset['scale'][idx].max(1)/np.maximum(asset['scale'][idx].min(1),1e-30)
                record['covariance_axis_agreement']=[dict(anisotropy_interval=[lo,hi],count=int(((ratio>=lo)&(ratio<hi)).sum()),median_angle=float(np.median(angles[(ratio>=lo)&(ratio<hi)])) if np.any((ratio>=lo)&(ratio<hi)) else None) for lo,hi in [(1,2),(2,5),(5,1e30)]]
            scales.append(record)
        adjacent=[]
        for a,b in zip(scales,scales[1:]):
            adjacent.append(float(axial_angle(a['equal_cell']['normal'],b['equal_cell']['normal'])) if 'equal_cell' in a and 'equal_cell' in b else None)
        result.append(dict(location=location,scales=scales,adjacent_scale_angles=adjacent))
    return result
