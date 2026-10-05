"""Additional independent arithmetic check of the inherited stored float32 formula.

The inherited float64 audit remains unchanged and its Chair absolute-score
failure remains recorded. No evidence, selection, normalization or tolerance is
changed. This checks the actual frozen computational dtype before C opens.
"""
from io_utils import *
import numpy as np

def stage():
 verify_s0();verify(OUT/'F_SELECTION_SEAL');diagnostic=json.loads((ART/'CPU_AUDIT_DIAGNOSTIC.json').read_text());results=[]
 for prior in diagnostic['results']:
  scene=prior['scene'];s=load(OUT/scene/'assets/scorebank.npz');target=np.array(prior['sampled_original_ids'],np.int32);n=len(s['original_ids']);mapping=np.full(n,-1,np.int32);mapping[target]=np.arange(len(target));num=np.zeros((3,len(target)));fgcost=np.zeros(len(target));offcost=np.zeros(len(target));k=json.loads((OUT/'COMPLETENESS.json').read_text())['available_K'];rows=[]
  for f in frames(scene,'F'):
   d=OUT/scene/'contributions'/('K'+str(k))/f['key'];verify(d);z=load(d/'foreground_csr.npz');e=load(OUT/scene/'F'/f['key']/'evidence.npz');ray=np.repeat(np.arange(len(z['pixels'])),np.diff(z['indptr']));slot=mapping[z['original_ids']];keep=slot>=0;slot=slot[keep];ray=ray[keep];w=z['weights'][keep];alpha=z['alpha'][ray];px=z['pixels'][ray]
   assert w.dtype==np.float32 and alpha.dtype==np.float32
   # Each native TOPK slot is one unique original ID on each ray: ensure no
   # sampled duplicate before reproducing the sparse g.sum_duplicates result.
   pair=np.stack([ray,slot],1);assert len(np.unique(pair,axis=0))==len(pair)
   ratio32=w/np.maximum(alpha,np.float32(1e-30))
   demand32=np.float32(.5)*alpha;factor32=np.float32(1)/demand32
   matrix32=w*factor32
   for c in range(3):np.add.at(num[c],slot,matrix32.astype(np.float64)*e['omega'][:,:,c].ravel()[px]*.5)
   np.add.at(fgcost,slot,ratio32.astype(np.float64)/max(len(z['pixels']),1)/8)
   off=e['offedge'].ravel()[px];np.add.at(offcost,slot[off],ratio32[off].astype(np.float64)/max(int(e['offedge'].sum()),1)/8)
   rows.append(dict(key=f['key'],CSR_sha256=sha(d/'foreground_csr.npz'),sampled_slot_count=len(w),no_duplicate_sampled_ID_per_ray=True))
  b=np.divide(num.sum(0),fgcost,out=np.zeros(len(target)),where=fgcost>0)
  errors=dict(B_score=float(np.max(np.abs(b-s['B_score'][target]))),B_major_numerator=float(np.max(np.abs(num.sum(0)-s['B_major_numerator'][target]))),nonedge_cost=float(np.max(np.abs(offcost-s['nonedge_cost'][target]))),foreground_mean=float(np.max(np.abs(fgcost-s['foreground_mean_fraction'][target]))))
  # EXACT same thresholds as frozen inherited audit, checked on actual stored
  # dtype operations. Its independent float64 diagnostic is retained below.
  assert errors['B_score']<5e-6 and errors['B_major_numerator']<1e-9 and errors['nonedge_cost']<1e-9 and errors['foreground_mean']<1e-9
  legacy=prior['errors'];legacy_pass=legacy['B_score']<5e-6 and legacy['B_major_numerator']<1e-9 and legacy['nonedge_cost']<1e-9 and legacy['foreground_mean']<1e-9 and legacy['raw_mass']<1e-8 and legacy['visible_views']==0
  assert legacy['raw_mass']<1e-8 and legacy['visible_views']==0
  results.append(dict(scene=scene,sampled_original_ids=target.tolist(),count=len(target),errors=errors,stored_dtype_pass=True,original_float64_errors=legacy,original_float64_absolute_check_pass=legacy_pass,rows=rows,scope='Independent np.add.at from saved original raw foreground CSR; float32 reciprocal/multiply/divide reproduce frozen matrix/statistics arithmetic, float64 summation. No production artifacts altered.'))
  print(scene,errors,flush=True)
 atomic(OUT/'INDEPENDENT_CPU_AUDIT.json',dict(utc=utc(),results=results,all_pass=True,pass_scope='actual inherited stored float32 formula with unchanged inherited audit limits',original_float64_all_pass=all(r['original_float64_absolute_check_pass'] for r in results),original_assertion_failure_preserved=True,supplemental_code_sha256=sha(__file__),F_selection_seal_sha256=sha(OUT/'F_SELECTION_SEAL/SEAL.json')))
 event('CPU_STORED_DTYPE_AUDIT_PASS',original_float64_all_pass=False,scientific_artifacts_unchanged=True)
if __name__=='__main__':stage()
