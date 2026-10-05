"""F-only scorebanks, exact lazy coverage greed and sealed original-ID prefixes."""
import numpy as np
from scipy import sparse
import representative_core as core
from io_utils import *

def matrix(scene,k):
 d=OUT/scene/'matrix';path=d/'objective.npz'
 if path.exists():
  z=load(path);return sparse.csc_matrix((z['data'],z['indices'],z['indptr']),shape=tuple(z['shape'])),z['omega'],load(d/'statistics.npz'),load(d/'rows.npz')
 n=INPUTS['scenes'][scene]['checkpoint']['qualification']['gaussians'];matrices=[];omegas=[];viewrows=[];classrows=[];pixelrows=[];stats=[]
 for vi,f in enumerate(frames(scene,'F')):
  folder=OUT/scene/'contributions'/('K'+str(k))/f['key'];verify(folder);z=load(folder/'foreground_csr.npz');s=load(folder/'statistics.npz');stats.append(s)
  g=sparse.csr_matrix((z['weights'],z['original_ids'],z['indptr']),shape=(len(z['pixels']),n));g.sum_duplicates()
  e=load(OUT/scene/'F'/f['key']/'evidence.npz')
  for c in range(3):
   pixels=np.flatnonzero((e['omega'][:,:,c]>0).ravel());p=np.searchsorted(z['pixels'],pixels);ok=(p<len(z['pixels']));ok[ok]=z['pixels'][p[ok]]==pixels[ok];pixels=pixels[ok];p=p[ok]
   v=g[p].multiply((1/(CFG['demand_fullalpha_fraction']*z['alpha'][p]))[:,None]).tocsr();matrices.append(v);omegas.append(e['omega'][:,:,c].ravel()[pixels]);viewrows.append(np.repeat(vi,len(p)));classrows.append(np.repeat(c,len(p)));pixelrows.append(pixels)
  event('S3_MATRIX_VIEW',scene=scene,key=f['key'],foreground_pixels=len(z['pixels']))
 a=sparse.vstack(matrices,format='csc',dtype=np.float32);a.sum_duplicates();a.sort_indices();omega=np.concatenate(omegas).astype(np.float64)
 mass=np.stack([s['raw_mass'] for s in stats]);visible=(mass>0).sum(0);rawmass=mass.sum(0);eligible=(rawmass>=1)&(visible>=2)
 stat=dict(raw_mass=rawmass,per_view_raw_mass=mass,visible_views=visible.astype(np.int16),eligible=eligible,unknown=rawmass==0,unreliable_seen=(rawmass>0)&~eligible,foreground_mean_fraction=np.stack([s['foreground_mean_fraction'] for s in stats]).mean(0),nonedge_cost=np.stack([s['nonedge_mean_fraction'] for s in stats]).mean(0),per_view_nonedge_cost=np.stack([s['nonedge_mean_fraction'] for s in stats]),class_counter_mass=np.stack([s['class_counter_mass'] for s in stats]).sum(0),class_positive_mass=np.stack([s['class_positive_mass'] for s in stats]).sum(0))
 row=dict(view=np.concatenate(viewrows).astype(np.int8),class_id=np.concatenate(classrows).astype(np.int8),pixel=np.concatenate(pixelrows).astype(np.int32))
 npz(path,data=a.data,indices=a.indices,indptr=a.indptr,shape=np.array(a.shape),omega=omega);npz(d/'statistics.npz',**stat);npz(d/'rows.npz',**row)
 atomic(d/'MATRIX.json',dict(shape=list(a.shape),nnz=a.nnz,omega_sum=float(omega.sum()),K=k,fullalpha_demand_fraction=.5,raw_topK_weights=True));seal(d,dict(F_only=True))
 return a,omega,stat,row

def select_scene(scene,k):
 folder=OUT/scene/'assets'
 if (folder/'SEAL.json').exists():verify(folder);return
 a,omega,stats,rows=matrix(scene,k);n=a.shape[1];maxcount=max(CFG['budgets'][scene]);ids=np.arange(n,dtype=np.int32)
 old=load(SRC/'artifacts/gaussian_edge_attribution_v1/assets'/scene/'scores.npz');assert np.array_equal(old['original_ids'],ids)
 aorder=np.lexsort((ids,-old['baseline_union']));aorder=aorder[old['eligible'][aorder]][:maxcount].astype(np.int32)
 numerator=np.asarray(a.T@omega).ravel()*.5;den=stats['foreground_mean_fraction'];bscore=np.divide(numerator,den,out=np.zeros(n),where=den>0)
 border=np.lexsort((ids,-bscore));border=border[stats['eligible'][border]][:maxcount].astype(np.int32)
 selected={'A':aorder,'B':border};curves={'A':core.prefix_curve(a,omega,aorder),'B':core.prefix_curve(a,omega,border)};gains={}
 for arm,lam in zip(('C','D','E'),CFG['lambda_grid']):
  event('S3_GREEDY_START',scene=scene,arm=arm,lambda_value=lam,eligible=int(stats['eligible'].sum()),rows=a.shape[0],nnz=a.nnz)
  order,g,u=core.greedy(a,omega,stats['nonedge_cost'],stats['eligible'],maxcount,lam,progress=lambda count,util,attempts:event('S3_GREEDY_PROGRESS',scene=scene,arm=arm,count=count,utility=util,heap_evaluations=attempts))
  selected[arm]=order;gains[arm]=g;curves[arm]=u
  event('S3_GREEDY_COMPLETE',scene=scene,arm=arm,count=len(order),utility=float(u[-1]) if len(u) else 0,early_stop=len(order)<maxcount)
 budgets=CFG['budgets'][scene];middle=budgets[1];target=float(curves['A'][min(middle,len(aorder))-1]);matches={}
 for arm,u in curves.items():
  p=np.flatnonzero(u>=target-1e-12);matches[arm]=int(p[0])+1 if len(p) else None
 evalcounts={arm:sorted(set(min(b,len(v)) for b in budgets)) for arm,v in selected.items()}
 for arm,count in matches.items():
  if count is not None:evalcounts[arm]=sorted(set(evalcounts[arm]+[count]))
 for arm in ('C','D','E'):
  for b in budgets:
   actual=min(b,len(selected[arm]))
   if actual<b:
    for base in ('A','B'):evalcounts[base]=sorted(set(evalcounts[base]+[min(actual,len(selected[base]))]))
 selection=dict(schema='fixed-original-gaussian-selected-id-v1',scene=scene,checkpoint_sha256=INPUTS['scenes'][scene]['checkpoint']['sha256'],identity='zero-based original PLY row, fixed across views',available_K=k,F_only=True,budgets=budgets,coverage_match_F_target=target,coverage_match_counts=matches,evaluation_counts=evalcounts,arms={})
 arrays=dict(original_ids=ids,A_score=old['baseline_union'],B_score=bscore,B_major_numerator=numerator,**stats)
 for c,name in enumerate(core.CLASSES):arrays['B_numerator_'+name]=np.asarray(a[rows['class_id']==c].T@omega[rows['class_id']==c]).ravel()*.5
 for arm,order in selected.items():
  arrays[arm+'_ordered_ids']=order;arrays[arm+'_utility_curve']=curves[arm];arrays[arm+'_cumulative_nonedge_cost']=np.cumsum(stats['nonedge_cost'][order]);
  if arm in gains:arrays[arm+'_objective_gain']=gains[arm]
  selection['arms'][arm]=dict(ordered_original_ids=order.tolist(),actual_prefix_length=len(order),prefixes={str(b):dict(requested_count=b,actual_count=min(b,len(order)),selected_ids=order[:b].tolist()) for b in budgets},early_stop=arm in gains and len(order)<maxcount)
 npz(folder/'scorebank.npz',**arrays);atomic(folder/'selected_ids.json',selection)
 atomic(folder/'ASSET.json',dict(scene=scene,K=k,eligible=int(stats['eligible'].sum()),unknown=int(stats['unknown'].sum()),unreliable_seen=int(stats['unreliable_seen'].sum()),selection_counts={arm:{str(b):min(b,len(order)) for b in budgets} for arm,order in selected.items()},coverage_match=matches,mathematically_full_attribution='UNDETERMINED',residual_flags='TOPK residual ray mass remains; no per-ID omitted-mass assignment; unobserved != nonedge',code_hashes={name:sha(ART/'code'/name) for name in ['config.json','representative_core.py','legacy_core.py','selection.py']},normalization_sha256=sha(OUT/'NORMALIZATION.json')))
 seal(folder,dict(F_only=True,all_8_F=True,scene=scene));event('S3_SCENE_SEALED',scene=scene,counts={arm:len(order) for arm,order in selected.items()},coverage_match=matches)

def stage():
 verify_s0();k=json.loads((OUT/'COMPLETENESS.json').read_text())['available_K']
 for s in CFG['scenes']:select_scene(s,k)
 d=OUT/'F_SELECTION_SEAL';d.mkdir(exist_ok=True);atomic(d/'bindings.json',dict(scenes={s:sha(OUT/s/'assets/SEAL.json') for s in CFG['scenes']},normalization_sha256=sha(OUT/'NORMALIZATION.json'),S0_sha256=sha(ART/'S0_SEAL.json'),completeness_sha256=sha(OUT/'COMPLETENESS.json'),created_before_C_or_arc=True));seal(d,dict(all16F_selected=True));event('S3_ALL_F_SEALED',seal_sha256=sha(d/'SEAL.json'))
if __name__=='__main__':
 try:stage()
 except Exception as ex:event('ENGINEERING_STOP',requested_phase='selection',error=str(ex));raise
