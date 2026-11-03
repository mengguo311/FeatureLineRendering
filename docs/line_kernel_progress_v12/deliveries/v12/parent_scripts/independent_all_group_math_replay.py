from pathlib import Path
import os,sys,json,importlib.util,hashlib,time
sys.dont_write_bytecode=True
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='2'
if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import numpy as np
u=Path(sys.argv[1]);r=Path(sys.argv[2]);dest=Path(sys.argv[3]);dest.mkdir(exist_ok=True,parents=True)
c=json.loads((r/'WINDOW.json').read_text());sc=json.loads((r/'SOURCE_CONFIG_EXTRACT.json').read_text());old=Path(c['old_output'])/'units/unit_001';snap=old/'source_snapshot';sys.path.insert(0,str(snap))
spec=importlib.util.spec_from_file_location('independent_v11_core',snap/'core.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def load(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
a=load(u/'ORIGINAL_GAUSSIANS.npz');b=load(u/'FULL_POSITION_ONLY_GAUSSIANS.npz');m=load(u/'MEMBERSHIP.npz');base=load(Path(c['input_stage'])/'MEMBERSHIP.npz');assert m.keys()==base.keys() and all(m[k].shape==base[k].shape and m[k].dtype==base[k].dtype and m[k].tobytes()==base[k].tobytes() for k in m)
assert hashlib.sha256((u/'ORIGINAL_GAUSSIANS.npz').read_bytes()).hexdigest()==hashlib.sha256(Path(sc['gaussians']).read_bytes()).hexdigest()
edge=m['edge_id'];p=float(sc['p']);ids=np.unique(edge[edge>=0]);rec=[];bad=[];start=time.monotonic()
for gid in ids:
 rows=np.flatnonzero(edge==gid);local={k:a[k][rows].copy() for k in ['means','covariance']}
 try:
  q=mod.collapse(local,np.arange(len(rows)),p)['position_only']['means'];same=q.dtype==b['means'].dtype and q.tobytes()==b['means'][rows].tobytes();item=dict(edge_id=int(gid),kernels=len(rows),expected='SUCCESS',exact_math_replay=same,max_mean_difference=float(np.abs(q-b['means'][rows]).max()))
 except (ValueError,np.linalg.LinAlgError) as exc:
  same=a['means'][rows].tobytes()==b['means'][rows].tobytes();item=dict(edge_id=int(gid),kernels=len(rows),expected='NUMERIC_SKIP',reason=str(exc),retained_original=same)
 if not same:bad.append(item)
 rec.append(item)
assert len(rec)==3655 and sum(x['kernels'] for x in rec)==127152
rows=np.flatnonzero(edge==30579);v11=load(old/'POSITION_ONLY_GAUSSIANS.npz');reference=a['means'][rows].shape==v11['means'][rows].shape and b['means'][rows].tobytes()==v11['means'][rows].tobytes()
res=dict(groups=len(rec),member_rows=sum(x['kernels'] for x in rec),mismatch_groups=bad,all_group_math_exact=not bad,numerically_undefined_groups=sum(x['expected']=='NUMERIC_SKIP' for x in rec),group30579_same_saved_v11_position_only=reference,source_membership_all_arrays_bitwise_equal=True,original_npz_matches_canonical_encoded_sha256=True,p_world=p,elapsed_seconds=time.monotonic()-start,groups_replayed=rec)
(dest/'INDEPENDENT_ALL_GROUP_MATH_REPLAY.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k!='groups_replayed'}));assert not bad and reference
