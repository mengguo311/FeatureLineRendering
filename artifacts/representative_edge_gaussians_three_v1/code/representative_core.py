"""CPU evidence and fixed original-ID weighted coverage; no geometric recovery."""
import heapq
import numpy as np
from scipy import ndimage as ndi
from scipy import sparse
import legacy_core
CLASSES=('color','geometry','outline')
BASE=dict(depth_field='median_depth',interior_alpha=.5,foreground_alpha=.08,interior_erosion_pixels=2,nms_step_pixels=1.)
def multiscale(raw,sigmas=(.8,1.6,3.2)):
    return np.stack([legacy_core.evidence_fields(raw,dict(BASE,gaussian_sigma=s))['magnitude'] for s in sigmas])
def multiscale_fields(raw,sigmas=(.8,1.6,3.2)):
    return [legacy_core.evidence_fields(raw,dict(BASE,gaussian_sigma=s)) for s in sigmas]
def split_scales(responses,threshold=.1,radius=2):
    active=responses>=threshold
    major=np.zeros_like(responses[0])
    for c in range(3):
        dil=[ndi.distance_transform_edt(~active[s,:,:,c])<=radius if active[s,:,:,c].any() else np.zeros(active.shape[1:3],bool) for s in range(3)]
        for s in range(3):
            persists=active[s,:,:,c] & np.logical_or.reduce([dil[t] for t in range(3) if t!=s])
            major[:,:,c]=np.maximum(major[:,:,c],responses[s,:,:,c]*persists)
    fine=responses[0]*(responses[0]>=threshold)
    fine_persistent=np.zeros_like(active[0])
    for c in range(3):
        other=[ndi.distance_transform_edt(~active[t,:,:,c])<=radius if active[t,:,:,c].any() else np.zeros(active.shape[1:3],bool) for t in (1,2)]
        fine_persistent[:,:,c]=active[0,:,:,c] & (other[0]|other[1])
    detail=fine*~fine_persistent
    return major.astype(np.float32),detail.astype(np.float32)
def chunks(e,spatial=32,min_component=3):
    labels,n=ndi.label(e>0,structure=np.ones((3,3),bool));sizes=np.bincount(labels.ravel());valid=(labels>0)&(sizes[labels]>=min_component)
    y,x=np.where(valid);out=np.zeros(e.shape,np.int32);w=np.zeros(e.shape,np.float32)
    if len(y):
        key=np.stack([labels[y,x],y//spatial,x//spatial],1)
        _,inv=np.unique(key,axis=0,return_inverse=True);out[y,x]=inv+1
        mass=np.bincount(inv,weights=e[y,x]);w[y,x]=e[y,x]/mass[inv]/len(mass)
    return out,w,dict(components=int(n),retained_components=int(np.sum(sizes[1:]>=min_component)),small_components=int(np.sum(sizes[1:]<min_component)),chunks=int(out.max()),pixels=int(valid.sum()),all_ridge_pixels=int((e>0).sum()))
def evidence(raw,norm,cfg):
    fields=multiscale_fields(raw,cfg['sigmas_pixels'])
    responses=np.stack([np.clip(f['magnitude']/np.array(norm[s],np.float32),0,1)*f['nms'] for s,f in enumerate(fields)])
    major,detail=split_scales(responses,cfg['evidence_threshold'],cfg['persistence_radius_pixels'])
    result=dict(fine=(responses[0]*(responses[0]>=cfg['evidence_threshold'])).astype(np.float32),major=major,detail=detail)
    ch=[];ww=[];meta={}
    for c,name in enumerate(CLASSES):
        ids,w,m=chunks(major[:,:,c],cfg['chunk_spatial_pixels'],cfg['min_component_pixels']);ch.append(ids);ww.append(w);meta[name]=m
    result['chunks']=np.stack(ch,-1);result['omega']=np.stack(ww,-1)/24
    union=(major.max(-1)>0)|(detail.max(-1)>0)
    result['offedge']=(raw['alpha']>=cfg['foreground_alpha']) & (ndi.distance_transform_edt(~union)>cfg['nonedge_band_pixels']) if union.any() else raw['alpha']>=cfg['foreground_alpha']
    return result,meta

def marginal(a,omega,residual,j):
    s,e=a.indptr[j:j+2];rows=a.indices[s:e]
    return float(np.dot(omega[rows],np.minimum(a.data[s:e],residual[rows])))
def greedy(a,omega,cost,eligible,max_count,lam,progress=None):
    a=sparse.csc_matrix(a);a.sort_indices();residual=np.ones(a.shape[0],np.float64)
    active=np.flatnonzero(eligible);initial=np.asarray(a.minimum(1).T@omega).ravel()-lam*cost
    heap=[(-float(initial[j]),int(j)) for j in active];heapq.heapify(heap)
    ids=[];gains=[];utilities=[];u=0.;attempts=0
    while heap and len(ids)<max_count:
        _,j=heapq.heappop(heap);attempts+=1
        raw=marginal(a,omega,residual,j);g=raw-lam*cost[j]
        if heap and g < -heap[0][0]-1e-14:
            heapq.heappush(heap,(-g,j));continue
        if g<=1e-15:break
        ids.append(j);gains.append(g);u+=raw;utilities.append(u)
        s,e=a.indptr[j:j+2];r=a.indices[s:e];residual[r]=np.maximum(residual[r]-a.data[s:e],0)
        if progress and len(ids)%250==0:progress(len(ids),u,attempts)
    return np.array(ids,np.int32),np.array(gains,np.float64),np.array(utilities,np.float64)
def prefix_curve(a,omega,ids):
    a=sparse.csc_matrix(a);residual=np.ones(a.shape[0],np.float64);u=0.;curve=[]
    for j in ids:
        u+=marginal(a,omega,residual,int(j));s,e=a.indptr[j:j+2];r=a.indices[s:e];residual[r]=np.maximum(residual[r]-a.data[s:e],0);curve.append(u)
    return np.array(curve,np.float64)
