"""Complete immutable finite-curve seed bank; no old membership locks."""
from free_io import *
import heapq
from scipy.spatial import cKDTree
from free_core import EPS,arc,slice_q,resample,geometry_ok

def load_seeds(c,guard):
 guard('readiness');cp=json.loads(Path(c['seed_checkpoint']).read_text());pc=json.loads(Path(c['seed_predecessor_config']).read_text())
 assert cp['complete'] and cp['stage']=='M4_MERGE_ONLY_NATIVE';assert cp['all_rows']==c['kernel_count']
 assert cp['config_binding']==sha(c['seed_predecessor_config']) and cp['decision_sha256']==pc['decision_sha256'];assert sha(pc['decision_path'])==pc['decision_sha256']
 assert cp['files']['CARRIERS.npz']==sha(c['seed_carriers'])
 with np.load(c['seed_carriers'],allow_pickle=False) as z:a={k:z[k] for k in ('carrier_id','version','valid','baseline','kind','knot_offsets','knots','row_offsets','rows')}
 n=c['kernel_count'];k=c['seed_expected_carriers'];assert a['carrier_id'].shape==(k,) and np.all(np.diff(a['carrier_id'])>0)
 assert a['knots'].shape==(c['seed_expected_knots'],3)
 for offsets,count in [('knot_offsets',len(a['knots'])),('row_offsets',n)]:
  off=a[offsets];assert off.shape==(k+1,) and off[0]==0 and off[-1]==count and np.all(np.diff(off)>=0) and np.issubdtype(off.dtype,np.integer)
 for field in ('version','valid','baseline','kind'):assert a[field].shape==(k,)
 assert np.issubdtype(a['carrier_id'].dtype,np.integer) and np.issubdtype(a['version'].dtype,np.integer)
 assert a['rows'].shape==(n,) and np.issubdtype(a['rows'].dtype,np.integer);np.testing.assert_array_equal(np.sort(a['rows']),np.arange(n))
 owner=np.empty(n,np.int64)
 for j,cid in enumerate(a['carrier_id']):
  if j%512==0:guard('readiness')
  owner[a['rows'][a['row_offsets'][j]:a['row_offsets'][j+1]]]=cid
 with np.load(c['reference_memberships']['v05_M4'],allow_pickle=False) as m:
  np.testing.assert_array_equal(m['line_kernel_id'],np.arange(n));np.testing.assert_array_equal(m['carrier_id'],owner)
 # Ownership checked solely as provenance; no assigned/valid/baseline gate is returned to assignment.
 return a

def context_rows(a,ids):
 wanted=set(map(int,ids));parts=[a['rows'][a['row_offsets'][j]:a['row_offsets'][j+1]] for j,cid in enumerate(a['carrier_id']) if int(cid) in wanted]
 return np.sort(np.concatenate(parts)) if parts else np.array([],np.int64)

def windows(q):
 if len(q)<2 or not np.isfinite(q).all():raise ValueError('nonfinite_or_short_q')
 if np.any(np.linalg.norm(np.diff(q,axis=0),axis=1)<EPS):raise ValueError('degenerate_segment')
 L=arc(q)[-1]
 for k in range(int(np.ceil(L/128))):
  lo=128.*k;hi=min(128.*(k+1),float(L))
  if hi-lo<EPS:continue
  cut=slice_q(q,lo,hi)
  if cut is None:raise ValueError('empty_window')
  yield k,lo,hi,resample(cut)

def compatible_rows(x,t,valid_rows,tree,q,guard=lambda:None):
 hits=[]
 for j,(a,b) in enumerate(zip(q[:-1],q[1:])):
  if j%32==0:guard()
  v=b-a;l=np.linalg.norm(v)
  if l<EPS:continue
  ids=np.asarray(tree.query_ball_point((a+b)/2,l/2+1+EPS,workers=1),np.int64);rr=valid_rows[ids]
  if not len(rr):continue
  u=np.clip((x[rr]-a)@v/(l*l),0,1);dist=np.linalg.norm(x[rr]-a-u[:,None]*v,axis=1);angle=np.degrees(np.arccos(np.clip(np.abs(t[rr]@(v/l)),0,1)));co=dist**2+.25*(angle/30)**2
  hits.append(rr[(dist<=1+EPS)&(angle<=30+EPS)&(co<1)])
 return np.unique(np.concatenate(hits)) if hits else np.array([],np.int64)

def select(coverage,keys,cap=512,guard=lambda:None):
 if not coverage:return [],[],np.array([],np.int64)
 nvox=max((int(v.max())+1 for v in coverage if len(v)),default=0);covered=np.zeros(nvox,bool);heap=[(-len(v),tuple(keys[i]),i) for i,v in enumerate(coverage)];heapq.heapify(heap);chosen=[];gains=[]
 while heap and len(chosen)<cap:
  guard();neg,key,i=heapq.heappop(heap);gain=int(np.count_nonzero(~covered[coverage[i]]));updated=(-gain,key,i)
  if heap and updated>heap[0]:heapq.heappush(heap,updated);continue
  if gain==0:break
  chosen.append(i);gains.append(gain);covered[coverage[i]]=True
 remaining=np.array([np.count_nonzero(~covered[v]) for v in coverage],np.int64)
 return chosen,gains,remaining

def pack_bank(records,qs,coverage):
 qo=[0];co=[0]
 for q,v in zip(qs,coverage):qo.append(qo[-1]+len(q));co.append(co[-1]+len(v))
 return dict(candidate_key=np.asarray([r['key'] for r in records],np.int64).reshape(-1,3),domain_p=np.asarray([r['domain_p'] for r in records],float).reshape(-1,2),old_valid=np.asarray([r['old_valid'] for r in records],bool),old_baseline=np.asarray([r['old_baseline'] for r in records],bool),compatible_kernel_count=np.asarray([r['compatible_kernels'] for r in records],np.int64),knot_offsets=np.asarray(qo,np.int64),q_normalized=np.concatenate(qs) if qs else np.empty((0,3)),coverage_offsets=np.asarray(co,np.int64),coverage_voxel_id=np.concatenate(coverage) if coverage else np.array([],np.int64))

def initialize(c,d,a,guard):
 U=Path(c['unit_root']);out=U/'seed_bank';out.mkdir(parents=True,exist_ok=True)
 vr=np.flatnonzero(d['valid']);tree=cKDTree(d['x'][vr]);voxels,inv=np.unique(np.floor(d['x'][vr]).astype(np.int64),axis=0,return_inverse=True);row_voxel=np.full(len(d['x']),-1,np.int64);row_voxel[vr]=inv
 nz(out/'VOXELS.npz',keys=voxels,original_row_voxel=row_voxel)
 records=[];qs=[];coverage=[];rejected=0;scanned=0
 journal=out/'PROPOSAL_JOURNAL.jsonl'
 try:
  with open(journal,'x') as log:
   for j,cid in enumerate(a['carrier_id']):
    guard();scanned+=1;version=int(a['version'][j]);q=a['knots'][a['knot_offsets'][j]:a['knot_offsets'][j+1]]/d['p']
    try:window_list=list(windows(q))
    except ValueError as exc:
     rejected+=1;log.write(json.dumps(dict(key=[int(cid),version,-1],status='REJECTED',reason=str(exc)))+'\n');continue
    for w,lo,hi,nq in window_list:
     guard();key=(int(cid),version,w);ok,reason=geometry_ok(nq)
     if not ok:
      rejected+=1;log.write(json.dumps(dict(key=key,status='REJECTED',reason=reason,domain_p=[lo,hi]))+'\n');continue
     rr=compatible_rows(d['x'],d['t'],vr,tree,nq,guard);cv=np.unique(row_voxel[rr]);assert np.all(cv>=0)
     item=dict(key=key,domain_p=[lo,hi],old_valid=bool(a['valid'][j]),old_baseline=bool(a['baseline'][j]),compatible_kernels=len(rr),coverage_voxels=len(cv));records.append(item);qs.append(nq);coverage.append(cv)
     log.write(json.dumps(dict(**item,status='BANK_READY',candidate_index=len(records)-1))+'\n')
    if scanned%256==0:log.flush();os.fsync(log.fileno())
   log.flush();os.fsync(log.fileno())
  nz(out/'COMPLETE_BANK.npz',**pack_bank(records,qs,coverage));js(out/'BANK_CHECKPOINT.json',dict(complete=True,carrier_records_scanned=scanned,candidates=len(records),rejected_records=rejected,files={fn:sha(out/fn) for fn in ['VOXELS.npz','PROPOSAL_JOURNAL.jsonl','COMPLETE_BANK.npz']},decision_sha256=c['decision_sha256']))
 except Exception as exc:
  nz(out/'INCOMPLETE_BANK.npz',**pack_bank(records,qs,coverage));js(out/'BANK_FAILURE.json',dict(complete=False,promoted=False,carrier_records_scanned=scanned,candidates_saved=len(records),error=type(exc).__name__+': '+str(exc)));raise
 chosen,gains,remaining=select(coverage,[r['key'] for r in records],512,guard);rank=np.full(len(records),-1,np.int64);rank[chosen]=np.arange(len(chosen));why=np.full(len(records),'UNSELECTED_CAP',dtype='U24');why[remaining==0]='ZERO_MARGINAL';why[chosen]='SELECTED'
 nz(out/'SELECTION.npz',candidate_index=np.asarray(chosen,np.int64),marginal_gain=np.asarray(gains,np.int64),selection_rank=rank,final_marginal=remaining,reason=why)
 events=[];models={}
 for mid,i in enumerate(chosen):
  models[mid]=qs[i].copy();events.append(dict(operation='seed_initialization',model=mid,candidate_index=i,source_carrier_id=records[i]['key'][0],source_version=records[i]['key'][1],window_index=records[i]['key'][2],domain_p=records[i]['domain_p'],marginal_voxels=gains[mid],source_rows_not_locked=True))
 allcov=np.unique(np.concatenate(coverage)) if coverage else np.array([],np.int64)
 summary=dict(seed_family='legacy_finite_q_with_free_kernel_membership',seed_bank_complete=True,seed_count=len(records),carrier_records=scanned,selected_models=len(models),covered_voxels=int(sum(gains)),bank_compatible_voxels=len(allcov),total_valid_voxels=len(voxels),uncovered_valid_voxels=len(voxels)-sum(gains),zero_marginal_unselected=int(np.sum((rank<0)&(remaining==0))),positive_marginal_unselected=int(np.sum((rank<0)&(remaining>0))),truncated=bool(np.any((rank<0)&(remaining>0))),cap=512,events=events)
 js(out/'SELECTION_CHECKPOINT.json',dict(complete=True,files={fn:sha(out/fn) for fn in ['BANK_CHECKPOINT.json','SELECTION.npz']},decision_sha256=c['decision_sha256']))
 return models,len(models),summary
