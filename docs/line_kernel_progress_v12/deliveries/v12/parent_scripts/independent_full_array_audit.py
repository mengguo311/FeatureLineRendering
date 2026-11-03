from pathlib import Path
import os,sys,json,hashlib
sys.dont_write_bytecode=True
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='2'
if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import numpy as np
u=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
def load(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
def same(a,b):return a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
a=load(u/'ORIGINAL_GAUSSIANS.npz');b=load(u/'FULL_POSITION_ONLY_GAUSSIANS.npz');assert a.keys()==b.keys();m=load(u/'MEMBERSHIP.npz');edge=m['edge_id'];assert len(edge)==len(a['means'])==279616
unknown=edge<0;assigned=~unknown;assert int(unknown.sum())==152464 and int(assigned.sum())==127152
unchanged_fields={k:same(a[k],b[k]) for k in a if k!='means'};assert all(unchanged_fields.values());assert same(a['means'][unknown],b['means'][unknown]);assert a['means'].dtype==b['means'].dtype and a['means'].shape==b['means'].shape;assert np.isfinite(b['means']).all()
changed=np.any(a['means'].view(np.uint64).reshape(len(edge),-1)!=b['means'].view(np.uint64).reshape(len(edge),-1),axis=1) if a['means'].dtype==np.float64 else np.any(a['means']!=b['means'],axis=1)
assert not changed[unknown].any();ids,counts=np.unique(edge[assigned],return_counts=True)
records=[]
for gid,n in zip(ids,counts):
 row=np.flatnonzero(edge==gid);records.append(dict(edge_id=int(gid),kernels=int(n),changed=int(changed[row].sum()),max_displacement_world=float(np.linalg.norm(b['means'][row]-a['means'][row],axis=1).max())))
assert sum(x['kernels'] for x in records)==127152 and len(records)==3655
res=dict(all_rows=len(edge),all_groups_accounted=len(records),assigned=int(assigned.sum()),unknown=int(unknown.sum()),changed_means=int(changed.sum()),unknown_changed=int(changed[unknown].sum()),nonmean_fields_bitwise_equal=unchanged_fields,all_new_means_finite=True,membership_sha256=sha(u/'MEMBERSHIP.npz'),original_sha256=sha(u/'ORIGINAL_GAUSSIANS.npz'),derived_sha256=sha(u/'FULL_POSITION_ONLY_GAUSSIANS.npz'),groups_with_changes=sum(x['changed']>0 for x in records),group_records=records)
(out/'INDEPENDENT_FULL_ARRAY_AUDIT.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k!='group_records'}))
