"""Small paired original-parameter perturbations; never writes input checkpoints."""
import math
import numpy as np
import torch
from scipy.spatial import cKDTree
from runtime import *
from operators import raw_forward
from diagnostics import sample_image,normal_points

def matched(ids,mass,conic,seed):
 det=conic[:,0]*conic[:,2]-conic[:,1]**2;area=1/np.maximum(np.sqrt(np.maximum(det,1e-20)),1e-20);valid=np.flatnonzero((mass>0)&(det>0)&np.isfinite(area));cost=np.column_stack([np.log(np.maximum(mass,1e-20)),np.log(area)]);mu=cost[valid].mean(0);sd=cost[valid].std(0);sd=np.maximum(sd,1e-6);feat=(cost-mu)/sd;tree=cKDTree(feat[valid]);chosen=[]
 for i in ids:
  _,nn=tree.query(feat[i],k=min(64,len(valid)));candidates=valid[np.atleast_1d(nn)];candidate=next((int(j) for j in candidates if j not in chosen and j!=i),None)
  if candidate is None:raise RuntimeError('matched cost pool empty')
  chosen.append(candidate)
 chosen=np.array(chosen,np.int32);error=np.abs(cost[chosen]-cost[ids]);return chosen,dict(log_mass_mean_abs=float(error[:,0].mean()),log_area_mean_abs=float(error[:,1].mean()),relative_total_mass_error=float(abs(mass[chosen].sum()-mass[ids].sum())/max(mass[ids].sum(),1e-20)),overlap=int(np.intersect1d(ids,chosen).size))

def profile_metrics(p):
 luminance=np.mean(p,axis=1);d=np.abs(np.diff(luminance));total=d.sum();center=float((d*np.arange(-11.5,12)).sum()/max(total,1e-20));width=float(np.sqrt((d*(np.arange(-11.5,12)-center)**2).sum()/max(total,1e-20)));contrast=float(luminance[-4:].mean()-luminance[:4].mean());ringing=float(max(total-abs(luminance[-1]-luminance[0]),0));return dict(center=center,width=width,contrast=contrast,ringing=ringing)

def run_probes(scene,module,s,model,a,groups,geometry,mass,config):
 xy,conic,colors,cov=geometry;base=a['RGB'];basealpha=a['alpha'];rows=[];arrays={};n=len(model['means3D']);offsets=np.arange(-12,13)
 for g in groups:
  if g['fragment']>=config['fragments_per_category']:continue
  points=np.asarray(g['profiles_yx']);y,x=g['center_yx'];box=np.zeros((800,800),bool);box[y-12:y+12,x-12:x+12]=True;other=np.zeros_like(box)
  for h in groups:
   if h['roi']==g['roi']:continue
   yy,xx=h['center_yx'];other[yy-12:yy+12,xx-12:xx+12]=True
  selected={k:np.asarray(v,np.int32) for k,v in g['selected'].items()};random,match=matched(selected['multiD'],mass,conic,config['random_seed']+g['roi']);selected['matched_random']=random
  baselineprofile=sample_image(base,points);baseline_metrics=profile_metrics(baselineprofile)
  for method,ids in selected.items():
   guard(f'{scene}_probe_roi{g["roi"]}_{method}')
   if len(ids)!=config['edited_count']:raise RuntimeError('unequal edit count')
   idx=torch.tensor(ids.astype(np.int64),device='cuda');edited_mass=float(mass[ids].sum());det=conic[ids,0]*conic[ids,2]-conic[ids,1]**2;projected_area=float((1/np.sqrt(np.maximum(det,1e-20))).sum());arraykey=f'roi{g["roi"]}_{method}';arrays[arraykey+'_ids']=ids;arrays[arraykey+'_baseline_profile']=baselineprofile
   for parameter,amps in (('DC',config['DC_amplitudes']),('logscale',config['logscale_amplitudes'])):
    derivatives=[]
    for amplitude in amps:
     outs=[];alphas=[]
     for sign in (1,-1):
      edited={**model}
      if parameter=='DC':
       edited['shs']=model['shs'].clone();edited['shs'][idx,0,:]+=sign*amplitude
      else:
       edited['scales']=model['scales'].clone();edited['scales'][idx]*=math.exp(sign*amplitude)
      with torch.no_grad():rgb=raw_forward(module,s,edited)[1].cpu().numpy().transpose(1,2,0)
      if parameter=='logscale':
       with torch.no_grad():alpha=raw_forward(module,s,edited,torch.ones((n,3),device='cuda'),torch.zeros(3,device='cuda'))[1][0].cpu().numpy()
      else:alpha=basealpha
      outs.append(rgb);alphas.append(alpha)
     plus,minus=outs;derivative=(plus-minus)/(2*amplitude);derivatives.append(derivative);nonlinear=(plus+minus-2*base)/(amplitude**2);dp=sample_image(derivative,points);pp=sample_image(plus,points);mp=sample_image(minus,points);pm=profile_metrics(pp);mm=profile_metrics(mp)
     target_energy=float(np.square(derivative[box]).sum(dtype=np.float64));outside_energy=float(np.square(derivative[~box]).sum(dtype=np.float64));den=target_energy+outside_energy
     alpha_damage=float(max(np.square(alphas[0]-basealpha).mean(),np.square(alphas[1]-basealpha).mean()));coverage_damage=int(max(((alphas[0]>.5)!=(basealpha>.5)).sum(),((alphas[1]>.5)!=(basealpha>.5)).sum()))
     row=dict(roi=g['roi'],category=g['category'],fragment=g['fragment'],method=method,parameter=parameter,amplitude=amplitude,edited_count=len(ids),visible_mass=edited_mass,projected_area=projected_area,target_response_energy=target_energy,outside_response_energy=outside_energy,target_response_fraction=target_energy/max(den,1e-20),outside_MSE=float(max(np.square(plus[~box]-base[~box]).mean(),np.square(minus[~box]-base[~box]).mean())),other_ROI_MSE=float(max(np.square(plus[other]-base[other]).mean(),np.square(minus[other]-base[other]).mean())) if other.any() else 0.,alpha_MSE=alpha_damage,alpha_threshold_coverage_changed=coverage_damage,nonlinearity_norm=float(np.linalg.norm(nonlinear)),paired_profile_derivative_norm=float(np.linalg.norm(dp)),baseline_profile=baseline_metrics,plus_profile=pm,minus_profile=mm,matched_random_residual=match if method=='matched_random' else None)
     rows.append(row);k=f'{arraykey}_{parameter}_{amplitude}';arrays[k+'_plus_profile']=pp;arrays[k+'_minus_profile']=mp;arrays[k+'_derivative_profile']=dp
    relative=float(np.linalg.norm(derivatives[0]-derivatives[1])/max(np.linalg.norm(derivatives[1]),1e-20));rows[-1]['half_amplitude_derivative_relative_change']=relative;rows[-2]['half_amplitude_derivative_relative_change']=relative
 print('PROBES',scene,len(rows),flush=True);p=ART/'downloads'/scene/'original_parameter_probes.npz';npz(p,profile_offsets=offsets,**arrays)
 return dict(rows=rows,files=[rel(p)],same_parameter_permissions=True,interpretation='local response and collateral change, not improvement of an already correct edge; method visible mass/area differences recorded')
