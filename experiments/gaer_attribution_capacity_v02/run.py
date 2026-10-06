"""Plain bounded, resumable scientific runner; per-unit atomic results/seals."""
import argparse,gc,json,time,traceback
import numpy as np
import torch
from runtime import *
from binding import backend,scene_io
from operators import NativeWeights,raw_forward,rank,binary,query_extension
from solver import Pool,solve
from diagnostics import analyze_view,sample_image
from probes import run_probes
from media import save,sheet,profile_plot
from shape import run_shape

def metrics(ink,a):
 E=a['line_binary'];alpha=a['alpha'];mass=float(ink.sum(dtype=np.float64));line=float(ink[E].sum(dtype=np.float64));fraction=ink/np.maximum(alpha,1e-20)
 return dict(line_total_contribution=line,mass_recall=line/max(float(alpha[E].sum(dtype=np.float64)),1e-20),coverage_gt_01=float((fraction[E]>.1).mean()),coverage_gt_05=float((fraction[E]>.5).mean()),nonline_mass_leakage=float(ink[~E].sum(dtype=np.float64)/max(mass,1e-20)),total_contribution=mass,line_target_MSE=float(np.square(ink[E]-a['ink'][E]).mean()),whole_target_MSE=float(np.square(ink-a['ink']).mean()),outside_weak_MSE=float(np.square(ink[(a['ink']>0)&~E]).mean()) if ((a['ink']>0)&~E).any() else 0.,outside_zero_MSE=float(np.square(ink[a['ink']==0]).mean()) if (a['ink']==0).any() else 0.)

def load_cached_map(scene,key,label):
 p=OLD/f'out/gaer_rgb_union_voting_v01/display_maps/{scene}/eval/{key}/{label}_fullT.npz';seal=OLD/f'artifacts/gaer_rgb_union_voting_v01/seals/{scene}_eval_{key}.json';d=json.loads(seal.read_text());expected=d['files'][str(p.relative_to(OLD))]
 if sha(p)!=expected:raise RuntimeError('old baseline cache seal invalid')
 data=np.load(p);return data[data.files[0]],dict(path=str(p),sha256=sha(p),prior_seal_sha256=sha(seal))

def oracle_scene(scene,record,module,model):
 views=record['views'];bs=[];records=[];ops={};fields={};repeat_errors=[]
 for v in views:
  key=v['key'];guard(scene+'_oracle_'+key);a=dict(np.load(v['source']));s=scene_io.make_settings(module,v['camera']);op=NativeWeights(module,s,model);E=torch.tensor(a['line_binary'].astype(np.float32),device='cuda');b=op.AT(E);bs.append(b.cpu().numpy());fields[key]=a
  if key in ('r_000','r_001'):
   repeat=op.AT(E);diff=(repeat-b).abs();repeat_errors.append(dict(view=key,max_abs=float(diff.max()),relative_sum=float(diff.double().sum()/b.abs().double().sum()),quantiles=torch.quantile(diff,torch.tensor([.5,.9,.99,1.],device='cuda')).cpu().tolist()))
  if key in ('r_001','r_014'):ops[key]=op
 b=np.stack(bs);keys=[v['key'] for v in views];src=b[[keys.index(k) for k in P['source_views']]].sum(0,dtype=np.float64);diag=b[[keys.index(k) for k in P['evaluation_views']]].sum(0,dtype=np.float64);agg=np.load(OLD/f'artifacts/gaer_rgb_union_voting_v01/downloads/{scene}_votes_all_original.npz');sets={};files=[];cache_receipts=[];counter=ART/'downloads'/scene/'fullN_linear_oracles.npz';npz(counter,original_ids=np.arange(record['count'],dtype=np.int32),view_keys=np.array(keys),per_view_fullT_line_b=b,source8_b=src,diagnostic2_b=diag);files.append(rel(counter))
 for B in P['budgets']:
  sets[f'raw_{B}']=agg[f'top{B}_ids'];sets[f'center_{B}']=agg[f'center_top{B}_ids'];sets[f'source8_oracle_{B}']=rank(src,B);sets[f'diagnostic2_pooled_oracle_{B}']=rank(diag,B)
  for key in P['evaluation_views']:sets[f'diagnostic_perview_{key}_{B}']=rank(b[keys.index(key)],B)
 rows=[];panels=[]
 for key in P['evaluation_views']:
  op=ops[key];a=fields[key];row=[a['RGB'],1-a['ink']];row_metrics={}
  for label,ids in sets.items():
   if label.startswith('diagnostic_perview_') and key not in label:continue
   if label.startswith(('raw_','center_')):
    typ,B=label.split('_');ink,receipt=load_cached_map(scene,key,f'{"top" if typ=="raw" else "center_top"}{B}');cache_receipts.append(receipt)
   else:ink=op.A(binary(op.n,ids)).cpu().numpy()
   met=metrics(ink,a);met['count']=len(ids);met['computed_linear_b_sum']=float(b[keys.index(key),ids].sum(dtype=np.float64));met['forward_vs_adjoint_sum_relative_error']=abs(met['line_total_contribution']-met['computed_linear_b_sum'])/max(met['line_total_contribution'],1e-20);row_metrics[label]=met
   p=ART/'downloads'/scene/f'{key}_{label}_fullT_ink.npz';npz(p,original_ids=ids,ink=ink);files.append(rel(p));files.append(save(ART/'media'/scene/'oracles'/f'{key}_{label}_ink.png',1-ink))
   if label in ('raw_500','source8_oracle_500','diagnostic2_pooled_oracle_500','raw_2000','source8_oracle_2000','diagnostic2_pooled_oracle_2000'):row.append(1-ink)
  rows.append(dict(view=key,metrics=row_metrics));panels.append(row)
 for B in P['budgets']:
  records.append(dict(budget=B,source8_optimal_line_mass=float(src[sets[f'source8_oracle_{B}']].sum()),raw_source8_fraction_of_bound=float(src[sets[f'raw_{B}']].sum()/src[sets[f'source8_oracle_{B}']].sum()),center_source8_fraction_of_bound=float(src[sets[f'center_{B}']].sum()/src[sets[f'source8_oracle_{B}']].sum()),diagnostic_pooled_bound=float(diag[sets[f'diagnostic2_pooled_oracle_{B}']].sum()),diagnostic_perview_adapted_bound=float(sum(b[keys.index(k),sets[f'diagnostic_perview_{k}_{B}']].sum(dtype=np.float64) for k in P['evaluation_views'])),raw_diagnostic_fraction_of_pooled_bound=float(diag[sets[f'raw_{B}']].sum()/diag[sets[f'diagnostic2_pooled_oracle_{B}']].sum()),center_diagnostic_fraction_of_pooled_bound=float(diag[sets[f'center_{B}']].sum()/diag[sets[f'diagnostic2_pooled_oracle_{B}']].sum())))
 p=ART/'media'/scene/'two_holdout_native_oracles.jpg';files.append(sheet(p,panels,['original SH3','old target','raw500 ink','source oracle500','pooled diag500','raw2000 ink','source oracle2000','pooled diag2000'],scene+' native full-T ink, fixed gain 1; rows r_001/r_014',800))
 setsfile=ART/'downloads'/scene/'oracle_original_ID_sets.npz';npz(setsfile,**sets);files.append(rel(setsfile))
 return dict(all_original_N=record['count'],eight_source_views=P['source_views'],evaluation_views=P['evaluation_views'],repeat_atomic_errors=repeat_errors,budgets=records,per_view=rows,cached_baseline_receipts=cache_receipts,scope='linear line-mass bound for computed FP32 original full-T b only, no leakage constraint; diagnostic targets known; shape/deletion excluded',files=files)

def capacity_scene(scene,record,module,model):
 vs={v['key']:v for v in record['views']};fields=[dict(np.load(vs[k]['source'])) for k in P['diagnostic_views']];ops=[NativeWeights(module,scene_io.make_settings(module,vs[k]['camera']),model) for k in P['diagnostic_views']];agg=np.load(OLD/f'artifacts/gaer_rgb_union_voting_v01/downloads/{scene}_votes_all_original.npz');base=binary(record['count'],agg['top2000_ids']);files=[];fits=[];per_strengths=[];per_images=[];baseline_metrics=[];baseline_maps=[]
 # Real-scene operator checks only for this new style path, no old campaign.
 gen=torch.Generator(device='cuda');gen.manual_seed(17);x=torch.rand(record['count'],device='cuda',generator=gen);checks=[]
 for key,op in zip(P['diagnostic_views'],ops):
  ax=op.A(x);native=op.ink_rgb(x);formula=float((native-(1-ax)[None]).abs().max());y=torch.rand((800,800),device='cuda',generator=gen);lhs=float((ax.double()*y.double()).sum());rhs=float((x.double()*op.AT(y).double()).sum());adj=abs(lhs-rhs)/max(abs(lhs),abs(rhs),1e-20);checks.append(dict(view=key,formula_max_abs=formula,adjoint_relative_error=adj));
  if formula>3e-6 or adj>3e-5:raise RuntimeError('new style operator invalid')
 for key,op,a in zip(P['diagnostic_views'],ops,fields):
  guard(scene+'_fit_perview_'+key);pool=Pool([op],[a]);zero,r0,imgs=solve(pool,torch.zeros(record['count'],device='cuda'),P['solver'],'zero');second,r1,_=solve(pool,base,P['solver'],'baseline');best=zero if r0['certificate']['primal_feasible_objective']<=r1['certificate']['primal_feasible_objective'] else second;ink=op.A(best).cpu().numpy();per_strengths.append(best.cpu().numpy());per_images.append(ink);fits.append(dict(scope='perview_known_target',view=key,starts=[r0,r1],selected_certificate=(r0 if best is zero else r1)['certificate'],metrics=metrics(ink,a)));p=ART/'downloads'/scene/f'{key}_perview_strengths.npz';npz(p,original_ids=np.arange(record['count'],dtype=np.int32),strength=best.cpu().numpy(),ink=ink,view_keys=np.array([key]),source_sha256=np.array(vs[key]['source_sha256']));files.append(rel(p));files.append(save(ART/'media'/scene/'capacity'/f'{key}_perview_ink.png',1-ink))
  baselines={}
  for B in P['budgets']:
   for label in ('raw','center'):
    ids=agg[f'{"top" if label=="raw" else "center_top"}{B}_ids'];out=op.A(binary(record['count'],ids)).cpu().numpy();baselines[f'{label}_{B}']=metrics(out,a)
    if label=='raw' and B==2000:baseline_maps.append(out)
  baseline_metrics.append(dict(view=key,metrics=baselines))
 pool=Pool(ops,fields);guard(scene+'_fit_shared');zero,r0,_=solve(pool,torch.zeros(record['count'],device='cuda'),P['solver'],'zero');second,r1,_=solve(pool,base,P['solver'],'baseline');best=zero if r0['certificate']['primal_feasible_objective']<=r1['certificate']['primal_feasible_objective'] else second;shared=[op.A(best).cpu().numpy() for op in ops];fits.append(dict(scope='shared_known_targets',views=P['diagnostic_views'],starts=[r0,r1],selected_certificate=(r0 if best is zero else r1)['certificate'],per_view_metrics=[metrics(img,a) for img,a in zip(shared,fields)]));p=ART/'downloads'/scene/'shared_strengths.npz';npz(p,original_ids=np.arange(record['count'],dtype=np.int32),strength=best.cpu().numpy(),view_keys=np.array(P['diagnostic_views']),source_sha256=np.array([vs[k]['source_sha256'] for k in P['diagnostic_views']]));files.append(rel(p));rows=[]
 for j,(key,a,ip,is_) in enumerate(zip(P['diagnostic_views'],fields,per_images,shared)):
  # This is actual white-background black appearance, all original Gaussians kept.
  actual=ops[j].ink_rgb(best).cpu().numpy().transpose(1,2,0);formula=float(np.abs(actual-(1-is_)[...,None]).max());p=ART/'downloads'/scene/f'{key}_shared_native_RGB.npz';npz(p,RGB=actual,ink=is_,native_formula_max_abs=np.array(formula));files.append(rel(p));files.append(save(ART/'media'/scene/'capacity'/f'{key}_shared_native.png',actual));rows.append([a['RGB'],1-a['ink'],1-baseline_maps[j],1-ip,actual,np.repeat(np.abs(is_-a['ink'])[...,None],3,2)])
 p=ART/'media'/scene/'fourview_known_target_capacity.jpg';files.append(sheet(p,rows,['original SH3','old continuous target','raw2000 native ink','all-N perview fit','all-N shared fit','absolute error gain1'],scene+' known targets, original footprints, full 800x800; no deletion',800))
 roirows=[]
 for key in P['roi_views']:
  j=P['diagnostic_views'].index(key);a=fields[j]
  for r in record['rois'][key]:
   x0,y0,x1,y1=r['box_xyxy'];crop=lambda img:img[y0:y1,x0:x1];roirows.append([crop(1-a['ink']),crop(1-per_images[j]),crop(1-shared[j])]);center=np.array([r['center_yx']]);from diagnostics import normal_points;nn,_=normal_points(a,center);points=center+np.arange(-12,13)[:,None]*nn;files.append(profile_plot(ART/'media'/scene/'profiles'/f'{key}_{r["category"]}_{r["fragment"]}.png',{'target':sample_image(a['ink'],points),'perview':sample_image(per_images[j],points),'shared':sample_image(shared[j],points)},scene+' '+key+' '+r['category']))
 p=ART/'media'/scene/'frozen_ROI_capacity_nearest.jpg';files.append(sheet(p,roirows,['target','perview','shared'],scene+' 24px frozen fragments, nearest resize, fixed gain 1',192))
 return dict(views=P['diagnostic_views'],all_original_N=record['count'],operator_checks=checks,fits=fits,baselines=baseline_metrics,scope='known-target capacity, perview/shared exact same four-frame pool; all-N continuous vs fixed-count baselines not equal-budget superiority; visual GO human pending',files=files)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--scene',choices=['lego','chair','both'],default='both');parser.add_argument('--units',default='math,oracle,roi,probes,capacity,shape');args=parser.parse_args();torch.set_num_threads(2);guard('runner_start');global P;P=json.loads((ART/'PROTOCOL.json').read_text());module=backend();units=args.units.split(',');summary={};query=None
 if 'math' in units:
  import test_new_math;test_new_math.main()
 for scene in (['lego','chair'] if args.scene=='both' else [args.scene]):
  record=P['scenes'][scene];model=scene_io.load_model(record);summary[scene]={}
  try:
   if 'oracle' in units:summary[scene]['oracle']=sealed(scene+'_oracle',lambda:oracle_scene(scene,record,module,model))
   if 'roi' in units:
    if query is None:query=query_extension()
    for key in P['roi_views']:
     v=next(v for v in record['views'] if v['key']==key);a=dict(np.load(v['source']));s=scene_io.make_settings(module,v['camera']);summary[scene]['roi_'+key]=sealed(scene+'_roi_'+key,lambda key=key,a=a,s=s:analyze_view(scene,key,module,s,model,a,record['rois'][key],query,P['D'])[0])
   if 'probes' in units:
    key='r_000';v=next(v for v in record['views'] if v['key']==key);a=dict(np.load(v['source']));s=scene_io.make_settings(module,v['camera']);r=json.loads((ART/'results'/f'{scene}_roi_{key}.json').read_text());d=np.load(ART/'downloads'/scene/f'{key}_ROI_full_CSR.npz');geom=tuple(d[k] for k in ('projected_means_xy','projected_conic_opacity','effective_SH3_colors','original_cov3D'));mass=NativeWeights(module,s,model).AT(torch.ones((800,800),device='cuda')).cpu().numpy();summary[scene]['probes']=sealed(scene+'_probes',lambda:run_probes(scene,module,s,model,a,r['groups'],geom,mass,P['probes']))
   if 'capacity' in units:summary[scene]['capacity']=sealed(scene+'_capacity',lambda:capacity_scene(scene,record,module,model))
   if 'shape' in units:
    key='r_000';v=next(v for v in record['views'] if v['key']==key);a=dict(np.load(v['source']));s=scene_io.make_settings(module,v['camera']);r=json.loads((ART/'results'/f'{scene}_roi_{key}.json').read_text());c=json.loads((ART/'results'/f'{scene}_capacity.json').read_text());cert=next(f for f in c['fits'] if f.get('view')==key)['selected_certificate'];strength=torch.tensor(np.load(ART/'downloads'/scene/f'{key}_perview_strengths.npz')['strength'],device='cuda');summary[scene]['shape']=sealed(scene+'_shape',lambda:run_shape(scene,s,model,a,record['rois'][key],r['groups'],ART/'downloads'/scene/f'{key}_ROI_full_CSR.npz',strength,cert,P['shape']))
  except Exception as e:
   atomic_json(ART/'results'/f'{scene}_FAILURE.json',dict(status='ENGINEERING_NOT_READY',error=str(e),traceback=traceback.format_exc()));print(traceback.format_exc(),flush=True);summary[scene]['failure']=str(e)
  del model;gc.collect();torch.cuda.empty_cache()
 atomic_json(ART/'RUN_STATUS.json',dict(status='COMPLETE_UNITS' if all('failure' not in s for s in summary.values()) else 'PARTIAL_ENGINEERING',requested_units=units,scenes={s:list(v) for s,v in summary.items()},protocol_sha256=sha(ART/'PROTOCOL.json')))
if __name__=='__main__':main()
