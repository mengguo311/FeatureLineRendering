"""Historical TOP4 A baseline_union, same algorithm newly computed; F only."""
import json
import numpy as np
import legacy_core as old
from io_utils import *
from scene_binding import budget_counts

def manual(raw,e,stat,n):
 ids=raw['topk_id'];w=raw['topk_w'].astype(np.float64)
 seen=np.flatnonzero(stat['denominator']>0);unseen=np.flatnonzero(stat['denominator']==0)
 sample=np.unique(np.r_[seen[np.linspace(0,len(seen)-1,min(12,len(seen))).astype(int)],unseen[:4]])
 den=[];num=[]
 for i in sample:
  m=ids==i;den.append(float(w[m].sum()));num.append([float((w*np.asarray(e[c],np.float64)[...,None])[m].sum()) for c in old.CLASSES])
 den=np.array(den);num=np.array(num);de=float(np.max(np.abs(den-stat['denominator'][sample]),initial=0));ne=float(np.max(np.abs(num-stat['numerator'][sample]),initial=0));assert de<1e-7 and ne<1e-7
 return dict(sampled_original_ids=sample.tolist(),denominator_max_abs=de,numerator_max_abs=ne,method='Independent boolean-mask float64 sums from original full-grid TOP4 and frozen evidence, not bincount',pass_status=True)

def scene_stage(scene):
 dest=OUT/scene/'baseline_A/assets'
 if (dest/'SEAL.json').exists():verify(dest);return json.loads((dest/'ASSET.json').read_text())['budgets']
 legacy_cfg=json.loads(Path(INPUTS['A_config_source']['path']).read_text());norm=json.loads(Path(INPUTS['A_normalization_source']['path']).read_text())['normalization'];n=INPUTS['scenes'][scene]['checkpoint']['qualification']['gaussians'];stats=[];audits=[]
 for f in frames(scene,'F'):
  d=OUT/scene/'baseline_A/F'/f['key']
  if (d/'SEAL.json').exists():
   verify(d);z=load(d/'statistics.npz');meta=json.loads((d/'STATISTICS.json').read_text());stat=dict(z,**meta);audits.append(json.loads((d/'CPU_AUDIT.json').read_text()))
  else:
   raw=read(scene,f,'S3_A_HISTORICAL_F');fields=old.evidence_fields(raw,legacy_cfg);e=old.compute_evidence(fields,norm,legacy_cfg);stat=old.view_statistics(raw,e,n,legacy_cfg,with_side=False);stat.update(split='F',frame_id=int(f['key'][2:]));aud=manual(raw,e,stat,n);audits.append(aud)
   npz(d/'evidence.npz',**{k:v for k,v in e.items() if isinstance(v,np.ndarray)});npz(d/'statistics.npz',**{k:v for k,v in stat.items() if isinstance(v,np.ndarray)});atomic(d/'STATISTICS.json',{k:v for k,v in stat.items() if not isinstance(v,(np.ndarray,dict))});atomic(d/'CPU_AUDIT.json',aud);seal(d,dict(scene=scene,F_only=True,raw_sha256=f['raw_sha256'],same_algorithm_newly_computed=True,with_side=False,side_excluded_reason='A baseline_union never uses side_numerator; no historical two-sided arm claimed'))
  stats.append(stat)
 asset=old.aggregate_views(stats,legacy_cfg);tiers=old.rank_tiers(asset,legacy_cfg,score_key='baseline_union');counts=[len(tiers[str(p)]) for p in (1,3,10)];assert counts==budget_counts(int(asset['eligible'].sum()))
 npz(dest/'scores.npz',**{k:v for k,v in asset.items() if isinstance(v,np.ndarray)});npz(dest/'selection.npz',**{'baseline_union_'+str(p).zfill(2):tiers[str(p)] for p in (1,3,10)})
 atomic(dest/'ASSET.json',dict(scene=scene,source='same algorithm newly computed',estimator='TOP4-TRUNCATED',eligible=int(asset['eligible'].sum()),unknown=int(asset['unknown'].sum()),unreliable=int(asset['unreliable'].sum()),budgets=counts,normalization_source=INPUTS['A_normalization_source'],config_source=INPUTS['A_config_source'],core_sha256=sha(ART/'code/legacy_core.py'),original_ids='original PLY row, unchanged',F_only=True,manual_CPU_audits=audits))
 seal(dest,dict(F_only=True,same_algorithm_newly_computed=True));event('A_BASELINE_SEALED',scene=scene,counts=counts,eligible=int(asset['eligible'].sum()));return counts

def stage():
 verify_s0();counts={s:scene_stage(s) for s in CFG['scenes']};d=OUT/'BUDGET_SEAL'
 if (d/'SEAL.json').exists():verify(d);assert json.loads((d/'binding.json').read_text())['counts']==counts
 else:
  atomic(d/'binding.json',dict(rule=CFG['budget_rule'],counts=counts,A_seals={s:sha(OUT/s/'baseline_A/assets/SEAL.json') for s in CFG['scenes']},before_selection_and_C_arc=True));seal(d,dict(F_only=True,rule_predeclared_S0=True));event('BUDGET_COUNTS_SEALED',counts=counts)
 CFG['budgets']=counts
if __name__=='__main__':stage()
