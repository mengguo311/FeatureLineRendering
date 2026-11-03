"""Finite observed-support carriers and original-kernel axial port evidence."""
import copy
from port_paths import Leaf
from frontier_core import at,unit
from frontier_loader import local_validator
from geometry_base import *
from observation_oracle import ObservationOracle,port_join

def clipped_leaf(old):
 new=copy.copy(old);new.q=old.q.copy();new.intervals=old.intervals.copy();receipt=dict(carrier_id=old.cid,version=int(old.version),status='ready')
 def fail(why):new.valid=False;receipt['status']=why;return new,receipt
 if not old.valid:return fail('original_invalid')
 if len(old.q)<2 or not np.isfinite(old.q).all():return fail('invalid_original_geometry')
 raw=np.asarray(old.intervals);L=float(arc(old.q)[-1]);receipt['original_length_p']=L
 if not raw.size or not np.isfinite(raw).all():return fail('empty_or_nonfinite_support')
 if raw.min() < -EPS or raw.max()>L+EPS:return fail('support_out_of_domain')
 iv=union_intervals(raw)[0];clamped=np.clip(iv,0,L);receipt['clamped_endpoint_count']=int(np.sum(clamped!=iv));receipt['max_clamp_p']=float(np.max(abs(clamped-iv),initial=0));receipt['raw_support_bounds_p']=[float(iv.min()),float(iv.max())]
 a=float(clamped[0,0]);b=float(clamped[-1,1]);receipt.update(start_p=a,end_p=b)
 if b-a<=EPS:return fail('degenerate_support')
 ss=arc(old.q);new.q=clean(np.vstack([at(old.q,a),old.q[(ss>a)&(ss<b)],at(old.q,b)]));new.intervals=clamped-a
 if len(new.q)<2:return fail('degenerate_support')
 return new,receipt

def port_evidence(leaf,port,ss,tangents):
 L=float(arc(leaf.q)[-1]);distance=ss if port==0 else L-ss
 norm=np.linalg.norm(tangents,axis=1);valid=np.isfinite(tangents).all(1)&np.isfinite(norm)&(norm>0)
 pick=np.flatnonzero(valid&(distance>=-EPS)&(distance<=2+EPS));bins=np.floor(np.maximum(0,distance[pick])).astype(np.int64)
 outward=unit(leaf.q[0]-leaf.q[1] if port==0 else leaf.q[-1]-leaf.q[-2])
 z=dict(known=False,reason='insufficient_derivatives',rows=leaf.rows[pick].tolist(),bins=bins.tolist(),distance_from_port_p=distance[pick].tolist(),q_obs_outward=None if outward is None else outward.tolist())
 if len(pick)<3:return z
 tt=tangents[pick]/norm[pick,None];tensor=np.mean([np.einsum('ni,nj->ij',tt[bins==b],tt[bins==b])/np.sum(bins==b) for b in np.unique(bins)],axis=0)
 values,vectors=np.linalg.eigh(tensor);values=values[::-1];axis=vectors[:,-1];z['eigenvalues']=values.tolist()
 if values[0]<=EPS or values[0]+EPS<2*values[1]:z['reason']='weak_axis';return z
 if outward is None:z['reason']='degenerate_sign';return z
 dot=float(axis@outward);z['unsigned_sign_dot']=abs(dot)
 if abs(dot)<=EPS:z['reason']='orthogonal_sign';return z
 sign=1 if dot>0 else -1;z.update(known=True,reason='known',axis=(axis*sign).tolist(),sign=sign)
 return z

def observations(d,guard):
 out=dict(d);out['original_leaves']=d['leaves'];out['leaves']={};ports={};receipts=[]
 validate=local_validator(d,d['p'])
 for index,(cid,old) in enumerate(sorted(d['leaves'].items())):
  if index%64==0:guard()
  leaf,r=clipped_leaf(old);out['leaves'][cid]=leaf
  if leaf.valid:
   ok,why=validate(leaf);r['all_member_check']=why;r['all_member_check_pass']=ok
   if not ok:leaf.valid=False;r['status']='observed_leaf_residual_tangent'
  if leaf.valid:
   ss=project(d['asset']['means'][leaf.rows]/d['p'],leaf.q)[0]
   for port in (0,1):
    z=port_evidence(leaf,port,ss,d['tangents'][leaf.rows]);rawdir=unit(old.q[0]-old.q[1] if port==0 else old.q[-1]-old.q[-2]);z['original_q_outward']=None if rawdir is None else rawdir.tolist();ports[(cid,port)]=z
  else:
   for port in (0,1):ports[(cid,port)]=dict(known=False,reason=r['status'],rows=[],bins=[])
  receipts.append(r)
 out['ports']=ports;out['observation_receipts']=receipts
 return out
