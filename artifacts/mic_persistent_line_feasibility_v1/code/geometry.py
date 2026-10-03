"""Frozen calibrated path matching and persistent world-geometry construction.

No source pixels or assets are opened here. The staged runner supplies paths and
the construction-only native-depth callback. Local DTW compilation is confined
to this experiment's approved out directory.
"""
from __future__ import annotations

import ctypes
import hashlib
import itertools
import math
import os
from pathlib import Path
import subprocess

import numpy as np
from scipy.optimize import least_squares


class GeometryError(ValueError):
    def __init__(self, reason, diagnostics=None):
        super().__init__(reason)
        self.reason = reason
        self.diagnostics = diagnostics or {}


def _cfg(config, name):
    return config.get(name, config)


def camera_matrices(camera):
    camera = camera.get('camera', camera)
    K = np.asarray(camera.get('native_K', camera.get('K')), float)
    E = np.asarray(camera['w2c'], float)
    if K.shape != (3, 3) or E.shape != (4, 4) or not np.isfinite(K).all() or not np.isfinite(E).all():
        raise GeometryError('invalid_camera')
    return K, E[:3, :3], E[:3, 3]


def project(xyz, camera):
    xyz = np.asarray(xyz, dtype=float)
    K, R, t = camera_matrices(camera)
    q = xyz @ R.T + t
    h = q @ K.T
    with np.errstate(divide='ignore', invalid='ignore'):
        uv = h[..., :2] / h[..., 2:3]
    return uv, q[..., 2]


def _rays(uv, camera):
    K, R, t = camera_matrices(camera)
    uv = np.asarray(uv, float)
    q = np.c_[uv, np.ones(len(uv))] @ np.linalg.inv(K).T @ R
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    return -R.T @ t, q


def _ray_triangulation(observations, cameras, config):
    observations = np.asarray(observations, float)
    if observations.ndim == 2:
        observations = observations[:, None, :]
    if observations.ndim != 3 or observations.shape[0] != len(cameras) or observations.shape[2] != 2:
        raise GeometryError('invalid_correspondence_shape')
    if len(cameras) < _cfg(config, 'matching').get('min_views', 3) or not observations.shape[1] or not np.isfinite(observations).all():
        raise GeometryError('invalid_correspondences')
    tr = _cfg(config, 'triangulation')
    center_ray = [_rays(uv, cam) for uv, cam in zip(observations, cameras)]
    centers = np.asarray([v[0] for v in center_ray])
    rays = np.asarray([v[1] for v in center_ray])
    n = observations.shape[1]
    xyz = np.full((n, 3), np.nan)
    conditions, parallaxes, ranks, valid, reasons = [], [], [], [], []
    for s in range(n):
        ray = rays[:, s]
        angles = [math.degrees(math.acos(float(np.clip(abs(np.dot(a,b)), 0, 1))))
                  for a,b in itertools.combinations(ray, 2)]
        parallax = min(angles)
        planes = np.eye(3)[None] - ray[:, :, None] * ray[:, None, :]
        A = planes.sum(0)
        b = np.einsum('vij,vj->i', planes, centers)
        rank = int(np.linalg.matrix_rank(A))
        condition = float(np.linalg.cond(A))
        reason = None
        if parallax < tr['min_parallax_deg']:
            reason = 'low_parallax'
        elif rank < tr['min_rank']:
            reason = 'rank_deficient'
        elif not np.isfinite(condition) or condition > tr['max_ray_system_condition']:
            reason = 'ill_conditioned'
        else:
            xyz[s] = np.linalg.solve(A, b)
            if any(project(xyz[s:s+1], cam)[1][0] <= config.get('visibility', {}).get('near_plane', .001) for cam in cameras):
                reason = 'nonpositive_depth'
        conditions.append(condition)
        parallaxes.append(parallax)
        ranks.append(rank)
        valid.append(reason is None)
        reasons.append(reason)
    diag = dict(condition=conditions, parallax_deg=parallaxes, rank=ranks,
                valid=valid, sample_reasons=reasons)
    return xyz, diag


def triangulate(observations, cameras, config):
    original = np.asarray(observations, float)
    xyz, diag = _ray_triangulation(original, cameras, config)
    if not all(diag['valid']):
        raise GeometryError(next(x for x in diag['sample_reasons'] if x), diag)
    obs = original[:, None, :] if original.ndim == 2 else original
    error = np.asarray([np.linalg.norm(project(xyz, c)[0]-o, axis=1) for c,o in zip(cameras,obs)])
    diag.update(reprojection_median_px=float(np.median(error)),
                reprojection_p90_px=float(np.quantile(error, .9)))
    tr = _cfg(config, 'triangulation')
    if diag['reprojection_median_px'] > tr['max_reprojection_median_px'] or diag['reprojection_p90_px'] > tr['max_reprojection_p90_px']:
        raise GeometryError('reprojection_error', diag)
    return (xyz[0] if original.ndim == 2 else xyz), diag


def unique_choice(costs, config):
    values = np.asarray(costs, float)
    finite = np.flatnonzero(np.isfinite(values))
    if not len(finite):
        return None
    order = finite[np.argsort(values[finite], kind='stable')]
    if len(order) == 1:
        return int(order[0])
    best, second = values[order[:2]]
    mc = _cfg(config, 'matching')
    if second-best < mc['unique_margin_absolute_px']:
        return None
    if (second-best)/max(second, 1e-12) < mc['unique_margin_ratio']:
        return None
    return int(order[0])


def _fundamental(camera1, camera2):
    K1,R1,t1 = camera_matrices(camera1)
    K2,R2,t2 = camera_matrices(camera2)
    R = R2 @ R1.T
    t = t2-R@t1
    skew = np.array([[0,-t[2],t[1]], [t[2],0,-t[0]], [-t[1],t[0],0.]])
    return np.linalg.inv(K2).T @ skew @ R @ np.linalg.inv(K1)


def _epipolar_distances(xy1, xy2, camera1, camera2, directional=False):
    x1=np.c_[xy1,np.ones(len(xy1))]
    x2=np.c_[xy2,np.ones(len(xy2))]
    F=_fundamental(camera1,camera2)
    l2=x1@F.T
    l1=x2@F
    numer=np.abs(x1@F.T@x2.T)
    d1=np.linalg.norm(l2[:,:2],axis=1)
    d2=np.linalg.norm(l1[:,:2],axis=1)
    with np.errstate(divide='ignore',invalid='ignore'):
        target_distance=numer/d1[:,None]
        source_distance=numer/d2[None,:]
        distances=.5*(target_distance+source_distance)
    distances[~np.isfinite(distances)]=np.inf
    if directional:
        target_distance[~np.isfinite(target_distance)]=np.inf
        source_distance[~np.isfinite(source_distance)]=np.inf
        return distances,source_distance,target_distance
    return distances


_DTW = None


def _dtw(distances):
    global _DTW
    if _DTW is None:
        source=Path(__file__).with_name('geometry_dp.cpp')
        root=Path(__file__).resolve().parents[3]
        out=root/'out'/'mic_persistent_line_feasibility_v1'/'compiled'
        out.mkdir(parents=True,exist_ok=True)
        digest=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
        library=out/f'geometry_dp_{digest}.so'
        if not library.exists():
            subprocess.run(['g++','-O3','-std=c++11','-shared','-fPIC',str(source),'-o',str(library)],
                           check=True,capture_output=True,env=dict(os.environ,TMPDIR=str(out)))
        lib=ctypes.CDLL(str(library))
        fn=lib.bounded_dtw
        ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS')
        iptr=np.ctypeslib.ndpointer(dtype=np.int32,flags='C_CONTIGUOUS')
        fn.argtypes=[ptr,ctypes.c_int,ctypes.c_int,iptr,iptr]
        fn.restype=ctypes.c_int
        _DTW=(lib,fn)
    distances=np.ascontiguousarray(distances,dtype=np.float64)
    n,m=distances.shape
    rows=np.empty(n+m,np.int32); cols=np.empty(n+m,np.int32)
    count=_DTW[1](distances,n,m,rows,cols)
    return np.c_[rows[:count],cols[:count]]


def _summarize_mapping(distances, mapping, config, directional=None):
    mc=_cfg(config,'matching')
    mapping=np.asarray(mapping,int).reshape(-1,2)
    if not len(mapping):
        return dict(compatible=False,reason='no_ordered_alignment',cost=float('inf'),coverage=0.,mapping=[])
    values=distances[mapping[:,0],mapping[:,1]]
    if directional is None:
        directional_values=np.c_[values,values]
    else:
        directional_values=np.stack([d[mapping[:,0],mapping[:,1]] for d in directional],axis=1)
    good=np.isfinite(directional_values)&(directional_values<=mc['epipolar_p90_px'])
    coverage=min(len(np.unique(mapping[good[:,0],0]))/distances.shape[0],
                 len(np.unique(mapping[good[:,1],1]))/distances.shape[1])
    median=float(np.median(values)); p90=float(np.quantile(values,.9))
    compatible=bool(coverage>=mc['min_matched_fraction'] and median<=mc['epipolar_median_px'] and p90<=mc['epipolar_p90_px'])
    return dict(compatible=compatible,reason=None if compatible else 'epipolar_or_coverage',
                cost=median+.25*p90 if compatible else float('inf'),
                raw_cost=median+.25*p90,median=median,p90=p90,coverage=float(coverage),
                mapping=mapping.tolist(),pairs=mapping.tolist(),distances=values.tolist(),
                directional_distances=directional_values.tolist())


def _ordered_options(xy1,xy2,camera1,camera2,config):
    xy1=np.asarray(xy1,float); xy2=np.asarray(xy2,float)
    if xy1.ndim!=2 or xy2.ndim!=2 or len(xy1)<2 or len(xy2)<2 or not np.isfinite(xy1).all() or not np.isfinite(xy2).all():
        return [dict(compatible=False,reason='invalid_path',cost=float('inf'),coverage=0.,mapping=[])]
    distance,source_distance,target_distance=_epipolar_distances(xy1,xy2,camera1,camera2,True)
    options=[]
    for reverse in (False,True):
        mapping=_dtw(distance[:,::-1] if reverse else distance)
        if reverse and len(mapping):
            mapping[:,1]=len(xy2)-1-mapping[:,1]
        result=_summarize_mapping(distance,mapping,config,(source_distance,target_distance))
        result['reversed']=reverse
        options.append(result)
    return options


def ordered_match(xy1,xy2,camera1,camera2,config):
    options=_ordered_options(xy1,xy2,camera1,camera2,config)
    return min(options,key=lambda x:(not x['compatible'],x.get('raw_cost',float('inf')),x.get('reversed',False)))


def validate_shape(xyz,cameras,config):
    xyz=np.asarray(xyz,float)
    if xyz.ndim!=2 or xyz.shape[1]!=3 or len(xyz)<2 or not np.isfinite(xyz).all():
        raise GeometryError('invalid_geometry')
    tr=_cfg(config,'triangulation')
    world_length=float(np.linalg.norm(np.diff(xyz,axis=0),axis=1).sum())
    if world_length<tr['world_length_min']:
        raise GeometryError('collapsed_world_length')
    views=[]
    for cam in cameras:
        uv,z=project(xyz,cam)
        length=float(np.linalg.norm(np.diff(uv,axis=0),axis=1).sum())
        extent=float(np.linalg.norm(uv[:,None]-uv[None,:],axis=-1).max())
        valid=bool(np.isfinite(uv).all() and np.all(z>config.get('visibility',{}).get('near_plane',.001)) and length>=tr['projected_length_min_px'] and extent>=tr['projected_extent_min_px'])
        views.append(dict(projected_length_px=length,projected_extent_px=extent,nondegenerate=valid))
    if sum(v['nondegenerate'] for v in views)<_cfg(config,'matching').get('min_views',3):
        raise GeometryError('collapsed_projected_coverage',dict(world_length=world_length,views=views))
    return dict(world_length=world_length,views=views)


def _points(path):
    return np.asarray(path.get('points',path.get('points32')),float)


def _compatible_descriptors(a,b,config,reverse=False):
    mc=config['matching']
    if not (int(a['source_bits']) & int(b['source_bits'])):
        return False,'type_incompatible'
    la=float(a['length']); lb=float(b['length'])
    if min(la,lb)<=0 or max(la,lb)/min(la,lb)>mc['length_ratio_max']:
        return False,'length_incompatible'
    ca=np.asarray(a['curvature'],float); cb=np.asarray(b['curvature'],float)
    if reverse: cb=cb[::-1]
    if ca.shape!=cb.shape or not np.isfinite(ca).all() or not np.isfinite(cb).all() or np.mean(np.abs(ca-cb))>mc['curvature_descriptor_difference_max']:
        return False,'curvature_incompatible'
    return True,None


def _pair_table(paths1,paths2,cam1,cam2,config,frozen=None,forced_chosen=None):
    table={}; costs=np.full((len(paths1),len(paths2)),np.inf)
    counts={}
    for i,a in enumerate(paths1):
        for j,b in enumerate(paths2):
            if frozen is not None and (i,j) not in frozen:
                continue
            okf,reason=_compatible_descriptors(a,b,config,False)
            okr,_=_compatible_descriptors(a,b,config,True)
            if not (okf or okr):
                counts[reason]=counts.get(reason,0)+1
                continue
            if frozen is None:
                options=_ordered_options(_points(a),_points(b),cam1,cam2,config)
                options=[o for o in options if _compatible_descriptors(a,b,config,o.get('reversed',False))[0]]
                result=min(options,key=lambda x:(not x['compatible'],x.get('raw_cost',float('inf')),x.get('reversed',False)))
            else:
                original=frozen[(i,j)]
                distance,source_distance,target_distance=_epipolar_distances(_points(a),_points(b),cam1,cam2,True)
                result=_summarize_mapping(distance,original['mapping'],config,(source_distance,target_distance))
                result['reversed']=original.get('reversed',False)
                if not _compatible_descriptors(a,b,config,result['reversed'])[0]:
                    result.update(compatible=False,cost=float('inf'),reason='curvature_incompatible')
                result['forced_no_rematch']=True
            table[(i,j)]=result
            costs[i,j]=result['cost']
            label='compatible' if result['compatible'] else result['reason']
            counts[label]=counts.get(label,0)+1
    chosen={}
    row_choices=[unique_choice(row,config) for row in costs]
    col_choices=[unique_choice(col,config) for col in costs.T]
    for i,j in enumerate(row_choices):
        if j is not None and col_choices[j]==i and (forced_chosen is None or forced_chosen.get(i)==j):
            chosen[i]=j
    alternatives=[]
    for side,matrix in [('source',costs),('target',costs.T)]:
        for i,row in enumerate(matrix):
            order=np.flatnonzero(np.isfinite(row))
            order=order[np.argsort(row[order],kind='stable')][:config['budget']['max_pair_alternatives_recorded']]
            alternatives.append(dict(side=side,index=i,alternatives=[dict(index=int(j),cost=float(row[j])) for j in order],unique_choice=unique_choice(row,config)))
    return dict(table=table,costs=costs,chosen=chosen,counts=counts,alternatives=alternatives)


def _map(result,reverse=False,max_distance=4.):
    pairs=np.asarray(result['mapping'],int)
    distances=np.asarray(result.get('distances',np.zeros(len(pairs))),float)
    if 'directional_distances' in result:
        distances=np.max(np.asarray(result['directional_distances'],float),axis=1)
    if reverse: pairs=pairs[:,::-1]
    mapping={}
    for (a,b),d in zip(pairs,distances):
        if d<=max_distance and (int(a) not in mapping or (d,int(b))<mapping[int(a)]):
            mapping[int(a)]=(float(d),int(b))
    return {a:b for a,(_,b) in mapping.items()}


def _refine_controls(samples,observations,cameras,config):
    tr=config['triangulation']
    arc=np.r_[0.,np.linalg.norm(np.diff(samples,axis=0),axis=1).cumsum()]
    if arc[-1]<=0: raise GeometryError('collapsed_world_length')
    count=min(config['budget']['max_controls_per_path'],len(samples))
    targets=np.linspace(0,arc[-1],count)
    selected=np.unique(np.argmin(np.abs(arc[:,None]-targets[None,:]),axis=0))
    if len(selected)<2: raise GeometryError('collapsed_world_length')
    control_arc=arc[selected]
    segment=np.clip(np.searchsorted(control_arc,arc,side='right')-1,0,len(selected)-2)
    weight=(arc-control_arc[segment])/np.maximum(control_arc[segment+1]-control_arc[segment],1e-12)
    def sample_controls(control):
        return control[segment]*(1-weight[:,None])+control[segment+1]*weight[:,None]
    def residual(flat):
        points=sample_controls(flat.reshape(-1,3))
        values=np.concatenate([(project(points,cam)[0]-obs).ravel() for cam,obs in zip(cameras,observations)])
        return np.nan_to_num(values,nan=1e12,posinf=1e12,neginf=-1e12)
    initial=samples[selected].copy()
    result=least_squares(residual,initial.ravel(),loss=tr['robust_loss'],f_scale=tr['robust_scale_px'],max_nfev=tr['max_optimizer_evaluations'])
    control=result.x.reshape(-1,3)
    fitted=sample_controls(control)
    return control,fitted,dict(initial_control_xyz=initial.tolist(),selected_sample_indices=selected.tolist(),nfev=int(result.nfev),success=bool(result.success),cost=float(result.cost))


def _tangents(points):
    return np.gradient(np.asarray(points,float),axis=0)


def _angle(a,b):
    scale=np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)
    good=scale>1e-12
    value=np.full(len(a),np.nan)
    value[good]=np.degrees(np.arccos(np.clip(np.abs(np.sum(a[good]*b[good],axis=1)/scale[good]),0,1)))
    return value


def _construct_triplet(view_names,path_indices,paths_by_view,cameras,pair_tables,config,depth_support_callback,persistent_id):
    views=list(view_names); indices=list(path_indices)
    paths=[paths_by_view[v][i] for v,i in zip(views,indices)]
    pa=pair_tables[(views[0],views[1])]['table'][(indices[0],indices[1])]
    pb=pair_tables[(views[1],views[2])]['table'][(indices[1],indices[2])]
    pc=pair_tables[(views[0],views[2])]['table'][(indices[0],indices[2])]
    ab=_map(pa); bc=_map(pb); ca=_map(pc,True)
    ref=_points(paths[0]); common=[]; tuples=[]; errors=[]
    for i in range(len(ref)):
        if i not in ab or ab[i] not in bc or bc[ab[i]] not in ca: continue
        j=ab[i]; k=bc[j]; back=ca[k]
        error=float(np.linalg.norm(ref[back]-ref[i]))
        common.append(i); errors.append(error)
        if error<=config['matching']['cycle_error_px_max']: tuples.append((i,j,k))
    fraction=len(tuples)/len(common) if common else 0.
    diagnostic=dict(views=views,path_ids=[p['id'] for p in paths],cycle_common_count=len(common),cycle_good_count=len(tuples),cycle_fraction=fraction,cycle_errors_px=errors)
    if fraction<config['matching']['min_matched_fraction'] or len(tuples)<config['triangulation']['min_samples']:
        return None,dict(diagnostic,reason='cycle_or_sample_count')
    indices3=np.asarray(tuples,int)
    observations=np.asarray([_points(p)[indices3[:,v]] for v,p in enumerate(paths)])
    cams=[cameras[v] for v in views]
    samples,tri=_ray_triangulation(observations,cams,config)
    mask=np.asarray(tri['valid'],bool)
    diagnostic['triangulation']=tri
    if int(mask.sum())<config['triangulation']['min_samples']:
        return None,dict(diagnostic,reason='insufficient_triangulated_samples')
    observations=observations[:,mask]; indices3=indices3[mask]; samples=samples[mask]
    control,fitted,fit=_refine_controls(samples,observations,cams,config)
    reasons=[]; tr=config['triangulation']
    try: shape=validate_shape(control,cams,config)
    except GeometryError as exc:
        shape=exc.diagnostics; reasons.append(exc.reason)
    reprojection=[]; direction=[]; coverage=[]; depth=[]
    for v,(name,path,cam,observed) in enumerate(zip(views,paths,cams,observations)):
        projected,z=project(fitted,cam)
        errors=np.linalg.norm(projected-observed,axis=1)
        # Projection of local3D tangent, compared with observation tangent in this camera.
        angles=_angle(_tangents(projected),_tangents(_points(path))[indices3[:,v]])
        valid=np.isfinite(angles)
        median=float(np.median(errors)); p90=float(np.quantile(errors,.9))
        orientation=float(np.median(angles[valid])) if valid.any() else float('inf')
        reprojection.append(dict(median_px=median,p90_px=p90))
        direction.append(dict(median_deg=orientation,finite_count=int(valid.sum())))
        if median>tr['max_reprojection_median_px'] or p90>tr['max_reprojection_p90_px']: reasons.append('construction_reprojection')
        if orientation>config['matching']['orientation_degrees_max']: reasons.append('construction_orientation')
        info=depth_support_callback(name,observed,z)
        supported=np.asarray(info.get('supported',info.get('support')),bool)
        conflict=np.asarray(info.get('layer_conflict',info.get('conflict')),bool)
        fraction=float(supported.mean()) if len(supported) else 0.
        depth.append(dict(support_fraction=fraction,conflict_count=int(conflict.sum()),sample_count=len(supported),sample_diagnostics=_json(info)))
        if conflict.any(): reasons.append('construction_layer_conflict')
        if fraction<tr['depth_min_support_fraction']: reasons.append('construction_depth_support')
        good=valid & (angles<=config['matching']['orientation_degrees_max']) & (errors<=tr['max_reprojection_p90_px']) & supported & ~conflict
        cov=len(np.unique(indices3[good,v]))/config['extraction']['sample_count']
        coverage.append(cov)
        if cov<tr['construction_required_coverage']: reasons.append('construction_coverage')
        if not np.all(z>config['visibility']['near_plane']): reasons.append('construction_nonpositive_depth')
    # Bound all controls globally in caller; correspondence and raw samples stay diagnostics.
    arc=np.r_[0.,np.linalg.norm(np.diff(control,axis=0),axis=1).cumsum()]
    proposal=dict(persistent_id=persistent_id,id=persistent_id,xyz=control.tolist(),controls_xyz=control.tolist(),control_points_world=control.tolist(),
                  topology=list(range(len(control))),brush_arclength=arc.tolist(),
                  construction_ok=not reasons,construction_reasons=sorted(set(reasons)),
                  participating_views=views,construction_path_ids=[p['id'] for p in paths],
                  correspondences=dict(indices=indices3.tolist(),observations=observations.tolist(),triangulated_world=samples.tolist()),
                  cycle=diagnostic,fit=fit,shape=shape,reprojection=reprojection,direction=direction,coverage=coverage,depth=depth,
                  source_bits=int(np.bitwise_or.reduce([int(p['source_bits']) for p in paths])))
    return proposal,dict(diagnostic,reason=None if not reasons else 'construction_gates',construction_reasons=sorted(set(reasons)))


def _json(value):
    if isinstance(value,np.ndarray): return value.tolist()
    if isinstance(value,np.generic): return value.item()
    if isinstance(value,dict): return {str(k):_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [_json(v) for v in value]
    return value


def _enumerate_proposals(paths_by_view,cameras,tables,config,callback,prefix):
    names=list(paths_by_view)
    proposals=[]; attempts=[]; triplets=0; controls=0
    maxhyp=config['budget']['max_triplet_hypotheses']
    for views in itertools.combinations(names,3):
        if any(pair not in tables for pair in itertools.combinations(views,2)): continue
        a,b,c=views
        for i,j in sorted(tables[(a,b)]['chosen'].items()):
            triplets+=1
            if triplets>maxhyp: break
            k=tables[(a,c)]['chosen'].get(i)
            if k is None or tables[(b,c)]['chosen'].get(j)!=k: continue
            if len(proposals)>=config['budget']['max_proposals']: break
            result,diag=_construct_triplet(views,(i,j,k),paths_by_view,cameras,tables,config,callback,f'{prefix}{len(proposals):03d}')
            attempts.append(diag)
            if result is not None:
                if controls+len(result['xyz'])>config['budget']['max_total_controls']: break
                controls+=len(result['xyz']); proposals.append(result)
        if triplets>=maxhyp or len(proposals)>=config['budget']['max_proposals']: break
    return proposals,dict(triplet_hypotheses=min(triplets,maxhyp),triangulation_attempts=len(attempts),formed=len(proposals),proposals=len(proposals),construction_pass=sum(p['construction_ok'] for p in proposals),total_controls=controls,attempts=attempts)


def build_proposals(paths_by_view,cameras,config,depth_support_callback):
    names=[v for v in config['construction'] if v in paths_by_view]
    paths_by_view={v:paths_by_view[v] for v in names}
    tables={}; pair_report=[]
    for a,b in itertools.combinations(names,2):
        _,Ra,_=camera_matrices(cameras[a]); _,Rb,_=camera_matrices(cameras[b])
        separation=math.degrees(math.acos(float(np.clip(np.dot(Ra[2],Rb[2]),-1,1))))
        if separation<config['matching']['min_camera_separation_deg']:
            pair_report.append(dict(views=[a,b],separation_deg=separation,reason='camera_separation'));continue
        record=_pair_table(paths_by_view[a],paths_by_view[b],cameras[a],cameras[b],config)
        tables[(a,b)]=record
        pair_report.append(dict(views=[a,b],separation_deg=separation,counts=record['counts'],mutual_unique_count=len(record['chosen']),alternatives=record['alternatives']))
    proposals,diagnostics=_enumerate_proposals(paths_by_view,cameras,tables,config,depth_support_callback,'p')
    diagnostics['pairs']=pair_report
    # Wrong associations retain the original point-index mappings, never run DTW again.
    rng=np.random.default_rng(config['null']['association_shuffle_seed'])
    null_paths={v:list(p) for v,p in paths_by_view.items()}; permutations={}; eligible={}
    for target in names[1:]:
        target_indices=set()
        for (a,b),record in tables.items():
            if b==target:
                target_indices.update(j for (i,j),value in record['table'].items() if value['compatible'])
        ids=sorted(target_indices); eligible[target]=len(ids)
        if len(ids)<2: continue
        # Seeded order followed by one cyclic rotation is always a derangement.
        order=np.asarray(ids,int)[rng.permutation(len(ids))]
        mapping={int(a):int(b) for a,b in zip(order,np.roll(order,1))}
        for destination,source in mapping.items(): null_paths[target][destination]=paths_by_view[target][source]
        permutations[target]={str(k):v for k,v in sorted(mapping.items())}
    null_tables={}
    for (a,b),record in tables.items():
        null_tables[(a,b)]=_pair_table(null_paths[a],null_paths[b],cameras[a],cameras[b],config,
                                       frozen=record['table'],forced_chosen=record['chosen'])
    null_proposals,null_diag=_enumerate_proposals(null_paths,cameras,null_tables,config,depth_support_callback,'null_p')
    sufficient=bool(permutations) and all(n>=2 for n in eligible.values())
    diagnostics['null']=dict(sufficient=sufficient,status='evaluated' if sufficient else 'insufficient',eligible_target_identities=eligible,
                             permutations=permutations,rematched=False,**null_diag)
    diagnostics['null_proposals']=null_proposals
    return proposals,diagnostics
