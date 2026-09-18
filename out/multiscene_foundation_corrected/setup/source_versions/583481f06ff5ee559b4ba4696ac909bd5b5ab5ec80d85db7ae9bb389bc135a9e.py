"""ID-aware multi-view grouping, controlled nulls, and finite 3D linelets.
No mesh, detector, image, or data IO. IDs are necessary but never sufficient.
"""
from collections import defaultdict,Counter
import numpy as np
from scipy.spatial import cKDTree
from .id_anchor import subset


def shuffled_ids(obs,n_gaussians,seed):
    out={k:v.copy() for k,v in obs.items()}
    for view in sorted(set(obs['view'].tolist())):
        permutation=np.random.default_rng(seed+int(view)).permutation(n_gaussians)
        idx=obs['view']==view;ids=out['ids'][idx];valid=ids>=0
        ids[valid]=permutation[ids[valid]];out['ids'][idx]=ids
    return out


def match_counts(real,shifted,seed):
    """Match accepted observation counts separately per TRAIN view and source."""
    ri=[];ni=[]
    for view in sorted(set(real['view'].tolist())):
        for source in sorted(set(real['source'].tolist())):
            a=np.flatnonzero((real['view']==view)&(real['source']==source))
            b=np.flatnonzero((shifted['view']==view)&(shifted['source']==source));n=min(len(a),len(b))
            rng=np.random.default_rng(seed+view*101+source*17)
            ri.extend(np.sort(rng.permutation(a)[:n]));ni.extend(np.sort(rng.permutation(b)[:n]))
    return subset(real,np.asarray(ri,int)),subset(shifted,np.asarray(ni,int))


def group(obs,g,gaussian_keep,cameras,spacing,cfg):
    groups=[];index=defaultdict(set);nobs=len(obs['anchor']);radius=cfg['radius_spacing']*spacing
    order=np.lexsort((np.arange(nobs),-obs['strength']))
    for i in order:
        ids=[int(j) for j,w in zip(obs['ids'][i],obs['weights'][i]) if j>=0 and w>=cfg['min_id_weight']]
        candidates=set()
        for gid in ids:candidates.update(index[gid])
        possible=[]
        for ci in sorted(candidates):
            first=groups[ci][0];dist=np.linalg.norm(obs['anchor'][i]-obs['anchor'][first])
            if dist<=radius and abs(obs['lift'][i]@obs['lift'][first])>=cfg['lift_cos']:possible.append((dist,ci))
        if possible:ci=min(possible)[1];groups[ci].append(int(i))
        else:ci=len(groups);groups.append([int(i)])
        for gid in ids:index[gid].add(ci)
    centers=g['mu'][gaussian_keep];gtree=cKDTree(centers);scales=g['scale_max'][gaussian_keep]
    accepted=[];reasons=Counter();support_hist=Counter();all_support=[]
    for members in groups:
        members=np.asarray(members);views=np.unique(obs['view'][members]);support_hist[int(len(views))]+=1;all_support.append(len(views))
        if len(views)<cfg['min_views']:reasons['single_or_two_view']+=1;continue
        # One vote per view, avoiding repeated channel samples becoming fake support.
        representatives=[]
        for v in views:
            vi=members[obs['view'][members]==v]
            representatives.append(int(vi[np.argmax(obs['strength'][vi])]))
        ii=np.asarray(representatives);p=np.median(obs['anchor'][ii],axis=0)
        rays=np.asarray([cameras[int(v)].center for v in views])-p;rays/=np.maximum(np.linalg.norm(rays,axis=1,keepdims=True),1e-12)
        angle=float(np.rad2deg(np.arccos(np.clip(rays@rays.T,-1,1))).max())
        if angle<cfg['min_angle_deg']:reasons['camera_diversity']+=1;continue
        dist,near=gtree.query(p,k=min(12,len(centers)));Q=centers[near]-centers[near].mean(0)
        eig,V=np.linalg.eigh(Q.T@Q/max(len(Q),1));pc=V[:,-1]
        plane=obs['plane'][ii];M=plane.T@plane/len(ii)+cfg['pca_weight']*(np.eye(3)-np.outer(pc,pc))
        ew,ev=np.linalg.eigh(M);t=ev[:,0];t*=1 if t[np.argmax(abs(t))]>=0 else -1
        aligns=[]
        for j in ii:
            cam=cameras[int(obs['view'][j])];z=(cam.w2c[:3,:3]@p)+cam.w2c[:3,3];d=cam.w2c[:3,:3]@t
            h=cam.K@z;dh=cam.K@d;direction=(dh[:2]*h[2]-h[:2]*dh[2])/max(h[2]**2,1e-12)
            direction/=max(np.linalg.norm(direction),1e-12);aligns.append(abs(direction@obs['tangent'][j]))
        fraction=float(np.mean(np.asarray(aligns)>=cfg['min_tangent_cos']))
        if fraction<cfg['min_tangent_fraction']:reasons['tangent_inconsistent']+=1;continue
        spread=obs['anchor'][ii]-p;cov=spread.T@spread/len(ii)
        if np.sqrt(np.linalg.eigvalsh(cov).max())>radius:reasons['diffuse_cluster']+=1;continue
        half=float(np.clip(np.median(scales[near]),cfg['half_length_spacing'][0]*spacing,cfg['half_length_spacing'][1]*spacing))
        idset=sorted(set(int(x) for x in obs['ids'][members].ravel() if x>=0))
        sources=sorted(set(map(int,obs['source'][members])))
        channel_scores={str(s):float(np.mean(obs['strength'][members][obs['source'][members]==s])) for s in sources}
        accepted.append(dict(center=p.tolist(),tangent=t.tolist(),half_length=half,support_views=views.tolist(),
            ids=idset,source_tags=sources,channel_scores=channel_scores,covariance=cov.tolist(),
            tangent_confidence=float(1-ew[0]/max(ew.sum(),1e-12)),tangent_agreement=fraction,
            local_pca_anisotropy=float(eig[-1]/max(eig.sum(),1e-12)),max_view_angle_deg=angle,
            observations=len(members),confidence=float(len(views)*fraction),representative_indices=ii.tolist()))
    accepted.sort(key=lambda c:(-c['confidence'],c['ids'][0],*c['center']))
    uncapped=len(accepted);accepted=accepted[:cfg['max_clusters']]
    for i,c in enumerate(accepted):c['cluster_id']=i
    return accepted,dict(observations=nobs,preclusters=len(groups),support_histogram=dict(sorted(support_hist.items())),
        repeat_ge3=sum(n>=3 for n in all_support),accepted_before_cap=uncapped,accepted=len(accepted),
        rejection_reasons=dict(reasons),accepted_support_median=float(np.median([len(c['support_views']) for c in accepted])) if accepted else 0.,
        accepted_source_counts={str(s):sum(s in c['source_tags'] for c in accepted) for s in range(6)})


def linelets(clusters):
    return dict(p=np.asarray([c['center'] for c in clusters],float).reshape(-1,3),
                t=np.asarray([c['tangent'] for c in clusters],float).reshape(-1,3),
                l=np.asarray([c['half_length'] for c in clusters],float),
                confidence=np.asarray([c['confidence'] for c in clusters],float))
