"""Sparse original-ID bilinear endpoints and mandatory center-visible receivers.

Every sparse matrix is marked-pixels x original-ID, never a dense H x W x N.
Absent top-K endpoint entries are truncated estimates with retained residuals.
"""
import numpy as np
from scipy.sparse import coo_matrix, csr_matrix

REASONS={0:'BEST_RETAINED_D',1:'NORMAL_UNDEFINED_OR_LOW_CONFIDENCE',
         2:'D_NUMERICAL_FLOOR',3:'SIDE_UNKNOWN_EXCEEDS_D',
         4:'ENDPOINT_OUTSIDE_IMAGE',5:'UNASSIGNABLE_BACKGROUND',255:'NOT_MARKED'}

def sample_sparse(ids,weights,points,full_alpha,count):
    h,w,k=ids.shape;points=np.asarray(points,np.float64);p=len(points)
    y0=np.floor(points[:,0]).astype(np.int64);x0=np.floor(points[:,1]).astype(np.int64)
    fy=points[:,0]-y0;fx=points[:,1]-x0
    rows=[];cols=[];data=[];full=np.zeros(p,np.float64)
    for dy,dx,b in ((0,0,(1-fy)*(1-fx)),(0,1,(1-fy)*fx),(1,0,fy*(1-fx)),(1,1,fy*fx)):
        yy=y0+dy;xx=x0+dx;good=(yy>=0)&(yy<h)&(xx>=0)&(xx<w)&(b>0)
        rr=np.flatnonzero(good);ii=ids[yy[good],xx[good]];ww=weights[yy[good],xx[good]]
        valid=(ii>=0)&(ii<count)&(ww>0)
        rows.append(np.broadcast_to(rr[:,None],ii.shape)[valid]);cols.append(ii[valid])
        data.append((ww.astype(np.float64)*b[good,None])[valid])
        full[good]+=b[good]*full_alpha[yy[good],xx[good]]
    mat=coo_matrix((np.concatenate(data),(np.concatenate(rows),np.concatenate(cols))),shape=(p,count)).tocsr()
    mat.sum_duplicates();mat.sort_indices()
    residual=np.maximum(0,full-np.asarray(mat.sum(axis=1)).ravel())
    return mat,residual

def _row_max(mat):
    # CSR indices sorted by original ID. np.argmax takes the first exact tie.
    n=mat.shape[0];ids=np.full(n,-1,np.int32);values=np.zeros(n,np.float64)
    for j in range(n):
        a,b=mat.indptr[j:j+2]
        if a<b:
            best=a+int(np.argmax(mat.data[a:b]));values[j]=mat.data[best];ids[j]=mat.indices[best]
    return ids,values

def assign(ids,weights,full_alpha,line,normal_xy,confidence,count,delta=2.,numerical_floor=2e-6,normal_floor=.22):
    h,w,k=ids.shape;p=np.column_stack(np.nonzero(line));q=len(p)
    if ids.min()<-1 or ids.max()>=count:raise ValueError('not original IDs')
    normal=normal_xy[line].astype(np.float64)[:,::-1] # old xy normal -> array yx
    norm=np.linalg.norm(normal,axis=1)
    normal_ok=np.isfinite(norm)&(norm>1e-8)&(confidence[line]>=normal_floor)
    normal=np.nan_to_num(normal)/np.maximum(np.nan_to_num(norm),1e-8)[:,None]
    minus=p-delta*normal;plus=p+delta*normal
    center,_=sample_sparse(ids,weights,p,full_alpha,count)
    a,ra=sample_sparse(ids,weights,minus,full_alpha,count)
    b,rb=sample_sparse(ids,weights,plus,full_alpha,count)
    difference=abs(a-b);difference.eliminate_zeros();difference.sort_indices()
    # Source + sides form candidate union. Intersect with strictly positive
    # center alpha*T for the primary receiver; endpoint-only IDs are diagnostic.
    visible=center.copy();visible.data[:]=1
    receiver_D=difference.multiply(visible).tocsr();receiver_D.sort_indices()
    did,dmax=_row_max(receiver_D);cid,cmax=_row_max(center)
    eid,emax=_row_max(difference)
    bound=ra+rb
    endpoint_inside=np.all((minus>=0)&(minus<np.array([h-1,w-1])),1)&np.all((plus>=0)&(plus<np.array([h-1,w-1])),1)
    reason=np.zeros(q,np.uint8)
    reason[bound>dmax+numerical_floor]=3
    reason[dmax<=numerical_floor]=2
    reason[~endpoint_inside]=4
    reason[~normal_ok]=1
    valid=(cid>=0)&(cmax>0);reason[~valid]=5
    winner=np.where(reason==0,did,cid).astype(np.int32);winner[~valid]=-1
    winweight=np.asarray(center[np.arange(q),np.maximum(winner,0)]).ravel()
    winD=np.asarray(receiver_D[np.arange(q),np.maximum(winner,0)]).ravel()
    winweight[~valid]=0;winD[~valid]=0
    winner_map=np.full((h,w),-1,np.int32);winner_map[line]=winner
    center_map=np.full((h,w),-1,np.int32);center_map[line]=cid
    fallback=np.full((h,w),255,np.uint8);fallback[line]=reason
    nofallback=np.where(reason==0,winner,-1).astype(np.int32)
    counts=np.bincount(winner[valid],minlength=count).astype(np.int64)
    center_counts=np.bincount(cid[valid],minlength=count).astype(np.int64)
    nofallback_counts=np.bincount(nofallback[nofallback>=0],minlength=count).astype(np.int64)
    if counts.sum()!=valid.sum() or np.any(winweight[valid]<=0):raise AssertionError('mandatory receiver failed')
    return dict(points=p.astype(np.int32),winner_map=winner_map,center_map=center_map,fallback_map=fallback,
        counts=counts,center_counts=center_counts,nofallback_counts=nofallback_counts,
        selected_center_weight=winweight.astype(np.float32),selected_D=winD.astype(np.float32),
        largest_receiver_D=dmax.astype(np.float32),endpoint_best_id=eid,endpoint_best_D=emax.astype(np.float32),
        unknown_bound=bound.astype(np.float32),normal_ok=normal_ok,center_max_weight=cmax.astype(np.float32),
        unassignable=int((~valid).sum()),endpoint_only_best=(eid>=0)&(np.asarray(center[np.arange(q),np.maximum(eid,0)]).ravel()<=0),
        reliable_D=reason==0)

def aggregate(records,count):
    keys=[r[0] for r in records]
    if len(keys)!=len(set(keys)):raise ValueError('duplicate frozen camera')
    c=np.stack([r[1] for r in records]);den=np.array([r[2] for r in records],np.float64)
    if c.shape[1]!=count or np.any(c<0):raise ValueError('original-N counter invalid')
    return dict(per_view_counts=c,raw_frequency=c.sum(0,dtype=np.int64),
        view_count=(c>0).sum(0).astype(np.int16),view_normalized=(c/np.maximum(den[:,None],1)).sum(0))

def rank_ids(raw,views):
    live=np.flatnonzero(raw>0)
    return live[np.lexsort((live,-views[live],-raw[live]))].astype(np.int32)
