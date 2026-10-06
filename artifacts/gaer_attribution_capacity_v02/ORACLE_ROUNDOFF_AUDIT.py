"""New full-N oracle coefficient cross-check, native gradient vs FP64 replay."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/gaer_attribution_capacity_v02'))
import numpy as np
import torch
from runtime import *
from binding import backend,scene_io
from operators import NativeWeights,query_extension
from certificate import replay

def main():
 torch.set_num_threads(2);P=json.loads((ART/'PROTOCOL.json').read_text());module=backend();qext=query_extension()
 for scene,record in P['scenes'].items():
  model=scene_io.load_model(record)
  def calculate():
   original=np.load(ART/'downloads'/scene/'fullN_linear_oracles.npz');b64=[];rows=[]
   for j,v in enumerate(record['views']):
    guard(scene+'_oracle_roundoff_'+v['key']);a=np.load(v['source']);op=NativeWeights(module,scene_io.make_settings(module,v['camera']),model);E=torch.tensor(a['line_binary'].astype(np.float64),device='cuda');q,absq,_=replay(op,E,True,qext);alpha,_,_=replay(op,torch.ones(record['count'],device='cuda',dtype=torch.float64),False,qext);qq=q.cpu().numpy();b64.append(qq);diff=np.abs(original['per_view_fullT_line_b'][j]-qq);alphaerr=float(np.abs(alpha.cpu().numpy().reshape(800,800)-a['alpha']).max());assert alphaerr<3e-6;gamma=(640000*2**-52)/(1-640000*2**-52);rows.append(dict(view=v['key'],native_backward_vs_FP64_coefficient_max_abs=float(diff.max()),relative_L1=float(diff.sum()/max(qq.sum(),1e-20)),coefficient_error_quantiles=np.quantile(diff,[.5,.9,.99,1]).tolist(),full_image_alpha_replay_max_abs=alphaerr,FP64_positive_atomic_total_roundoff_bound=gamma*float(absq.sum())))
   b64=np.stack(b64);keys=original['view_keys'].tolist();source=b64[[keys.index(k) for k in P['source_views']]].sum(0);diag=b64[[keys.index(k) for k in P['evaluation_views']]].sum(0);sets=np.load(ART/'downloads'/scene/'oracle_original_ID_sets.npz');out=[]
   for name,vec,oldvec in (('source8',source,original['source8_b']),('diagnostic2_pooled',diag,original['diagnostic2_b'])):
    eps=float(np.abs(vec-oldvec).max())
    for B in P['budgets']:
     optimum=np.lexsort((np.arange(len(vec)),-vec))[:B];chosen=sets[f'{name}_oracle_{B}'];mass=float(vec[chosen].sum());upper=float(vec[optimum].sum());out.append(dict(domain=name,budget=B,FP64_optimal_line_mass=upper,original_frozen_oracle_FP64_line_mass=mass,original_vs_FP64_topB_different_IDs=int(B-len(np.intersect1d(optimum,chosen))),actual_suboptimal_line_mass=upper-mass,coefficient_Linf_error=eps,original_oracle_max_suboptimality_bound=2*B*eps,interpretation='frozen FP32 topB unchanged; true accepted-weight bound only within computed coefficient roundoff plus FP64 allowance'))
   p=ART/'downloads'/scene/'oracle_FP64_coefficients.npz';npz(p,original_ids=np.arange(record['count'],dtype=np.int32),view_keys=np.array(keys),per_view_fullT_line_b_FP64=b64,source8_b_FP64=source,diagnostic2_b_FP64=diag)
   return dict(rows=rows,oracle_roundoff_bounds=out,files=[rel(p)])
  sealed(scene+'_oracle_roundoff_audit',calculate);del model;torch.cuda.empty_cache()
if __name__=='__main__':main()
