"""Read-only construction-source diagnostics after both fusion arms are sealed.

This script never selects or modifies an asset, reads no DEV/reserved image,
and does not call a renderer. New raw here means full accepted-alpha*T soft-rim
participation from the independently calibrated CPU replica, not historical D.
"""
import json,math
from pathlib import Path
import numpy as np
from plyfile import PlyData
import runtime as rt

DISPLAY_MAX=12000

def display_ids(ids,limit=DISPLAY_MAX):
 """Deterministic, original-ID order strata; every shown ID is recorded."""
 ids=np.sort(np.asarray(ids,dtype=np.int64))
 return ids[np.linspace(0,len(ids)-1,min(limit,len(ids)),dtype=np.int64)] if len(ids) else ids

def top_budget(values,budget,eligible=None):
 values=np.asarray(values)
 ids=np.arange(len(values)) if eligible is None else np.flatnonzero(eligible)
 # Stable descending score order; equal values retain increasing original ID.
 return ids[np.argsort(-values[ids],kind='stable')[:budget]]

def quantiles(values):
 v=np.asarray(values)
 return {str(q):float(np.percentile(v,q)) for q in [0,5,50,95,100]} if v.size else {}

def hist(values):
 v,c=np.unique(values,return_counts=True);return {str(int(a)):int(b) for a,b in zip(v,c)}

def camera_summary(scene):
 keys=scene['roles']['construction'];directions=np.array([scene['cameras'][k]['direction'] for k in keys])
 all_keys=list(scene['cameras']);all_directions=np.array([scene['cameras'][k]['direction'] for k in all_keys])
 angles=np.degrees(np.arccos(np.clip(all_directions@directions.T,-1,1)))
 elevation=np.degrees(np.arcsin(np.clip(directions[:,2],-1,1)))
 az=np.degrees(np.arctan2(directions[:,1],directions[:,0]));az_sorted=np.sort((az+360)%360)
 gaps=np.diff(np.r_[az_sorted,az_sorted[0]+360])
 return dict(construction_keys=keys,construction_count=len(keys),all_metadata_camera_count=len(all_keys),construction_directions=directions.tolist(),elevation_deg=quantiles(elevation),azimuth_largest_unsampled_gap_deg=float(gaps.max()),nearest_construction_angle_for_all_metadata_deg=quantiles(angles.min(1)),below_equator_construction_count=int((directions[:,2]<0).sum()),below_equator_metadata_count=int((all_directions[:,2]<0).sum()),all_metadata_direction_z_range=[float(all_directions[:,2].min()),float(all_directions[:,2].max())],domain_statement='Camera-origin directions are metadata coverage, not a surface visibility certificate. No source image outside construction is read.')

def analyze_scene(name,scene):
 # Both arms and every extraction must already exist as hash-valid atomic units.
 for arm in ['two_source','multi24']:
  if not rt.resume(name+'_fusion_'+arm):raise RuntimeError('wait for fusion seal: '+name+' '+arm)
 two_path=rt.ART/'fusion'/name/'two_source.npz';multi_path=rt.ART/'fusion'/name/'multi24.npz'
 two=np.load(two_path);multi=np.load(multi_path);two_ids=two['selected_ids'];multi_ids=multi['selected_ids']
 views=multi['views'].tolist()
 if views!=scene['roles']['construction']:raise RuntimeError('fusion/source role mismatch')
 if two['views'].tolist()!=views[:2]:raise RuntimeError('two-source view mismatch')
 n=scene['count'];budget=int(math.ceil(.005*n));records=[];rim_total=np.zeros(n,np.float64);positive_views=np.zeros(n,np.uint8);weak_counts=np.zeros(n,np.uint8);perview_ids={};source_hashes={}
 for key in views:
  if not rt.resume(name+'_extract_'+key):raise RuntimeError('unsealed construction source '+key)
  path=rt.ART/'sources'/name/(key+'.npz');a=np.load(path)
  if str(a['role'])!='construction' or str(a['camera_sha256'])!=scene['cameras'][key]['camera_sha256']:raise RuntimeError('source role/camera mismatch')
  np.testing.assert_array_equal(a['original_ids'],np.arange(n))
  mass=a['visible_mass'].astype(np.float64);raw=a['rim_wide'].astype(np.float64);relative=np.divide(raw,mass,out=np.zeros_like(raw),where=mass>.1)
  raw_ids=top_budget(raw,budget);ratio_ids=top_budget(relative,budget)
  positive_views+=(raw>0).astype(np.uint8);weak=((mass>=.1)&(raw>=.01)&(np.divide(raw,mass,out=np.zeros_like(raw),where=mass>0)>=.12));weak_counts+=weak.astype(np.uint8);rim_total+=raw
  denom=max(float(raw.sum()),1e-12);capture=lambda ids:float(raw[ids].sum()/denom)
  records.append(dict(camera=key,camera_sha256=str(a['camera_sha256']),role='construction',all_original_N=n,diagnostic_budget=budget,visible_mass_sum=float(mass.sum()),soft_rim_mass_sum=float(raw.sum()),positive_rim_IDs=int((raw>0).sum()),weak_response_IDs=int(weak.sum()),raw_0p5pct_mass_capture=capture(raw_ids),relative_0p5pct_mass_capture=capture(ratio_ids),fixed_two_source_selected_mass_capture=capture(two_ids),fixed_multi24_selected_mass_capture=capture(multi_ids),raw_budget_zero_score_count=int((raw[raw_ids]<=0).sum()),ratio_budget_zero_score_count=int((relative[ratio_ids]<=0).sum()),footprint_radius_px_positive_quantiles=quantiles(a['radius'][raw>0]),raw_budget_semantics='full alphaT soft-rim participation, not old normal-difference D',unknown_truncated_mass=0,operator='stage CPU replica of full stock accepted alphaT; calibration is separate'))
  perview_ids[key+'_raw_budget_ids']=raw_ids.astype(np.int32);perview_ids[key+'_relative_budget_ids']=ratio_ids.astype(np.int32);source_hashes[str(path)]=rt.sha(path);a.close()
 np.testing.assert_array_equal(weak_counts,multi['distinct_views'])
 np.testing.assert_allclose(rim_total,multi['rim_mass'],rtol=1e-6,atol=1e-4)
 ply=PlyData.read(scene['model'])['vertex'];xyz=np.column_stack([ply[k] for k in ['x','y','z']]);two_shown=display_ids(two_ids);multi_shown=display_ids(multi_ids)
 display_path=rt.ART/'supplemental'/name/'DISPLAY_AND_DIAGNOSTIC_IDS.npz';rt.npz(display_path,two_source_display_ids=two_shown,multi24_display_ids=multi_shown,**perview_ids)
 covariance_corr=float(np.corrcoef(weak_counts[multi_ids],np.log1p(rim_total[multi_ids]))[0,1]) if len(multi_ids)>1 and np.std(weak_counts[multi_ids])>0 and np.std(rim_total[multi_ids])>0 else None
 result=dict(camera_domain=camera_summary(scene),views=records,selected_two_source_count=len(two_ids),selected_multi24_count=len(multi_ids),additional_multisource_IDs=int(len(np.setdiff1d(multi_ids,two_ids))),two_source_IDs_absent_from_multi24=int(len(np.setdiff1d(two_ids,multi_ids))),two_source_selected_distinct_view_histogram=hist(two['distinct_views'][two_ids]),multi24_selected_distinct_view_histogram=hist(weak_counts[multi_ids]),multi24_selected_positive_contribution_view_histogram=hist(positive_views[multi_ids]),multi24_selected_summed_soft_rim_mass=quantiles(rim_total[multi_ids]),count_vs_log_mass_pearson=covariance_corr,distinct_views_definition='Count of different camera keys satisfying visible_mass>=0.1, rim_mass>=0.01 and rim_mass/visible_mass>=0.12. It is not raw pixel votes, pixel count, or summed alphaT mass.',fusion_definition='Per-ID maximum regularized relative responsiveness plus single-hop 3D hysteresis, not repeated-view vote summation.',diagnostic_mass_capture_summary={key:quantiles([r[key] for r in records]) for key in ['raw_0p5pct_mass_capture','relative_0p5pct_mass_capture','fixed_two_source_selected_mass_capture','fixed_multi24_selected_mass_capture']},display_sampling=dict(rule='Sort original IDs ascending; choose integer indices linspace(0,n-1,min(12000,n)). Every displayed ID saved; these plots are deterministic samples, not full selected sets or footprints.',cap_per_panel=DISPLAY_MAX,two_source_displayed=len(two_shown),multi24_displayed=len(multi_shown),IDs_file=str(display_path)),source_sha256=source_hashes,fusion_sha256={'two_source':rt.sha(two_path),'multi24':rt.sha(multi_path)},only_construction_evidence_read=True,selection_or_asset_changed=False,semantic_status='Kernel-support diagnostics, not certified physical edges; world-center plot is not the rendered region asset.')
 result['support_domain_levels']={arm:dict(original_N=n,hysteresis_candidate_count=len(a['selected_ids']),hysteresis_candidate_fraction_of_full_model=float(len(a['selected_ids'])/n),score_above_region_level_count=int((a['score'][a['selected_ids']]>.100001).sum()),score_level=.100001) for arm,a in [('two_source',two),('multi24',multi)]}
 result['sealed_region_levels']=[]
 for path in sorted((rt.ART/'regions'/name).glob('*.npz')):
  unit=name+'_region_'+path.stem
  if not (rt.ART/'seals'/(unit+'.json')).exists():continue
  if not rt.resume(unit):continue
  a=np.load(path);support=a['support_ids'];retained=a['retained_owner_ids'];anchors=np.unique(a['vertex_anchor_ids'])
  if not np.isin(retained,support).all() or not np.isin(anchors,retained).all():raise RuntimeError('owner/anchor provenance not nested within support')
  result['sealed_region_levels'].append(dict(region=path.stem,path=str(path),sha256=rt.sha(path),support_after_score_level_count=len(support),retained_raw_voxel_owner_count=len(retained),unique_vertex_anchor_count=len(anchors),mesh_vertex_count=len(a['vertex_anchor_ids']),support_discarded_as_owner_count=len(support)-len(retained),vertex_anchor_fraction_of_original_N=float(len(anchors)/n),occupied_voxels=int(a['occupied_voxels']),world_width_floor=float(a['width_world_floor']),vertex_world_displacement=quantiles(a['vertex_displacement']),original_mahalanobis_displacement=quantiles(a['vertex_original_mahalanobis']),geometric_nearest_center_differs_from_actual_raw_owner=int((a['vertex_nearest_center_ids']!=a['vertex_anchor_ids']).sum()),fill_voxels_all=len(a['fill_grid_indices']),fill_voxels_surviving=int((~a['fill_rejected']).sum()),fill_witness_distinct_original_IDs=int(len(np.unique(a['fill_witness_ids']))),provenance_statement='Candidates, score-level supports, retained voxel winner owners, and final vertex anchors are distinct domains. Losing ownership does not imply zero Gaussian contribution.'))
  a.close()
 plot=dict(xyz=xyz,two_ids=two_ids,multi_ids=multi_ids,two_shown=two_shown,multi_shown=multi_shown,counts=weak_counts,two_counts=two['distinct_views'],rim_total=rim_total,views=views)
 two.close();multi.close();return result,plot,display_path

def plots(freeze,results,data,out):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.colors import Normalize
 plt.rcParams.update({'font.size':10})
 # Explicit directional domain, showing unsampled lower hemisphere.
 fig,axs=plt.subplots(1,2,figsize=(14,5),sharex=True,sharey=True)
 for ax,(name,scene) in zip(axs,freeze['scenes'].items()):
  cameras=scene['cameras'];keys=list(cameras);d=np.array([cameras[k]['direction'] for k in keys]);az=np.degrees(np.arctan2(d[:,1],d[:,0]));el=np.degrees(np.arcsin(np.clip(d[:,2],-1,1)))
  ax.axhspan(-90,0,color='#f5dddd',alpha=.8);ax.scatter(az,el,s=15,c='#aaaaaa',label='All 86 metadata directions (no images read)')
  for kk,color,label,size in [(scene['roles']['construction'][2:],'#246eab','Additional 22 construction sources',37),(scene['roles']['construction'][:2],'#dc7730','First 2 construction sources',65)]:
   dd=np.array([cameras[k]['direction'] for k in kk]);ax.scatter(np.degrees(np.arctan2(dd[:,1],dd[:,0])),np.degrees(np.arcsin(dd[:,2])),s=size,c=color,label=label,edgecolors='white',linewidths=.6)
  for k in scene['roles']['construction'][:2]:
   q=np.array(cameras[k]['direction']);ax.annotate(k,(np.degrees(np.arctan2(q[1],q[0])),np.degrees(np.arcsin(q[2]))),xytext=(4,4),textcoords='offset points')
  note='No observed bottom hemisphere\n(no construction cameras below equator)' if results[name]['camera_domain']['below_equator_construction_count']==0 else 'Bottom hemisphere coverage is limited\nsee actual construction directions'
  ax.text(0,-45,note,ha='center',va='center',color='#944444');ax.set(title=name+' | metadata-only camera domain',xlabel='Azimuth / degrees',xlim=(-180,180),ylim=(-90,90));ax.grid(alpha=.2);ax.legend(loc='lower left',fontsize=8)
 axs[0].set_ylabel('Elevation / degrees');fig.suptitle('Direction coverage is a camera-domain diagnostic, not a surface-visibility certificate');fig.tight_layout();p=out/'CAMERA_DIRECTION_DOMAIN.png';fig.savefig(p,dpi=150);plt.close(fig);files=[p]
 fig=plt.figure(figsize=(14,11));norm=Normalize(1,24)
 for row,name in enumerate(['lego','chair']):
  a=data[name];full=a['xyz'][a['multi_ids']];lo=full.min(0);hi=full.max(0);center=(lo+hi)/2;extent=float(np.max(hi-lo))*.53
  for col,key in enumerate(['two','multi']):
   ids=a[key+'_shown'];counts=a['two_counts'][ids] if key=='two' else a['counts'][ids];total=len(a[key+'_ids']);ax=fig.add_subplot(2,2,row*2+col+1,projection='3d')
   scatter=ax.scatter(*a['xyz'][ids].T,c=counts,cmap='viridis',norm=norm,s=1.25,alpha=.8,rasterized=True)
   ax.set(xlim=(center[0]-extent,center[0]+extent),ylim=(center[1]-extent,center[1]+extent),zlim=(center[2]-extent,center[2]+extent),xlabel='World X',ylabel='World Y',zlabel='World Z',title=f'{name} | '+('2 sources' if key=='two' else '24 sources')+f' | shown {len(ids):,} / selected {total:,}')
   ax.set_box_aspect((1,1,1));ax.view_init(elev=19,azim=-52)
 fig.colorbar(scatter,ax=fig.axes,shrink=.45,pad=.025,label='Distinct responsive construction cameras (not pixel mass)');fig.suptitle('Selected original kernel CENTERS: deterministic original-ID sample, not full footprints or final meshes',y=.97)
 p=out/'TWO_VS_24_SELECTED_WORLD_CENTERS.png';fig.savefig(p,dpi=160,bbox_inches='tight');plt.close(fig);files.append(p)
 fig,axs=plt.subplots(2,2,figsize=(14,8))
 for row,name in enumerate(['lego','chair']):
  r=results[name];x=np.arange(len(r['views']));ax=axs[row,0]
  for key,label in [('raw_0p5pct_mass_capture','Raw alphaT top 0.5%'),('relative_0p5pct_mass_capture','Relative response top 0.5%'),('fixed_two_source_selected_mass_capture','Fixed 2-source support'),('fixed_multi24_selected_mass_capture','Fixed 24-source support')]:ax.plot(x,[v[key] for v in r['views']],'.-',label=label,lw=1)
  ax.set(title=name+' | soft-rim mass captured (budgets unequal)',ylabel='Fraction of complete accepted rim mass',ylim=(0,1.02));ax.set_xticks(x);ax.set_xticklabels([v['camera'] for v in r['views']],rotation=90,fontsize=7);ax.legend(fontsize=8);ax.grid(alpha=.2)
  a=data[name];ids=a['multi_shown'];ax=axs[row,1];ax.scatter(a['counts'][ids],a['rim_total'][ids],s=2,alpha=.25);ax.set(yscale='log',xlabel='Distinct responsive cameras',ylabel='Summed soft-rim alphaT mass',title=name+' | sampled selected IDs: view count != pixel mass');ax.grid(alpha=.2)
 fig.suptitle('Construction evidence only; diagnostic ranking does not replace the frozen selection rule');fig.tight_layout();p=out/'MASS_BUDGET_AND_DISTINCT_VIEWS.png';fig.savefig(p,dpi=150);plt.close(fig);files.append(p)
 fig,axs=plt.subplots(1,2,figsize=(14,5))
 for ax,name in zip(axs,['lego','chair']):
  r=results[name]
  for arm,color in [('two_source','#d37a31'),('multi24','#246eab')]:
   base=r['support_domain_levels'][arm];regions=[q for q in r['sealed_region_levels'] if q['region'].startswith(arm+'_')]
   if not regions:ax.plot([0,1],[base['hysteresis_candidate_count'],base['score_above_region_level_count']],'o-',c=color,label=arm+' (regions not yet sealed)')
   for q in regions:
    values=[base['hysteresis_candidate_count'],q['support_after_score_level_count'],q['retained_raw_voxel_owner_count'],q['unique_vertex_anchor_count']]
    ax.plot(range(4),values,'o-',alpha=.8,c=color,label=q['region']+' | world floor '+format(q['world_width_floor'],'.4g'))
   ax.text(0,base['hysteresis_candidate_count'],f' {base["hysteresis_candidate_count"]:,} ({100*base["hysteresis_candidate_fraction_of_full_model"]:.1f}% N)',fontsize=8,color=color,va='bottom')
  ax.set_xticks(range(4));ax.set_xticklabels(['Hysteresis\ncandidates','Score-level\nregion support','Retained raw\nvoxel owners','Unique mesh\nvertex anchors']);ax.set(title=name+' | distinct original-ID domains',ylabel='Original ID count');ax.grid(alpha=.2);ax.legend(fontsize=7)
 fig.suptitle('Expanded candidate coverage is an unequal-budget hypothesis; retained owners/anchors are different counts');fig.tight_layout();p=out/'SUPPORT_DOMAIN_REDUCTION.png';fig.savefig(p,dpi=150);plt.close(fig);files.append(p);return files

def main():
 rt.guard('supplemental_source_analysis_start');freeze=json.loads((rt.ART/'INPUT_FREEZE.json').read_text());results={};data={};files=[]
 # Refuse partial execution before both scenes and both arms are available.
 for name in ['lego','chair']:
  for arm in ['two_source','multi24']:
   if not (rt.ART/'seals'/(name+'_fusion_'+arm+'.json')).exists():raise RuntimeError('both scenes must be sealed before supplemental analysis')
 for name in ['lego','chair']:
  results[name],data[name],path=analyze_scene(name,freeze['scenes'][name]);files.append(path)
 out=rt.ART/'supplemental';files+=plots(freeze,results,data,out)
 report=out/'SOURCE_COVERAGE_ANALYSIS.json';rt.atomic_json(report,dict(status='VALID_CONSTRUCTION_ONLY_SUPPLEMENT',method_unchanged=True,images_read=False,view_roles_frozen_before_sources=True,source_operator_note='independently calibrated CPU stock-rules replica, not live native CUDA execution',scenes=results));files.append(report)
 rt.seal('supplemental_source_coverage',files,dict(status='COMPLETE',scenes={k:{'two_source':r['selected_two_source_count'],'multi24':r['selected_multi24_count'],'additional':r['additional_multisource_IDs']} for k,r in results.items()},construction_only=True,method_or_asset_modified=False))
 print(json.dumps({k:{'two_source':r['selected_two_source_count'],'multi24':r['selected_multi24_count'],'mass_capture':r['diagnostic_mass_capture_summary']} for k,r in results.items()},indent=2))

if __name__=='__main__':main()
