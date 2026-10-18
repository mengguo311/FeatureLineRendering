from env import *
from experiment import ARMS,build_data,result,old_result
from coupling import labels

def calculate(s,arm):
 a=npz(R/'B'/s/arm/'fit/GRAPH.npz');q=a['probability'];i,j,w=a['i'],a['j'],a['weight'];degree=np.bincount(np.r_[i,j],weights=np.r_[w,w],minlength=len(q));neighbor=np.zeros_like(q)
 for k in range(q.shape[1]):neighbor[:,k]=np.bincount(np.r_[i,j],weights=np.r_[w*q[j,k],w*q[i,k]],minlength=len(q))
 data=[build_data(s,v,arm) for v in [DEV[s],AUX[s]]];rows=[];arrays={};offset=0
 for d in data:
  v=d['view'];n=len(d['world']);ids=np.flatnonzero(d['original_seeds']!=d['seeds']);gid=ids+offset;old=d['original_seeds'][ids];K=q.shape[1];g=a['gamma'][gid];deg=degree[gid];den=g+deg;mix=np.zeros((len(gid),K));ok=den>0;mix[ok]=(neighbor[gid][ok]+g[ok,None]*a['prior'][gid][ok])/den[ok,None];err=np.max(np.abs(mix-q[gid])) if len(ids) else 0
  other=AUX[s] if v==DEV[s] else DEV[s];e=npz(R3/'crossfit'/s/(other+'_TO_'+v)/'RESULT.npz');cross=np.zeros(d['mask'].shape,np.uint8);cross[e['target_uv'][:,1],e['target_uv'][:,0]]=e['predicted'];cp=cross[d['mask']][ids];new=labels(q[gid]);ap=labels(d['unary'][ids]);ap[~d['accepted'][ids]]=0;uf=np.divide(g,den,out=np.zeros_like(g),where=den>0)
  rows.append(dict(scene=s,view=v,arm=arm,withdrawn=len(ids),crossfit_known_contradictions=int(((cp>0)&(cp!=old)).sum()),pooled_prior_accepted_original=int((ap==old).sum()),pooled_prior_accepted_other=int(((ap>0)&(ap!=old)).sum()),pooled_prior_unknown=int((ap==0).sum()),final_original=int((new==old).sum()),final_other=int(((new>0)&(new!=old)).sum()),final_unknown=int((new==0).sum()),final_matches_crossfit_contradiction=int(((cp>0)&(cp!=old)&(new==cp)).sum()),unary_fraction_quantiles=np.quantile(uf,[0,.5,.9,1]).tolist() if len(uf) else [],equilibrium_max_absolute_error=float(err)))
  arrays[v]=dict(node_id=ids,uv=d['uv'][ids],original=old,crossfit=cp,pooled=ap,final=new,probability=q[gid],neighbor_probability=np.divide(neighbor[gid],deg[:,None],out=np.zeros_like(mix),where=deg[:,None]>0),unary_fraction=uf,equilibrium=mix);offset+=n
 return rows,arrays

def main():
 p=R/'mechanism_audit'
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(exist_ok=True);js(p/'DEFINITION.json',dict(utc=now(),purpose='post-pilot diagnostic, no algorithm/threshold alteration',equation='at free seed: q=(sum_j w_ij*q_j+gamma*u)/(degree+gamma)',no_GT=True,scope='all withdrawn original hard seeds, same policy and random'))
 rows=[]
 for s in SCENES:
  for arm in ARMS:
   rr,aa=calculate(s,arm);rows.extend(rr)
   for v,ar in aa.items():np.savez_compressed(p/(s+'_'+arm+'_'+v+'.npz'),**ar)
 js(p/'COUNTS.json',rows);seal(p);print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
