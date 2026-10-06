import runtime as rt
import json,time,traceback,shutil
from pathlib import Path
import numpy as np
from PIL import Image
from cpu_native import load_model_cpu,preprocess,rasterize
from fusion import evidence,fuse,select_support
from regions import build_region
from mesh_tools import render_mesh,tube_mesh,export_mesh,write_viewer
from metrics import measure,objective
from media_tools import save_image,make_panel,make_strip,encode_video
from contracts import camera_for
_models={}
def frozen():return json.loads((rt.ART/'INPUT_FREEZE.json').read_text())
def scene(n):return frozen()['scenes'][n]
def model(n):
 if n not in _models:_models[n]=load_model_cpu(scene(n))
 return _models[n]
def seal(unit,files,result):
 result=dict(result,method_hashes={p.name:rt.sha(p) for p in rt.EXP.glob('*.py')})
 rt.seal(unit,files+[rt.ART/'INPUT_FREEZE.json',rt.ART/'PROTOCOL.json'],result)
def raw_path(n,key):return rt.OUT/'renders'/n/(key+'.npz')
def source_path(n,key):return rt.ART/'sources'/n/(key+'.npz')
def base_render(n,c):
 path=raw_path(n,c['key']);unit=n+'_rgb_'+c['key']
 if rt.resume(unit):
  r=dict(np.load(path));return r
 rt.guard(unit);p=preprocess(model(n),c);r=rasterize(p)
 rt.npz(path,rgb=r['rgb'],alpha=r['alpha'])
 seal(unit,[path],dict(status='VALID_CPU_CALIBRATED_RENDER',camera_sha256=c['camera_sha256'],camera=c['key'],model_sha256=scene(n)['model_sha256']))
 return r
def extract_view(n,key):
 unit=n+'_extract_'+key
 if rt.resume(unit):return
 c=camera_for(scene(n),key,'extract');rt.guard(unit);t=time.time();p=preprocess(model(n),c);r=rasterize(p);e=evidence(r['alpha']);a=rasterize(p,maps=e['maps'])
 path=source_path(n,key);rt.npz(path,original_ids=np.arange(len(a['mass']),dtype=np.int32),visible_mass=a['mass'].astype(np.float32),rim_narrow=a['adjoints'][:,0].astype(np.float32),rim_wide=a['adjoints'][:,1].astype(np.float32),hole_mass=a['adjoints'][:,2].astype(np.float32),xy=p['xy'],conic=p['conic'],radius=p['radius'],depth=p['depth'],cov2d=p['cov2d'],camera_sha256=np.asarray(c['camera_sha256']),role=np.asarray('construction'))
 rp=raw_path(n,key);rt.npz(rp,rgb=r['rgb'],alpha=r['alpha']);save_image(rt.ART/'media'/n/'construction'/(key+'_RGB.png'),r['rgb'])
 mass=a['mass'];raw=a['adjoints'][:,1];ratio=np.divide(raw,mass,out=np.zeros_like(raw),where=mass>.1);b=int(np.ceil(.005*len(mass)));rawid=np.argsort(raw)[-b:];ratioid=np.argsort(ratio)[-b:]
 result=dict(status='VALID',camera=key,camera_sha256=c['camera_sha256'],N=len(mass),all_N=True,topK=False,unknown_truncated_mass=0,positive_rim_ids=int((raw>0).sum()),positive_visible_ids=int((mass>0).sum()),rim_mass=float(raw.sum()),visible_mass=float(mass.sum()),raw_0_5pct_captured_mass=float(raw[rawid].sum()/max(raw.sum(),1e-12)),relative_0_5pct_captured_mass=float(raw[ratioid].sum()/max(raw.sum(),1e-12)),budget_semantics='diagnostic only, not selection rule; raw here is alphaT rim participation, not old D',seconds=time.time()-t)
 seal(unit,[path,rp],result);seal(n+'_rgb_'+key,[rp],dict(status='VALID_CPU_CALIBRATED_RENDER',camera_sha256=c['camera_sha256']));print('EXTRACT',n,key,result['positive_rim_ids'],round(time.time()-t,2),flush=True)
def extract_scene(n):
 for k in scene(n)['roles']['construction']:extract_view(n,k)
def fusion_arm(n,arm):
 unit=n+'_fusion_'+arm
 if rt.resume(unit):return
 s=scene(n);views=s['roles']['construction'] if arm=='multi24' else s['roles']['construction'][:2]
 for k in views:
  if not rt.resume(n+'_extract_'+k):raise RuntimeError('unsealed source '+k)
 rows=[np.load(source_path(n,k)) for k in views];mass=np.array([a['visible_mass'] for a in rows]);rim=np.array([a['rim_wide'] for a in rows]);stats=fuse(mass,rim,views);ids,provenance=select_support(model(n),stats)
 path=rt.ART/'fusion'/n/(arm+'.npz');rt.npz(path,**stats,selected_ids=ids,views=np.asarray(views),mass=mass,raw_participation=rim,**{'hysteresis_'+k:v for k,v in provenance.items()})
 xyz=model(n)['xyz'][ids];ply=rt.ART/'fusion'/n/(arm+'_kernel_support.ply');write_support(ply,ids,model(n),stats)
 result=dict(status='VALID',arm=arm,sources=views,selected_count=len(ids),high_count=int(stats['high'].sum()),weak_count=int(stats['weak'].sum()),selected_single_source=int((stats['distinct_views'][ids]==1).sum()),selected_multi_source=int((stats['distinct_views'][ids]>=2).sum()),source_captured_mass=[float(r[ids].sum()/max(r.sum(),1e-12)) for r in rim],original_N=len(stats['score']))
 seal(unit,[path,ply],result);print('FUSION',n,arm,result['selected_count'],flush=True)
def write_support(path,ids,m,stats):
 from plyfile import PlyData,PlyElement
 a=np.empty(len(ids),dtype=[('x','f4'),('y','f4'),('z','f4'),('original_id','i4'),('score','f4'),('distinct_views','u1')])
 for j,k in enumerate(['x','y','z']):a[k]=m['xyz'][ids,j]
 a['original_id']=ids;a['score']=stats['score'][ids];a['distinct_views']=stats['distinct_views'][ids];PlyData([PlyElement.describe(a,'vertex')],text=False).write(str(rt.scoped(path)))
def build_arm(n,arm,width):
 token=str(width).replace('.','p');unit=n+'_region_'+arm+'_'+token
 path=rt.ART/'regions'/n/(arm+'_'+token+'.npz')
 if rt.resume(unit):return path
 if not rt.resume(n+'_fusion_'+arm):raise RuntimeError('fusion prerequisite not sealed')
 s=scene(n);a=dict(np.load(rt.ART/'fusion'/n/(arm+'.npz')));views=a['views'].tolist();cams=[s['cameras'][k] for k in views];es=[evidence(np.load(raw_path(n,k))['alpha']) for k in views];rt.guard(unit);t=time.time()
 r=build_region(model(n),a['selected_ids'],a,width,cams,es);rt.npz(path,**r)
 result=dict(status='VALID',arm=arm,width_voxels=width,world_width_floor=float(r['width_world_floor']),vertices=len(r['vertices']),triangles=len(r['faces']),components_6neighbor=int(r['component_count']),occupied_voxels=int(r['occupied_voxels']),raw_voxels=int(r['raw_voxels']),fill_count=len(r['fill_grid_indices']),fill_rejected=int(r['fill_rejected'].sum()),construction_veto_count=len(r['rejected_grid_indices']),merge_candidates=len(r['merge_ids']),vertex_displacement_p95=float(np.quantile(r['vertex_displacement'],.95)),original_mahalanobis_p95=float(np.quantile(r['vertex_original_mahalanobis'],.95)),seconds=time.time()-t,provenance='overlap/influence witness graph plus post-carve interfaces; candidate merges before carve are not all surviving topology; fill CSR gives actual local raw-owner witnesses')
 seal(unit,[path],result);print('REGION',n,arm,width,result['triangles'],round(time.time()-t,2),flush=True);return path
def old_graph(n):return dict(np.load(Path('/home/u00134/3dgs_line/gaer_kernel_space_lines_v01/artifacts/gaer_kernel_space_lines_v01/assets')/n/'FULL_GRAPH.npz'))
def dev_scene(n):
 unit=n+'_develop'
 if rt.resume(unit):return
 s=scene(n);dev=[camera_for(s,k,'develop') for k in s['roles']['dev']];es=[evidence(base_render(n,c)['alpha']) for c in dev];candidates=[]
 for w in [.4,.8,1.2]:
  path=build_arm(n,'multi24',w);a=np.load(path);renders=[render_mesh(a['vertices'],a['faces'],c) for c in dev];ms=[measure(r['mask'],e) for r,e in zip(renders,es)];val=float(np.mean([objective(m) for m in ms]));candidates.append(dict(width=w,path=str(path.relative_to(rt.ROOT)),objective=val,metrics=ms))
  make_panel([[(c['key']+' DEV width='+str(w),r['rgb']) for c,r in zip(dev,renders)]],rt.ART/'media'/n/'dev'/('width_'+str(w)+'.png'),tile_size=800)
 best=max(candidates,key=lambda x:(x['objective'],-x['width']));target=float(np.mean([m['ink_pixels'] for m in best['metrics']]));g=old_graph(n);lo=float(g['radius']);diagonal=float(np.linalg.norm(np.ptp(np.load(rt.ROOT/best['path'])['vertices'],axis=0)));hi=.025*diagonal;trials=[]
 for radius in [lo,hi]:
  v,f=tube_mesh(g['xyz'],g['A'],radius);ms=[measure(render_mesh(v,f,c)['mask'],e) for c,e in zip(dev,es)];trials.append(dict(radius=radius,ink=float(np.mean([m['ink_pixels'] for m in ms])),metrics=ms))
 for _ in range(8):
  radius=(lo+hi)/2;v,f=tube_mesh(g['xyz'],g['A'],radius);ms=[measure(render_mesh(v,f,c)['mask'],e) for c,e in zip(dev,es)];ink=float(np.mean([m['ink_pixels'] for m in ms]));trials.append(dict(radius=radius,ink=ink,metrics=ms))
  if ink<target:lo=radius
  else:hi=radius
 matched=min(trials,key=lambda x:abs(x['ink']-target));two=build_arm(n,'two_source',best['width'])
 result=dict(status='SELECTED_DEV_ONLY',candidates=candidates,chosen=best,widened=matched,widened_trials=trials,ink_match_relative_error=abs(matched['ink']-target)/max(target,1),two_source_path=str(two.relative_to(rt.ROOT)),reserved_opened=False)
 seal(unit,[rt.ROOT/best['path'],two],result);print('DEVELOP',n,best['width'],result['ink_match_relative_error'],flush=True)
def seal_scene(n):
 unit=n+'_asset'
 if rt.resume(unit):return
 if not rt.resume(n+'_develop'):raise RuntimeError('DEV selection not sealed')
 selection=json.loads((rt.ART/'results'/(n+'_develop.json')).read_text());g=old_graph(n);assets={};paths=[];records={}
 for arm in ['thin','widened','two_source','multi24']:
  if arm in ['thin','widened']:v,f=tube_mesh(g['xyz'],g['A'],float(g['radius']) if arm=='thin' else selection['widened']['radius'])
  else:
   path=selection['chosen']['path'] if arm=='multi24' else selection['two_source_path'];a=np.load(rt.ROOT/path);v=a['vertices'];f=a['faces']
  ex=export_mesh(rt.ART/'assets'/n/arm,v,f,name='outer');paths.extend(Path(p) for p in ex.values());assets[arm]=dict(vertices=v,faces=f);records[arm]=dict(paths={k:str(Path(p).relative_to(rt.ROOT)) for k,p in ex.items()},geometry_sha256=rt.digest(dict(vertices_sha256=__import__('hashlib').sha256(v.tobytes()).hexdigest(),faces_sha256=__import__('hashlib').sha256(f.tobytes()).hexdigest())),glb_sha256=rt.sha(ex['glb']),vertices=len(v),triangles=len(f),region_provenance=path if arm in ['two_source','multi24'] else None)
 viewer=rt.ART/'assets'/n/'viewer_3d.html';write_viewer(viewer,assets);paths.append(viewer)
 result=dict(status='SEALED_FIXED_ASSET',arms=records,chosen_width=selection['chosen']['width'],visibility='asset self-zbuffer only / x-ray relative original GS',internal_secondary='NOT_RUN; alpha-hole boundaries part of primary; no texture lines',model_sha256=scene(n)['model_sha256'],construction=scene(n)['roles']['construction'],dev=scene(n)['roles']['dev'],reserved_unopened=True)
 seal(unit,paths,result);print('ASSET_SEALED',n,flush=True)
def assets(n):
 if not rt.resume(n+'_asset'):raise RuntimeError('asset not sealed')
 rec=json.loads((rt.ART/'results'/(n+'_asset.json')).read_text());return rec,{k:dict(np.load(rt.ROOT/a['paths']['npz'])) for k,a in rec['arms'].items()}
def evaluate_view(n,c,role):
 unit=n+'_eval_'+c['key'];folder=rt.ART/'media'/n/role/c['key']
 if rt.resume(unit):return json.loads((rt.ART/'results'/(unit+'.json')).read_text())
 rec,meshes=assets(n);raw=base_render(n,c);e=evidence(raw['alpha']);rgb=np.clip(raw['rgb']*255,0,255).astype(np.uint8);paths=[];row=[('RGB SH3 / '+role+' '+c['key'],rgb)];results={}
 p=preprocess(model(n),c);features=np.zeros((len(model(n)['xyz']),2),np.float32)
 for j,arm in enumerate(['two_source','multi24']):a=np.load(rt.ROOT/rec['arms'][arm]['region_provenance']);features[a['retained_owner_ids'],j]=1
 foot=rasterize(p,features=features)['features'];fp=1-np.clip(foot[:,:,1],0,1);fp=np.repeat(fp[:,:,None],3,2);save_image(folder/'fixed_selected_fullT_footprint.png',fp);paths.append(folder/'fixed_selected_fullT_footprint.png');row.append(('retained region owner IDs / full-T footprint',fp))
 for j,arm in enumerate(['two_source','multi24']):results[arm+'_footprint']=measure(foot[:,:,j]>.1,e)
 for arm,a in meshes.items():
  r=render_mesh(a['vertices'],a['faces'],c,color=(18,18,18));results[arm]=measure(r['mask'],e);path=folder/(arm+'_fixed_mesh.png');save_image(path,r['rgb']);paths.append(path);row.append((arm+' / fixed mesh / xray wrt GS',r['rgb']))
  if arm=='multi24':
   overlay=rgb.copy();overlay[r['mask']]=(0.25*overlay[r['mask']]+.75*np.array([20,85,235])).astype(np.uint8);save_image(folder/'overlay.png',overlay);paths.append(folder/'overlay.png');row.append(('multi24 blue overlay / all rear regions',overlay))
 save_image(folder/'RGB_SH3.png',rgb);paths.append(folder/'RGB_SH3.png');panel=folder/'comparison.png';make_panel([row],panel,tile_size=800);paths.append(panel)
 # Automatic evidence-derived crop, no part labels or manually drawn corrections.
 ys,xs=np.where(e['foreground']);box=(max(0,int(xs.min())-12),max(0,int(ys.min())-12),min(800,int(xs.max())+13),min(800,int(ys.max())+13))
 for key in ['multi24_fixed_mesh','overlay','RGB_SH3']:
  im=Image.open(folder/(key+'.png'));out=folder/(key+'_object_crop.png');im.crop(box).save(out);paths.append(out)
 from scipy import ndimage as ndi
 multi_mask=np.any(np.array(Image.open(folder/'multi24_fixed_mesh.png'))<128,axis=2)
 for kind,bad in [('missing_edge',e['boundary']&(ndi.distance_transform_edt(~multi_mask)>3)),('negative_space',multi_mask&~e['foreground'])]:
  if not bad.any():bad=e['boundary']
  score=ndi.uniform_filter(bad.astype(np.float32),size=64);cy,cx=np.unravel_index(np.argmax(score),score.shape);x0=int(np.clip(cx-64,0,672));y0=int(np.clip(cy-64,0,672));crop=(x0,y0,x0+128,y0+128)
  cr=[]
  for label,file in [('RGB','RGB_SH3.png'),('thin','thin_fixed_mesh.png'),('widened','widened_fixed_mesh.png'),('two-source','two_source_fixed_mesh.png'),('multi24','multi24_fixed_mesh.png'),('overlay','overlay.png')]:
   with Image.open(folder/file) as im:cr.append((kind+' '+label+' / 128px crop',np.array(im.crop(crop))))
  zp=folder/(kind+'_zoom.png');make_panel([cr],zp,tile_size=512);paths.append(zp)
 rt.npz(folder/'evidence_masks.npz',foreground=e['foreground'],boundary=e['boundary'],holes=e['holes'],hole_boundary=e['hole_boundary'],camera_sha256=np.asarray(c['camera_sha256']))
 result=dict(status='VALID',role=role,camera=c['key'],camera_sha256=c['camera_sha256'],geometry_sha256={k:a['geometry_sha256'] for k,a in rec['arms'].items()},metrics=results,visibility=rec['visibility'],files=[str(p.relative_to(rt.ROOT)) for p in paths])
 seal(unit,paths+[folder/'evidence_masks.npz'],result);print('EVAL',n,c['key'],round(results['multi24']['coverage3'],3),flush=True);return result
def eval_scene(n):
 assets(n);s=scene(n);rows=[];allr=[]
 for key in s['roles']['reserved']:
  c=camera_for(s,key,'eval',True);r=evaluate_view(n,c,'reserved');allr.append(r)
  folder=rt.ART/'media'/n/'reserved'/key;rows.append([(key+' / reserved / '+label,np.array(Image.open(folder/file))) for label,file in [('RGB','RGB_SH3.png'),('full-T support','fixed_selected_fullT_footprint.png'),('thin','thin_fixed_mesh.png'),('widened','widened_fixed_mesh.png'),('two-source','two_source_fixed_mesh.png'),('multi24','multi24_fixed_mesh.png'),('overlay','overlay.png')]])
 panel=rt.ART/'media'/n/'reserved_eight_FULL.png';make_panel(rows,panel,tile_size=800);preview=rt.ART/'media'/n/'reserved_eight_preview.jpg';Image.open(panel).resize((2240,8*342)).save(preview,quality=92)
 seal(n+'_reserved_complete',[panel,preview],dict(status='EVALUATED',views=[r['camera'] for r in allr],metrics={r['camera']:r['metrics'] for r in allr}))
def arc_scene(n):
 unit=n+'_arc_complete'
 if rt.resume(unit):return
 rec,mesh=assets(n);a=mesh['multi24'];frames=[];records=[];folder=rt.ART/'media'/n/'arc'
 for c in scene(n)['arc']:
  frameunit=n+'_arc_'+c['key'];path=folder/(c['key']+'.png')
  if not rt.resume(frameunit):
   raw=base_render(n,c);rgb=np.clip(raw['rgb']*255,0,255).astype(np.uint8);r=render_mesh(a['vertices'],a['faces'],c,color=(18,18,18));overlay=rgb.copy();overlay[r['mask']]=(overlay[r['mask']]*.25+np.array([20,85,235])*.75).astype(np.uint8);make_panel([[('RGB SH3 / '+c['key'],rgb),('fixed multi24 mesh / xray relative GS',r['rgb']),('overlay / no hidden-line cleanup',overlay)]],path,tile_size=800)
   seal(frameunit,[path],dict(status='VALID',camera_sha256=c['camera_sha256'],geometry_sha256=rec['arms']['multi24']['geometry_sha256'],metrics=measure(r['mask'],evidence(raw['alpha']))))
  fr=json.loads((rt.ART/'results'/(frameunit+'.json')).read_text());frames.append(path);records.append(dict(frame=len(frames)-1,camera=c,camera_sha256=c['camera_sha256'],geometry_sha256=rec['arms']['multi24']['geometry_sha256'],metrics=fr['metrics']))
 video=folder/'fixed_region_33.mp4';manifest=encode_video(frames,video,fps=12,expected_frames=33,frame_records=records);strip=folder/'ALL_33_FRAMES.jpg';make_strip(frames,strip,columns=3,thumb_width=720);seal(unit,[video,video.with_suffix('.manifest.json'),strip],dict(status='VALID_33_COMPLETE',frames=33,geometry_sha256=rec['arms']['multi24']['geometry_sha256'],video_manifest=manifest));print('ARC_COMPLETE',n,flush=True)
