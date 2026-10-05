"""G0: captured raw alphaT vs native fixed-field projection, without rerendering."""
import numpy as np
from scipy import sparse
from io_utils import *

def stage():
 k=json.loads((OUT/'COMPLETENESS.json').read_text())['available_K'];rows=[]
 for scene in CFG['scenes']:
  selection=json.loads((OUT/scene/'assets/selected_ids.json').read_text());n=INPUTS['scenes'][scene]['checkpoint']['qualification']['gaussians']
  for f in frames(scene,'F'):
   z=load(OUT/scene/'contributions'/('K'+str(k))/f['key']/'foreground_csr.npz');d=OUT/scene/'evaluation'/f['key'];verify(d);meta=json.loads((d/'METRICS.json').read_text());q=load(d/'projection.npz')['Q'].reshape(-1,len(meta['fields']))[z['pixels']]
   g=sparse.csr_matrix((z['weights'].astype(np.float64),z['original_ids'],z['indptr']),shape=(len(z['pixels']),n));g.sum_duplicates();fields=np.zeros((n,len(meta['fields'])),np.float64)
   for j,item in enumerate(meta['fields']):fields[np.asarray(selection['arms'][item['arm']]['ordered_original_ids'][:item['count']],np.int32),j]=1
   captured=g@fields;residual=np.maximum(z['alpha']-np.asarray(g.sum(1)).ravel(),0)
   lower=float(np.min(q-captured,initial=0));upper=float(np.max(q-captured-residual[:,None],initial=0));assert lower>=-5e-6 and upper<=5e-6
   rows.append(dict(scene=scene,key=f['key'],fields=len(meta['fields']),captured_alphaT_never_renormalized=True,native_minus_captured_min=lower,residual_bound_excess=upper,allones_max_abs=meta['allones_alpha_max_abs'],field_alpha_depth_exact=meta['attributes_alpha_depth_exact'],native_projection_sha256=sha(d/'projection.npz')))
 atomic(OUT/'NATIVE_CAPTURED_MASS_AUDIT.json',dict(K=k,all24_F_pass=True,rows=rows,scope='CPU CSR sums vs actual full-native selected fields, original all-ray T retained; omission interval uses full original alpha',rounding_bound_atol=5e-6));event('G0_NATIVE_CAPTURED_MASS_PASS',F_count=24)
if __name__=='__main__':stage()
