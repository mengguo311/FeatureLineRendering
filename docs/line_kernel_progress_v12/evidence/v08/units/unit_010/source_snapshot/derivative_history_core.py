"""Original-kernel derivative history only; shared geometry and membership untouched."""
import numpy as np
from geometry_base import arc,project,extended_s,EPS,RAD
from frontier_core import at,unit,choices as secant_choices
from switch_core import assemble
ARMS=('BASE','SECANT_HISTORY','OBS_HISTORY')

def evidence(d,rows,q,source,attachment,connectors):
 rows=np.unique(np.asarray(list(rows),np.int64));q=np.asarray(q,float);L=float(arc(q)[-1]);x=d['asset']['means'][rows]/d['p'];t=d['tangents'][rows]
 if len(rows):s,_,_,segments,_=project(x,q);es=extended_s(x,q)[0]
 else:s=es=np.empty(0);segments=np.empty(0,int)
 norm=np.linalg.norm(t,axis=1);valid=np.isfinite(t).all(1)&np.isfinite(norm)&(norm>0)
 domain=np.isfinite(es)&(es>=-EPS)&(es<=L+EPS)
 inside=np.zeros(len(rows),bool)
 for a,b in connectors:inside|=(s>min(a,b))&(s<max(a,b))
 coordinate=L-s if source else s-attachment;available=L if source else L-attachment
 out=dict(length_p=L,attachment_p=float(attachment),available_length_p=float(available),known=False,source=bool(source),connector_intervals_p=connectors,exclusions=dict(invalid_derivative=rows[~valid].tolist(),finite_domain=rows[~domain].tolist(),connector_interior=rows[inside].tolist(),outside_history_bins=rows[(coordinate<0)|(coordinate>2)].tolist()),bins=[])
 for j in (0,1):
  mask=valid&domain&~inside&(coordinate>=j)&((coordinate<1) if j==0 else (coordinate<=2))
  picked=np.flatnonzero(mask);tt=t[picked]/norm[picked,None]
  binq=[L-j-1,L-j] if source else [attachment+j,attachment+j+1]
  secant=unit(at(q,binq[1])-at(q,binq[0])) if available>=2-EPS else None
  z=dict(index=j,bounds_p=[j,j+1],upper_inclusive=j==1,rows=rows[picked].tolist(),count=len(picked),coordinates_p=coordinate[picked].tolist(),projection_s_p=s[picked].tolist(),extended_s_p=es[picked].tolist(),projection_segments=segments[picked].tolist(),centers_p=x[picked].tolist(),directed_q_bin_p=binq,known=False,reason='insufficient_rows',tensor=None,eigenvalues=None,axis=None,sign=None,secant=None if secant is None else secant.tolist())
  if len(picked):
   tensor=np.einsum('ni,nj->ij',tt,tt)/len(tt);values,vectors=np.linalg.eigh(tensor);values=values[::-1];axis=vectors[:,-1];z.update(tensor=tensor.tolist(),eigenvalues=values.tolist())
  if available<2-EPS:z['reason']='insufficient_finite_history'
  elif len(picked)<3:pass
  elif values[0]<=EPS or values[0]+EPS<2*values[1]:z['reason']='weak_axis'
  elif secant is None:z['reason']='degenerate_sign_secant'
  else:
   dot=float(axis@secant);z['absolute_sign_dot']=abs(dot)
   if abs(dot)<=EPS:z['reason']='orthogonal_sign'
   else:
    sign=1 if dot>0 else -1;z.update(known=True,reason='known',sign=sign,axis=(axis*sign).tolist())
  out['bins'].append(z)
 out['known']=all(z['known'] for z in out['bins']);return out

def member_rows(d,chain):return np.unique(np.concatenate([d['leaves'][i].rows for i,_ in chain]))

def observed_history(d,state,seed,side,z):
 q=np.asarray(state['curves'][seed]);a=q if side else q[::-1];L=float(arc(q)[-1]);connectors=state['metrics'][seed].get('unsupported_connectors_p',[])
 if not side:connectors=[[L-b,L-a] for a,b in connectors[::-1]]
 src=evidence(d,member_rows(d,state['chains'][seed]),a,True,0.,connectors)
 relay=z['relay']
 if z['relation']=='overlap':
  leaf=d['leaves'][z['donor']];b=leaf.q[::-1] if z['reverse'] else leaf.q;s=z['attachment_s_oriented_p'];donorconnect=[];gap=0.
 else:
  cid,rev=relay[0];first=d['leaves'][cid].q[::-1] if rev else d['leaves'][cid].q
  b,donorconnect=assemble(d,first,relay[1:]);s=0.;gap=z['gap']
 dst=evidence(d,member_rows(d,relay),b,False,s,donorconnect)
 result=dict(eligible=False,reason='observed_history_unknown',source=src,donor=dst,gap_p=float(gap),evidence='original_control_derivative_axes',secant_fallback=False)
 if not(src['known'] and dst['known']):return result
 tm=np.asarray(src['bins'][1]['axis']);t0=np.asarray(src['bins'][0]['axis']);u0=np.asarray(dst['bins'][0]['axis']);u1=np.asarray(dst['bins'][1]['axis']);k=t0-tm;pred=unit(t0+gap*k)
 if pred is None:result['reason']='degenerate_prediction';return result
 angle=float(np.degrees(np.arccos(np.clip(pred@u0,-1,1))));delta=float(np.linalg.norm(u1-u0-k));ok=angle<=15+EPS and delta<=2*np.sin(7.5*RAD)+EPS
 result.update(eligible=bool(ok),reason='observed_history_pass' if ok else 'observed_history_reject',predicted_angle_deg=angle,curvature_difference=delta,t_minus=tm.tolist(),t0=t0.tolist(),k=k.tolist(),u0=u0.tolist(),u1=u1.tolist())
 return result

def annotate(d,state,seed,side,lib,guard=lambda:None):
 for z in lib['records']:
  guard();z['observed_history']=observed_history(d,state,seed,side,z) if z['common'] else dict(eligible=False,reason='not_common_candidate')
 return lib

def choices(records):
 old=secant_choices(records);out=dict(BASE=old['BASE'],SECANT_HISTORY=old['HISTORY'],OBS_HISTORY=None,reason=old['reason'])
 if old['reason']=='selected':out['OBS_HISTORY']=next((i for i,z in enumerate(records) if z['common'] and z['observed_history']['eligible']),None)
 return out

def remove_diagnostics(lib):
 import copy
 out=copy.deepcopy(lib)
 for z in out['records']:z.pop('observed_history',None)
 return out
