"""Independent arithmetic audit from compact raw foreground contribution CSR."""
import json,traceback
import numpy as np
from io_utils import *

def audit_scene(scene):
 verify(OUT/scene/'assets');s=load(OUT/scene/'assets/scorebank.npz');k=json.loads((OUT/'COMPLETENESS.json').read_text())['available_K'];n=len(s['original_ids']);rng=np.random.default_rng(1729)
 chosen=set(rng.choice(np.flatnonzero(s['eligible']),24,replace=False).tolist())
 chosen.update(rng.choice(np.flatnonzero(s['unknown']),8,replace=False).tolist())
 for arm in ('A','B','C','D','E'):
  o=s[arm+'_ordered_ids'];chosen.update(o[:4].tolist());chosen.update(o[-4:].tolist())
 target=np.array(sorted(chosen),np.int32);mapping=np.full(n,-1,np.int32);mapping[target]=np.arange(len(target));num=np.zeros((3,len(target)));fgcost=np.zeros(len(target));offcost=np.zeros(len(target));mass=np.zeros(len(target));views=np.zeros(len(target),np.int32);rows=[]
 for f in frames(scene,'F'):
  folder=OUT/scene/'contributions'/('K'+str(k))/f['key'];z=load(folder/'foreground_csr.npz');stat=load(folder/'statistics.npz');e=load(OUT/scene/'F'/f['key']/'evidence.npz');ray=np.repeat(np.arange(len(z['pixels'])),np.diff(z['indptr']));slot=mapping[z['original_ids']];keep=slot>=0;slot=slot[keep];ray=ray[keep];w=z['weights'][keep].astype(np.float64);a=z['alpha'][ray];px=z['pixels'][ray];frac=w/a
  for c in range(3):np.add.at(num[c],slot,frac*e['omega'][:,:,c].ravel()[px])
  np.add.at(fgcost,slot,frac/max(len(z['pixels']),1)/8)
  off=e['offedge'].ravel()[px];np.add.at(offcost,slot[off],frac[off]/max(int(e['offedge'].sum()),1)/8)
  mass+=stat['raw_mass'][target];views+=(stat['raw_mass'][target]>0)
  captured=np.add.reduceat(np.r_[z['weights'],0.],np.minimum(z['indptr'][:-1],len(z['weights'])))
  # Empty rows must have zero rather than next row's mass; explicit independent correction.
  captured[np.diff(z['indptr'])==0]=0
  bound=float(np.max(captured-z['alpha'],initial=0));assert bound<5e-6
  rows.append(dict(key=f['key'],foreground_mass_alpha_bound_excess=bound,csr_nonzero=int(len(z['weights'])),audit_raw_sha256=sha(folder/'foreground_csr.npz')))
 b=np.divide(num.sum(0),fgcost,out=np.zeros(len(target)),where=fgcost>0)
 errors=dict(B_score=float(np.max(np.abs(b-s['B_score'][target]))),B_major_numerator=float(np.max(np.abs(num.sum(0)-s['B_major_numerator'][target]))),nonedge_cost=float(np.max(np.abs(offcost-s['nonedge_cost'][target]))),foreground_mean=float(np.max(np.abs(fgcost-s['foreground_mean_fraction'][target]))),raw_mass=float(np.max(np.abs(mass-s['raw_mass'][target]))),visible_views=int(np.max(np.abs(views-s['visible_views'][target]))))
 assert errors['B_score']<5e-6 and errors['B_major_numerator']<1e-9 and errors['nonedge_cost']<1e-9 and errors['foreground_mean']<1e-9 and errors['raw_mass']<1e-8 and errors['visible_views']==0
 assert np.all(s['unknown'][target[mass==0]])
 return dict(scene=scene,sampled_original_ids=target.tolist(),count=len(target),errors=errors,rows=rows,pass_status=True,scope='Independent np.add.at accumulation from saved true raw foreground CSR; fullgrid mass/visibility cross-checks stored perview arrays, not independent CUDA traversal')
def stage():
 results=[audit_scene(s) for s in CFG['scenes']];atomic(OUT/'INDEPENDENT_CPU_AUDIT.json',dict(utc=utc(),results=results,all_pass=True));event('CPU_INDEPENDENT_AUDIT_PASS',sampled_IDs={r['scene']:r['count'] for r in results})
if __name__=='__main__':
 try:stage()
 except Exception as e:event('ENGINEERING_STOP',requested_phase='independent_cpu_audit',error=str(e),traceback=traceback.format_exc());raise
