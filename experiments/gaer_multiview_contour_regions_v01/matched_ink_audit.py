"""Isolated post-protocol DEV ink control. Never changes any primary result.

Run only after the root coordinator declares its primary producer idle.  Only
historical A tube radius changes; the multi24 target stays permanently sealed.
"""
import hashlib,json,traceback
from pathlib import Path
import numpy as np
from PIL import Image
import runtime as rt
from contracts import camera_for
from fusion import evidence
from metrics import measure
from mesh_tools import render_mesh,tube_mesh,export_mesh,write_viewer
from media_tools import save_image,make_panel

NAME='post_protocol_dev_ink_diagnostic'
PROTOCOL=rt.ART/'PROTOCOL_MATCHED_INK_AUDIT.json'
BASE=rt.ART/NAME

def geometry_hash(vertices,faces):
 # Canonical serialized mesh storage. Historical primary tube hashes used the
 # pre-export int64 edge-offset arithmetic; values survive int32 export exactly.
 return rt.digest(dict(vertices_sha256=hashlib.sha256(np.asarray(vertices,dtype=np.float32).tobytes()).hexdigest(),faces_sha256=hashlib.sha256(np.asarray(faces,dtype=np.int32).tobytes()).hexdigest()))

def unit(scene,stage):return scene+'_'+NAME+'_'+stage

def load_primary(scene):
 if not rt.resume(scene+'_asset'):raise RuntimeError('primary fixed asset seal missing')
 rec=json.loads((rt.ART/'results'/(scene+'_asset.json')).read_text());meshes={};notes={}
 for arm in ['multi24','widened']:
  with np.load(rt.ROOT/rec['arms'][arm]['paths']['npz']) as a:meshes[arm]={'vertices':a['vertices'],'faces':a['faces']}
  canonical=geometry_hash(**meshes[arm]);declared=rec['arms'][arm]['geometry_sha256']
  if canonical!=declared:
   v=meshes[arm]['vertices'];f=meshes[arm]['faces'];legacy=rt.digest(dict(vertices_sha256=hashlib.sha256(v.tobytes()).hexdigest(),faces_sha256=hashlib.sha256(f.astype(np.int64).tobytes()).hexdigest()))
   if arm!='widened' or legacy!=declared:raise RuntimeError('primary geometry hash mismatch beyond documented int64/int32 serialization')
   notes[arm]=dict(declared_hash=declared,serialized_canonical_hash=canonical,legacy_int64_faces_hash_matches=True,serialized_faces_dtype=str(f.dtype),index_values_unchanged=True,explanation='Primary tube hash was calculated before exporter converted int64 face indices to int32; no coordinate/index-value change.')
 rec['hash_normalization_notes']=notes
 return rec,meshes

def raw(scene,key):
 if not rt.resume(scene+'_rgb_'+key):raise RuntimeError('existing primary RGB/alpha unit unavailable '+scene+' '+key)
 path=rt.OUT/'renders'/scene/(key+'.npz')
 with np.load(path) as a:return a['rgb'],a['alpha'],path

def fit_and_seal(name,scene):
 key=unit(name,'asset')
 if rt.resume(key):return json.loads((rt.ART/'results'/(key+'.json')).read_text())
 rt.guard(key);protocol=json.loads(PROTOCOL.read_text())
 if protocol['preregistered_main_arm'] is not False or protocol['search']['bisection_steps']!=12:raise RuntimeError('unexpected diagnostic protocol')
 primary,meshes=load_primary(name);target_mesh=meshes['multi24'];devkeys=scene['roles']['dev'];dev=[camera_for(scene,k,'develop') for k in devkeys]
 es=[];dev_raw={}
 for c in dev:
  _,alpha,p=raw(name,c['key']);es.append(evidence(alpha));dev_raw[c['key']]=rt.sha(p)
 target_renders=[render_mesh(**target_mesh,camera=c,color=(18,18,18)) for c in dev];target_counts=[int(r['mask'].sum()) for r in target_renders];target=float(np.mean(target_counts))
 if target<=0:raise RuntimeError('empty primary ink target; diagnostic invalid')
 old_path=Path('/home/u00134/3dgs_line/gaer_kernel_space_lines_v01/artifacts/gaer_kernel_space_lines_v01/assets')/name/'FULL_GRAPH.npz'
 with np.load(old_path) as g:xyz=g['xyz'];edges=g['A'];original_ids=g['ids'];start=float(g['radius'])
 diagonal=float(np.linalg.norm(np.ptp(target_mesh['vertices'],axis=0)));upper=.5*diagonal
 if not 0<start<=upper:raise RuntimeError('invalid diagnostic radius interval')
 folder=BASE/name;trials=[];cache={};trial_path=folder/'DEV_RADIUS_TRIALS.json'
 def trial(radius,phase):
  radius=float(radius)
  if radius.hex() in cache:return cache[radius.hex()]
  v,f=tube_mesh(xyz,edges,radius);ink=[int(render_mesh(v,f,c)['mask'].sum()) for c in dev];avg=float(np.mean(ink));r=dict(index=len(trials),phase=phase,radius_world=radius,diameter_world=2*radius,dev_cameras=devkeys,ink_pixels_per_view=ink,mean_ink_pixels=avg,target_mean_ink_pixels=target,signed_mean_ink_error=avg-target,relative_absolute_error=abs(avg-target)/target)
  trials.append(r);cache[radius.hex()]=r
  rt.atomic_json(trial_path,dict(status='RUNNING_DEV_ONLY_SEARCH',protocol_sha256=rt.sha(PROTOCOL),scene=name,target_camera_ink=target_counts,target_mean_ink=target,scene_diagonal=diagonal,max_radius=upper,trials=trials,reserved_read_by_this_diagnostic=False))
  return r
 first=trial(start,'original_radius');lo=start;hi=start;bracket=False
 if first['mean_ink_pixels']<=target:
  previous=first
  while hi<upper and previous['mean_ink_pixels']<target:
   lo=hi;hi=min(2*hi,upper);previous=trial(hi,'doubling_expansion')
  bracket=previous['mean_ink_pixels']>=target
  if bracket:
   for _ in range(12):
    mid=(lo+hi)/2;r=trial(mid,'bisection')
    if r['mean_ink_pixels']<target:lo=mid
    else:hi=mid
 best=min(trials,key=lambda r:(r['relative_absolute_error'],r['radius_world']));matched=best['relative_absolute_error']<.01;status='DIAGNOSTIC_MATCHED' if matched else 'DIAGNOSTIC_UNMATCHED'
 v,f=tube_mesh(xyz,edges,best['radius_world']);ex=export_mesh(folder/'assets',v,f,name='same_A_matched_ink_outer');geometry=geometry_hash(v,f)
 dev_metrics=[measure(render_mesh(v,f,c)['mask'],e) for c,e in zip(dev,es)]
 capped=[measure(render_mesh(**meshes['widened'],camera=c)['mask'],e) for c,e in zip(dev,es)];main=[measure(r['mask'],e) for r,e in zip(target_renders,es)]
 original_develop=json.loads((rt.ART/'results'/(name+'_develop.json')).read_text())
 final=dict(status=status,name=NAME,preregistered_main_arm=False,protocol_sha256=rt.sha(PROTOCOL),scene=name,original_N=scene['count'],graph_original_ID_count=len(original_ids),unchanged_graph_edges=len(edges),historical_graph_path=str(old_path),historical_graph_sha256=rt.sha(old_path),historical_original_radius=start,radius_world=best['radius_world'],world_diameter=2*best['radius_world'],radius_multiplier_vs_original=best['radius_world']/start,scene_diagonal=diagonal,max_radius=upper,target_mean_DEV_ink=target,target_DEV_ink_by_camera=dict(zip(devkeys,target_counts)),actual_mean_DEV_ink=best['mean_ink_pixels'],relative_ink_error=best['relative_absolute_error'],target_bracketed=bracket,bisection_evaluations=sum(t['phase']=='bisection' for t in trials),trials=trials,original_capped_DEV_relative_error=original_develop['ink_match_relative_error'],original_capped_world_radius=original_develop['widened']['radius'],dev_metrics=dict(multi24=main,primary_capped_widened=capped,post_protocol_matched=dev_metrics),dev_raw_sha256=dev_raw,geometry_sha256=geometry,paths={k:str(Path(p).relative_to(rt.ROOT)) for k,p in ex.items()},main_geometry_sha256={a:primary['arms'][a]['geometry_sha256'] for a in ['multi24','widened']},main_model_sha256=scene['model_sha256'],reserved_read_by_this_diagnostic=False,reserved_already_used_by_main_experiment=True,claim='Additional DEV-only equal-ink diagnostic, not a primary arm or a rescue of fusion; primary protocol, width selection, gates, assets and results unchanged.',visibility='asset self-zbuffer; x-ray relative original GS')
 final['primary_hash_normalization_notes']=primary['hash_normalization_notes'];final['diagnostic_geometry_hash_convention']='float32 vertices / int32 faces, matching exported NPZ storage'
 rt.atomic_json(trial_path,final);viewer=folder/'assets/viewer_3d.html';write_viewer(viewer,{'primary multi24 fixed region':meshes['multi24'],'primary capped widened A':meshes['widened'],'post-protocol matched-ink A':{'vertices':v,'faces':f}})
 rt.seal(key,[Path(p) for p in ex.values()]+[trial_path,viewer,PROTOCOL],final);print('MATCHED_INK_ASSET',name,status,best['relative_absolute_error'],best['radius_world'],flush=True);return final

def evaluate_reserved(name,scene):
 asset_unit=unit(name,'asset')
 if not rt.resume(asset_unit):raise RuntimeError('diagnostic reserved access before geometry seal')
 final=json.loads((rt.ART/'results'/(asset_unit+'.json')).read_text());primary,meshes=load_primary(name)
 with np.load(rt.ROOT/final['paths']['npz']) as a:meshes['post_protocol_matched']={'vertices':a['vertices'],'faces':a['faces']}
 if geometry_hash(**meshes['post_protocol_matched'])!=final['geometry_sha256']:raise RuntimeError('diagnostic mesh changed')
 outputs=[];records=[];rows=[]
 for camkey in scene['roles']['reserved']:
  viewunit=unit(name,'reserved_'+camkey);folder=BASE/name/'reserved'/camkey;c=camera_for(scene,camkey,'eval',True)
  if not rt.resume(viewunit):
   rgb,alpha,rawpath=raw(name,camkey);e=evidence(alpha);metrics={};paths=[];items=[('RGB / reused construction-holdout '+camkey,np.clip(rgb*255,0,255).astype(np.uint8))]
   save_image(folder/'RGB_SH3.png',items[0][1]);paths.append(folder/'RGB_SH3.png')
   for arm,label in [('multi24','Main fixed multi24'),('widened','Main old-A capped width'),('post_protocol_matched','POST-PROTOCOL old-A matched DEV ink')]:
    r=render_mesh(**meshes[arm],camera=c,color=(18,18,18));metrics[arm]=measure(r['mask'],e);p=folder/(arm+'.png');save_image(p,r['rgb']);paths.append(p);items.append((label+' / same fixed mesh / xray wrt GS',r['rgb']))
   p=folder/'comparison.png';make_panel([items],p,tile_size=800,title=NAME+' | '+name+' '+camkey+' | additional diagnostic, not a primary arm');paths.append(p)
   result=dict(status='VALID_FIXED_DIAGNOSTIC_EVAL',name=NAME,scene=name,camera=camkey,camera_sha256=c['camera_sha256'],actual_camera=c,role='reserved_reused_after_primary_evaluation',diagnostic_asset_sealed_before_this_evaluation=True,geometry_sha256={'multi24':primary['arms']['multi24']['geometry_sha256'],'widened':primary['arms']['widened']['geometry_sha256'],'post_protocol_matched':final['geometry_sha256']},primary_main_geometry_unchanged=True,RGB_alpha_sha256=rt.sha(rawpath),metrics=metrics,visibility=final['visibility'])
   rt.seal(viewunit,paths+[PROTOCOL],result)
  result=json.loads((rt.ART/'results'/(viewunit+'.json')).read_text());records.append(result)
  row=[]
  for label,file in [('RGB','RGB_SH3.png'),('main multi24','multi24.png'),('main capped A','widened.png'),('post-protocol equal-ink A','post_protocol_matched.png')]:
   p=folder/file
   with Image.open(p) as image:row.append((name+' '+camkey+' / '+label,np.asarray(image.convert('RGB'))))
   outputs.append(p)
  rows.append(row)
 panel=BASE/name/'reserved_eight_additional_FULL.png';make_panel(rows,panel,title='POST-PROTOCOL DEV INK DIAGNOSTIC | '+name+' | reused holdouts, primary artifacts unchanged',tile_size=800);outputs.append(panel)
 preview=BASE/name/'reserved_eight_additional_preview.jpg'
 with Image.open(panel) as im:im.resize((1600,round(im.height/2))).save(preview,quality=93)
 outputs.append(preview)
 keys=list(records[0]['metrics']['multi24']);means={arm:{k:float(np.mean([r['metrics'][arm][k] for r in records])) for k in keys} for arm in ['multi24','widened','post_protocol_matched']}
 result=dict(status='COMPLETE_ADDITIONAL_DIAGNOSTIC',name=NAME,main_protocol_or_assets_changed=False,asset_status=final['status'],DEV_relative_ink_error=final['relative_ink_error'],DEV_radius=final['radius_world'],reserved_prior_exposure=True,reserved_camera_count=len(records),per_view=records,mean_reserved_metrics=means,mean_metric_caveat='Simple per-view arithmetic means; area match is DEV mean only and is not guaranteed for every reserved camera.',scientific_gate_modified=False,claim_limit='Post-protocol area-matching control only, not a preregistered primary comparison or fresh blind test.')
 metrics_path=BASE/name/'ADDITIONAL_METRICS.json';rt.atomic_json(metrics_path,result);outputs.append(metrics_path);rt.seal(unit(name,'complete'),outputs+[PROTOCOL],result)
 print('MATCHED_INK_RESERVED_COMPLETE',name,final['relative_ink_error'],flush=True);return result

def main():
 # Existing protocol is a separate artifact; never overwrite primary PROTOCOL.
 if not PROTOCOL.exists():raise RuntimeError('additional protocol must be frozen before DEV search')
 freeze=json.loads((rt.ART/'INPUT_FREEZE.json').read_text());results={}
 protected=[rt.ART/'PROTOCOL.json',rt.ART/'INPUT_FREEZE.json']+[p for p in (rt.ART/'assets').rglob('*') if p.is_file()]
 for name in ['lego','chair']:
  for stage in ['develop','asset','reserved_complete']:
   protected.extend([rt.ART/'results'/(name+'_'+stage+'.json'),rt.ART/'seals'/(name+'_'+stage+'.json')])
  protected.extend([rt.ART/'media'/name/'reserved_eight_FULL.png',rt.ART/'media'/name/'reserved_eight_preview.jpg'])
 before={str(p):rt.sha(p) for p in protected if p.exists()};rt.atomic_json(BASE/'PRIMARY_PROTECTED_BEFORE.json',before)
 for name in ['lego','chair']:
  try:
   fit_and_seal(name,freeze['scenes'][name]);results[name]=evaluate_reserved(name,freeze['scenes'][name])
  except Exception as error:
   failure=BASE/name/'FAILURE.json';rt.atomic_json(failure,dict(status='INVALID_OR_INCOMPLETE_DIAGNOSTIC',error=repr(error),traceback=traceback.format_exc(),primary_results_untouched=True));results[name]={'status':'INVALID_OR_INCOMPLETE_DIAGNOSTIC','failure':str(failure)}
 changed=[p for p,h in before.items() if not Path(p).exists() or rt.sha(p)!=h]
 rt.atomic_json(BASE/'PRIMARY_PROTECTED_AFTER.json',dict(checked_files=len(before),unchanged=not changed,changed=changed))
 rt.atomic_json(BASE/'SUMMARY.json',results);rt.guard('matched_ink_diagnostic_complete')
 if changed:raise RuntimeError('primary protected artifacts changed: '+str(changed))
 if any(r['status']=='INVALID_OR_INCOMPLETE_DIAGNOSTIC' for r in results.values()):raise SystemExit(1)

if __name__=='__main__':main()
