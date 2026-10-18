from env import *
from responsibility import ProjectedSource,measure_difference
from geometry_roles import classify,fit_patch,plane_ray_depth
from measure import query_case,calibration,unique_rows
from conditional import enrich
import copy,zlib
ARMS=['line','shifted_12px','source_geometry_axis','shuffled_sides']
def baseline(case,arm,c,raw,proj,source):
 cache=OLD/'scenes'/case['scene']/'stage1'/c['view']/case['case']/('line' if arm=='shuffled_sides' else arm)
 if (cache/'RESULT.json').exists():r=json.loads((cache/'RESULT.json').read_text());e=npz(cache/'EVIDENCE.npz')
 else:r,e=query_case(case,'line' if arm=='shuffled_sides' else arm,c,raw,proj,source)
 if arm!='shuffled_sides':return r,e,str(cache) if cache.exists() else 'new source-only measurements'
 e={k:v.copy() for k,v in e.items()};r=copy.deepcopy(r);k=e['side_offset']!=0;rng=np.random.default_rng(zlib.crc32((case['scene']+case['case']+c['view']).encode()));e['side_offset'][k]=rng.permutation(e['side_offset'][k]);side=e['side_offset'];rows=[]
 for lo,hi in zip(e['csr_offsets'][:-1],e['csr_offsets'][1:]):rows.append(dict(ids=e['source_index'][lo:hi],weight=e['weight'][lo:hi]))
 lr,li=unique_rows(rows,e['query_uv'],side<0);rr,ri=unique_rows(rows,e['query_uv'],side>0);d=measure_difference(lr,rr);p=r['info']['pixel_world_proxy'];patches=[]
 for name,ix in [('left',li),('right',ri)]:
  ix=ix[e['patch_valid'][ix]];pa=fit_patch(unproject(e['query_uv'][ix],e['native_z'][ix],c),e['query_alpha'][ix],p);r[name+'_patch']=pa;e[name+'_points']=np.array(pa['points']).reshape(-1,3);e[name+'_patch_source_uv']=e['query_uv'][ix];patches.append(pa)
 z1=plane_ray_depth(patches[0],e['proposed_line_uv'],c);z2=plane_ray_depth(patches[1],e['proposed_line_uv'],c);valid=np.isfinite(z1-z2);r['info'].update(L1=d['L1'],alpha_left=d['left_alpha'],alpha_right=d['right_alpha'],join_pixels=float(np.median(abs(z1[valid]-z2[valid]))/p) if valid.any() else 1e9);r['role']=classify(*patches,r['info']);r['arm']=arm;r['front_side']='shuffled_label_null';r['offset_evidence']={};r['overlap']=d['overlap'];e.update(participant_ids=d['ids'],left_mass=d['left'],right_mass=d['right'],differential_responsibility=d['difference']);return r,e,'same line pixel/weight budget; deterministic shuffled side labels'
def condition_result(r,e,a,c):
 q=enrich(e,a,c);st=q['conditional_stats'];p=r['info']['pixel_world_proxy'];native=e['native_z'];eligible=e['patch_valid'];valid=eligible&(st[:,4]>=.8)&np.isfinite(st[:,5]);close=valid&(abs(st[:,1]-native)<=np.maximum(.02*native,4*p));fraction=float(close.sum()/max(1,eligible.sum()));x=r['info'].copy();x['ray_width_pixels']=float(np.median(st[close,5])/p) if close.any() else 1e9;x['center_supported']=x['center_supported'] and fraction>=.8;role=classify(r['left_patch'],r['right_patch'],x)
 if role['reason']=='broad_source_center_depth_mixture_not_a_surface_proof':role['reason']='broad_conditional_modes_or_conditional_sigma_proxy'
 if not x['center_supported'] and r['info']['center_supported']:role['reason']='conditional_finite_mass_or_native_consistency_unqualified'
 out=dict(scene=r['scene'],case=r['case'],view=r['view'],arm=r['arm'],parent_id=r['parent_id'],source_views=r['source_views'],old_role=r['role'],conditional_role=role,old_width_p=r['info']['ray_width_pixels'],conditional_width_p=x['ray_width_pixels'],qualified_pixel_fraction=fraction,conditional_native_median_error_p=float(np.median(abs(st[close,1]-native[close]))/p) if close.any() else None,eligible_pixels=int(eligible.sum()),qualified_pixels=int(close.sum()),source_count_total=len(a['means']),alphaT_unchanged=True,ordering='original source center-z',physical_primitive_certified=False)
 q['conditional_pixel_qualified']=close;return out,q
def acquire(s,views,root):
 a=activate(read_ply(registry()[s]['model']));t0=time.time();results=[]
 for v in views:
  c=cam(s,v);raw=npz(rawpath(s,v));proj=ProjectedSource.from_asset(a,c,s);refpath=root/s/v/'reference';refpath.mkdir(parents=True,exist_ok=True)
  # Legacy calibration writes its simple per-directory seal. Store only new task output.
  if (refpath/'SEAL.json').exists():checkseal(refpath);ref=npz(refpath/'REFERENCE.npz');cal=json.loads((refpath/'CALIBRATION.json').read_text())
  else:ref,cal=calibration(s,c,raw,a,proj,refpath)
  assert cal['engineering_go'],(s,v,'ENGINEERING_INVALID');
  for case in cases(s):
   d=root/s/v/case['case'];d.mkdir(exist_ok=True)
   if not case['selection_valid']:js(d/'UNAVAILABLE.json',dict(reason='inherited selection failure, no replacement',original_case=case));continue
   for arm in ARMS:
    out=d/arm;out.mkdir(exist_ok=True)
    if (out/'SEAL.json').exists():checkseal(out);results.append(json.loads((out/'RESULT.json').read_text()));continue
    r,e,provenance=baseline(case,arm,c,raw,proj,a);res,q=condition_result(r,e,a,c);np.savez_compressed(out/'EVIDENCE.npz',**e,**q);js(out/'CENTER_BASELINE.json',r);res['input_measurement']=provenance;js(out/'RESULT.json',res);seal(out);results.append(res);print(s,v,case['case'],arm,r['role']['role'],'->',res['conditional_role']['role'],res['conditional_width_p'],flush=True)
   if time.time()-t0>5400:raise TimeoutError('Frozen per-round wall bound reached')
 return results
