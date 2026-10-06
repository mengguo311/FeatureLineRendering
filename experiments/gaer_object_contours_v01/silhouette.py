"""Alpha-only exterior evidence and raw-native quality measurements. Never ink drawing."""
import numpy as np
from scipy.ndimage import label,binary_fill_holes,binary_erosion,distance_transform_edt,map_coordinates

def evidence(alpha,c):
 raw=alpha>c['alpha_threshold'];lab,num=label(raw,np.ones((3,3)));areas=np.bincount(lab.ravel());mass=np.bincount(lab.ravel(),weights=alpha.ravel());keep=np.where((areas>=c['minimum_component_pixels'])&(mass>=c['minimum_component_alpha_mass']))[0];keep=keep[keep!=0];fg=np.isin(lab,keep);filled=binary_fill_holes(fg);holes=filled&~fg
 sdf=distance_transform_edt(filled)-distance_transform_edt(~filled);sdf-=.5*np.sign(sdf)
 gy,gx=np.gradient(sdf);norm=np.hypot(gy,gx);normal=np.stack([gy/np.maximum(norm,1e-12),gx/np.maximum(norm,1e-12)],-1).astype(np.float32);tangent=np.stack([-normal[...,1],normal[...,0]],-1)
 beta=np.clip(c['width_pixels']/2+.5-np.abs(sdf-c['inward_offset_pixels']),0,1).astype(np.float32);target=np.minimum(alpha,c['max_blackness']*beta).astype(np.float32);q=np.where(beta>0,c['weight_in_band'],c['weight_outside_band']).astype(np.float32);boundary=filled&~binary_erosion(filled,structure=np.ones((3,3)))
 hl,hn=label(holes,np.ones((3,3)))
 return dict(alpha=alpha.astype(np.float32),raw_mask=raw,component_mask=fg,object_mask=filled,holes=holes,dropped_components=raw&~fg,sdf=sdf.astype(np.float32),normal_yx=normal,tangent_yx=tangent,beta=beta,target=target,q=q,boundary=boundary,components_total=int(num),components_kept=len(keep),component_sizes=areas[keep].tolist(),holes_count=int(hn),hole_sizes=np.bincount(hl.ravel())[1:].tolist())

def weighted_quantile(values,weights,qs):
 idx=np.argsort(values);v=values[idx];w=weights[idx];cw=np.cumsum(w,dtype=np.float64)
 if not len(cw) or cw[-1]<=0:return [None]*len(qs)
 return np.interp(np.asarray(qs)*cw[-1],cw,v).tolist()

def metrics(ink,e,thresholds):
 import cv2
 coords=np.argwhere(e['boundary']);normal=e['normal_yx'][e['boundary']];offs=np.arange(-8,8.01,.5,dtype=np.float32);p=coords[:,None,:]+normal[:,None,:]*offs[None,:,None];profiles=map_coordinates(ink,[p[...,0],p[...,1]],order=1,mode='constant',cval=0);peaks=profiles.max(1);region=(offs>=-1)&(offs<=3);covered=profiles[:,region].max(1)>=thresholds['ink_threshold'];covermask=np.zeros_like(ink,dtype=bool);covermask[e['boundary']]=covered
 contours,_=cv2.findContours(e['object_mask'].astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE);gaps=[]
 for contour in contours:
  xy=contour[:,0,:];v=~covermask[xy[:,1],xy[:,0]];n=len(v)
  if n==0:continue
  if v.all():gaps.append(n);continue
  pivot=int(np.where(~v)[0][0]);v=np.roll(v,-pivot);run=0
  for missing in v:
   if missing:run+=1
   elif run:gaps.append(run);run=0
  if run:gaps.append(run)
 widths=[];locations=[]
 for pr,peak in zip(profiles,peaks):
  if peak<thresholds['ink_threshold']:continue
  j=int(pr.argmax());lo=j;hi=j
  while lo>0 and pr[lo-1]>=.5*peak:lo-=1
  while hi+1<len(pr) and pr[hi+1]>=.5*peak:hi+=1
  left=offs[lo]-.25;right=offs[hi]+.25
  if lo>0:left=offs[lo-1]+.5*(.5*peak-pr[lo-1])/max(pr[lo]-pr[lo-1],1e-12)
  if hi+1<len(pr):right=offs[hi]+.5*(pr[hi]-.5*peak)/max(pr[hi]-pr[hi+1],1e-12)
  widths.append(float(right-left));locations.append(float((pr*offs).sum()/max(pr.sum(),1e-12)))
 ink_mass=float(ink.sum(dtype=np.float64));interior=e['sdf']>4;qs=[.05,.25,.5,.75,.95];dist=weighted_quantile(np.abs(e['sdf']).ravel(),np.maximum(ink,0).ravel(),qs);fwhm=np.quantile(widths,qs).tolist() if widths else [None]*5;peakq=np.quantile(peaks,qs).tolist() if len(peaks) else [0]*5
 out=dict(boundary_pixels=len(coords),boundary_coverage=float(covered.mean()) if len(covered) else 0,longest_gap_pixels=max(gaps,default=0),gap_runs=len(gaps),gap_lengths=sorted(gaps,reverse=True),ink_mass=ink_mass,interior_ink_mass_fraction=float(ink[interior].sum(dtype=np.float64))/max(ink_mass,1e-12),interior_threshold_pixels=int((ink[interior]>=thresholds['ink_threshold']).sum()),contour_distance_quantiles_pixels=dist,profile_FWHM_quantiles_pixels=fwhm,profile_peak_quantiles=peakq,profile_location_quantiles_pixels=np.quantile(locations,qs).tolist() if locations else [None]*5,global_target_MSE=float(np.square(ink-e['target']).mean()),target_band_MSE=float(np.square(ink[e['beta']>0]-e['target'][e['beta']>0]).mean()),outside_band_MSE=float(np.square(ink[e['beta']==0]).mean()),strength_independent='metrics are from complete raw native ink; no thresholded/dilated final drawing')
 checks=dict(coverage=out['boundary_coverage']>=thresholds['clean_boundary_coverage_min'],gap=out['longest_gap_pixels']<=thresholds['clean_longest_gap_pixels_max'],distance=dist[-1] is not None and dist[-1]<=thresholds['clean_contour_distance_p95_pixels_max'],width=fwhm[-1] is not None and fwhm[-1]<=thresholds['clean_profile_FWHM_p95_pixels_max'],interior_mass=out['interior_ink_mass_fraction']<=thresholds['clean_interior_ink_mass_fraction_max'],interior_pixels=out['interior_threshold_pixels']<=thresholds['clean_interior_threshold_pixels_max'],blackness=peakq[2]>=thresholds['clean_peak_median_min']);out['clean_checks']=checks;out['clean_all']=all(checks.values());out['recognizable']=out['boundary_coverage']>=thresholds['recognizable_contour_boundary_coverage_min']
 return out,dict(profile_pixels_yx=coords.astype(np.int32),profile_offsets=offs,profile_ink=profiles.astype(np.float32),covered=covered)

def violation(m,t):
 pairs=[(1-m['boundary_coverage'],1-t['clean_boundary_coverage_min']),(m['longest_gap_pixels'],t['clean_longest_gap_pixels_max']),(m['contour_distance_quantiles_pixels'][-1] or 999,t['clean_contour_distance_p95_pixels_max']),(m['profile_FWHM_quantiles_pixels'][-1] or 999,t['clean_profile_FWHM_p95_pixels_max']),(m['interior_ink_mass_fraction'],t['clean_interior_ink_mass_fraction_max']),(m['interior_threshold_pixels'],t['clean_interior_threshold_pixels_max']),(max(0,t['clean_peak_median_min']-m['profile_peak_quantiles'][2]),t['clean_peak_median_min'])]
 return sum(max(0,a/max(b,1e-12)-1) for a,b in pairs)
