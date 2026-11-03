"""Paired source increments; full-bin axes and all membership guards unchanged."""
import copy
import numpy as np
import derivative_history_core as dh
from geometry_base import EPS,RAD
from frontier_core import unit
ARMS=('BASE','OBS_HISTORY','PAIRED_HISTORY')

def paired_side(d,evidence):
 bins=evidence['bins'];pid=d['asset']['primitive_id'];parameter=d['asset']['arc_t']
 rows=[np.asarray(b['rows'],np.int64) for b in bins]
 ids=[set(map(int,pid[r])) for r in rows];paired=sorted(ids[0]&ids[1])
 out=dict(known=False,paired_ids=paired,unpaired_ids=[sorted(g-set(paired)) for g in ids],unpaired_rows=[r[~np.isin(pid[r],paired)].tolist() for r in rows],unpaired_sources=[],sources=[],paired_row_counts=[int(np.sum(np.isin(pid[r],paired))) for r in rows],reason='insufficient_paired_rows')
 for g in sorted((ids[0]|ids[1])-set(paired)):
  rr=[r[pid[r]==g] for r in rows]
  out['unpaired_sources'].append(dict(primitive_id=g,rows=[r.tolist() for r in rr],counts=list(map(len,rr)),parameter_ranges=[[float(parameter[r].min()),float(parameter[r].max())] if len(r) else None for r in rr],weight=0,axes=None,increment=None,reason='absent_from_one_bin; retained_in_full_bin_orientation_and_membership'))
 for g in paired:
  rr=[r[pid[r]==g] for r in rows];ranges=[[float(parameter[r].min()),float(parameter[r].max())] for r in rr]
  forward=ranges[0][1]<=ranges[1][0]+EPS;backward=ranges[1][1]<=ranges[0][0]+EPS
  z=dict(primitive_id=g,rows=[r.tolist() for r in rr],counts=list(map(len,rr)),parameter_ranges=ranges,parameter_order='forward' if forward and not backward else 'reverse' if backward and not forward else 'ambiguous',weight=min(map(len,rr)),bins=[],known=False)
  for j,r in enumerate(rr):
   t=d['tangents'][r];t=t/np.linalg.norm(t,axis=1)[:,None];tensor=np.einsum('ni,nj->ij',t,t)/len(t);val,vec=np.linalg.eigh(tensor);val=val[::-1];axis=vec[:,-1];sec=bins[j]['secant']
   b=dict(tensor=tensor.tolist(),eigenvalues=val.tolist(),secant=sec,axis=None,sign=None,known=False,reason='weak_axis')
   if val[0]>EPS and val[0]+EPS>=2*val[1]:
    if sec is None:b['reason']='degenerate_sign_secant'
    else:
     dot=float(axis@np.asarray(sec));b['absolute_sign_dot']=abs(dot)
     if abs(dot)<=EPS:b['reason']='orthogonal_sign'
     else:b.update(known=True,reason='known',sign=1 if dot>0 else -1,axis=(axis*(1 if dot>0 else -1)).tolist())
   z['bins'].append(b)
  z['known']=z['parameter_order']!='ambiguous' and all(b['known'] for b in z['bins'])
  z['reason']='known' if z['known'] else 'ambiguous_parameter_order' if z['parameter_order']=='ambiguous' else 'weak_or_degenerate_axis'
  z['increment']=(np.asarray(z['bins'][0 if evidence['source'] else 1]['axis'])-np.asarray(z['bins'][1 if evidence['source'] else 0]['axis'])).tolist() if z['known'] else None
  out['sources'].append(z)
 if min(out['paired_row_counts'])<3:return out
 if not all(z['known'] for z in out['sources']):out['reason']='invalid_paired_source';return out
 denominator=sum(z['weight'] for z in out['sources'])
 # Source bin order is near/far; donor bin order is first/second.
 increments=[]
 for z in out['sources']:
  increments.append(z['weight']*np.asarray(z['increment']))
 out.update(known=True,reason='known',total_weight=denominator,increment=(sum(increments)/denominator).tolist());return out

def paired_history(d,observed):
 result=dict(eligible=False,reason='paired_history_unknown',evidence='within_primitive_paired_derivative_increments',fallback=False,full_bin_axes_unchanged=True)
 if 'source' not in observed:return result
 # Always retain every paired source explanation, even when full-bin evidence is unknown.
 src=paired_side(d,observed['source']);dst=paired_side(d,observed['donor']);result.update(source=src,donor=dst,gap_p=observed['gap_p'])
 if not(observed['source']['known'] and observed['donor']['known'] and src['known'] and dst['known']):return result
 t0=np.asarray(observed['source']['bins'][0]['axis']);u0=np.asarray(observed['donor']['bins'][0]['axis']);kS=np.asarray(src['increment']);kD=np.asarray(dst['increment']);pred=unit(t0+observed['gap_p']*kS)
 result.update(t0=t0.tolist(),u0=u0.tolist(),kS=kS.tolist(),kD=kD.tolist())
 if pred is None:result['reason']='degenerate_prediction';return result
 angle=float(np.degrees(np.arccos(np.clip(pred@u0,-1,1))));delta=float(np.linalg.norm(kD-kS));ok=angle<=15+EPS and delta<=2*np.sin(7.5*RAD)+EPS
 result.update(eligible=bool(ok),reason='paired_history_pass' if ok else 'paired_history_reject',prediction=pred.tolist(),predicted_angle_deg=angle,curvature_difference=delta);return result

def annotate(d,state,seed,side,lib,guard=lambda:None):
 dh.annotate(d,state,seed,side,lib,guard)
 for z in lib['records']:
  guard();z['paired_history']=paired_history(d,z['observed_history']) if z['common'] else dict(eligible=False,reason='not_common_candidate')
 return lib

def choices(records):
 old=dh.choices(records);out=dict(BASE=old['BASE'],OBS_HISTORY=old['OBS_HISTORY'],PAIRED_HISTORY=None,reason=old['reason'])
 if old['reason']=='selected':out['PAIRED_HISTORY']=next((i for i,z in enumerate(records) if z['common'] and z['paired_history']['eligible']),None)
 return out

def remove_diagnostics(lib):
 out=copy.deepcopy(lib)
 for z in out['records']:z.pop('paired_history',None)
 return out
