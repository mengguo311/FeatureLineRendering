from runtime import *
from scipy.spatial.transform import Rotation
from core import eval_curve

def update_geometry(raw,cov,oldt,means,tangent,changed):
    rec=raw.copy();outcov=cov.copy();ids=np.flatnonzero(changed)
    if not len(ids): return rec,outcov
    u=unit(oldt[ids]);v=unit(tangent[ids]);cross=np.cross(u,v);sn=np.linalg.norm(cross,axis=1);dot=np.clip(np.sum(u*v,axis=1),-1,1)
    assert (dot>0).all(),'No antipodal geometry rotations'
    rv=cross*(np.arctan2(sn,dot)/np.maximum(sn,1e-30))[:,None]
    rot=Rotation.from_rotvec(rv);R=rot.as_matrix();outcov[ids]=R@cov[ids]@R.transpose(0,2,1)
    oldq=np.stack([raw['rot_'+str(i)][ids] for i in (1,2,3,0)],axis=1)
    newq=(rot*Rotation.from_quat(oldq)).as_quat()[:,[3,0,1,2]]
    for j,k in enumerate(('x','y','z')):rec[k][ids]=means[ids,j]
    for j in range(4):rec['rot_'+str(j)][ids]=newq[:,j]
    return rec,outcov

def build_curve_state(s,a):
    pair=s['piece_control_indices'];P=s['control'][pair];delta=P[:,1]-P[:,0]
    B=np.stack([P[:,0],P[:,0]+delta/3,P[:,0]+2*delta/3,P[:,1]],axis=1)
    n=len(pair);piece=a['internal_piece_id']
    return dict(control=B,degree=np.ones(n,np.uint8),kernel_curve_index=piece.astype(np.int64).copy(),
                kernel_t=s['basis'][:,1].copy(),piece_start=np.arange(n,dtype=np.int64),piece_stop=np.arange(1,n+1,dtype=np.int64))

def apply_curve(curves,start,stop,ids,t,B):
    curves['control'][start]=B;curves['degree'][start]=3;curves['degree'][start+1:stop]=0
    curves['piece_stop'][start]=stop;curves['kernel_curve_index'][ids]=start;curves['kernel_t'][ids]=t

def export_arm(folder,a,s,raw,oldt,means,tangent,curves,ledger,stats):
    folder.mkdir(parents=True,exist_ok=True);fmt,_=renderer_modules()
    changed=(np.linalg.norm(means-a['means'],axis=1)>1e-13)|(np.linalg.norm(tangent-oldt,axis=1)>1e-12)
    rec,cov=update_geometry(raw,a['covariance'],oldt,means,tangent,changed)
    derived={k:v.copy() for k,v in a.items()};derived.update(means=means,covariance=cov,line_kernel_id=np.arange(len(means),dtype=np.int64))
    np.savez_compressed(folder/'gaussians.npz',**derived);fmt.write_ply(folder/'gaussians.ply',rec)
    keep=curves['degree']>0;remap=np.cumsum(keep)-1;index=remap[curves['kernel_curve_index']]
    control=curves['control'][keep];start=curves['piece_start'][keep];stop=curves['piece_stop'][keep]
    piece_first=np.searchsorted(a['internal_piece_id'],np.arange(len(s['piece_control_indices'])))
    count=np.bincount(index,minlength=len(control));assert (count>0).all()
    data=dict(control=control,degree=curves['degree'][keep],kernel_curve_index=index,kernel_t=curves['kernel_t'],source_line_kernel_id=np.arange(len(means),dtype=np.int64),
              source_parent_id=a['primitive_id'],source_piece_id=a['internal_piece_id'],source_arc_t=a['arc_t'],original_piece_start=start,original_piece_stop=stop,
              curve_parent_id=a['primitive_id'][piece_first[start]],source_kernel_offsets=np.r_[0,np.cumsum(count)],
              window_origin=control[:,0],window_pixel_scale=s['pixel'][piece_first[start]],world_space=np.array(True),
              inverse_transform=np.array('world = local * window_pixel_scale + window_origin'),source_GS_ids=np.full(len(means),-1,np.int64))
    np.savez_compressed(folder/'curves.npz',**data)
    ledger=dict(ledger);ledger.update(line_kernel_id=np.arange(len(means),dtype=np.int64),modified=changed,retained=~changed,confidence_known=np.zeros(len(means),bool),source_GS_known=np.zeros(len(means),bool))
    np.savez_compressed(folder/'ledger.npz',**ledger)
    stats.update(modified_kernels=int(changed.sum()),retained_kernels=int((~changed).sum()),kernel_count=len(means),curve_segments=len(control),cubic_segments=int((data['degree']==3).sum()),
                 maximum_displacement_pixel=float((np.linalg.norm(means-a['means'],axis=1)/s['pixel']).max(initial=0)),source_GS='UNKNOWN_NOT_READ',confidence='UNKNOWN',unsupported_new_gaps=0)
    js(folder/'METRICS.json',stats)
    return stats
