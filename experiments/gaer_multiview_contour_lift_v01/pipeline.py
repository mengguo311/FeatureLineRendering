import runtime as rt
import json,time,traceback,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
import cv2
from scipy.spatial import cKDTree
from scipy import ndimage as ndi
from PIL import Image
import cpu_native as cpu
from core import *
import mesh_tools as mesh
from media_tools import save_image,make_panel,make_strip,encode_video
from metrics import measure
OLD=Path('/home/u00134/3dgs_line/gaer_multiview_contour_regions_v01');OLDART=OLD/'artifacts/gaer_multiview_contour_regions_v01'
_models={}
def frozen():return json.loads((rt.ART/'INPUT_FREEZE.json').read_text())
def scene(n):return frozen()['scenes'][n]
def model(n):
 if n not in _models:_models[n]=cpu.load_model_cpu(scene(n))
 return _models[n]
def seal(unit,files,result):rt.seal(unit,list(files)+[rt.ART/'INPUT_FREEZE.json',rt.ART/'PROTOCOL.json',rt.ART/'FUSION_FREEZE.json'],result)
def camera(n,key):
 s=scene(n)
 return s['cameras'][key] if key in s['cameras'] else next(c for c in s['arc'] if c['key']==key)
def cache(n,c,role):
 s=scene(n);key=c['key']
 if role in ('reserved','arc') and not rt.resume(n+'_asset'):raise RuntimeError('heldout image access before asset seal')
 assert key in (s['roles'].get(role,[]) if role!='arc' else [a['key'] for a in s['arc']])
 x=dict(c);h=x.pop('camera_sha256');assert h==rt.digest(x)
 unit=n+'_rgb_'+key;sp=OLDART/'seals'/(unit+'.json');sr=json.loads(sp.read_text());rp=OLDART/'results'/(unit+'.json');raw=OLD/'out/gaer_multiview_contour_regions_v01/renders'/n/(key+'.npz')
 for p in (rp,raw,OLDART/'INPUT_FREEZE.json'):
  assert rt.sha(p)==sr['files'][str(p.relative_to(OLD))],str(p)
 result=json.loads(rp.read_text());assert result['camera_sha256']==h
 if 'model_sha256' in result:assert result['model_sha256']==s['model_sha256']
 audit=dict(scene=n,camera=key,role=role,cache=str(raw),cache_sha256=rt.sha(raw),camera_sha256=h,model_sha256=s['model_sha256'],old_input_sha256=rt.sha(OLDART/'INPUT_FREEZE.json'),old_seal_sha256=rt.sha(sp),actual_file_path=c.get('frame_file'),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
 rt.atomic_json(rt.ART/'cache_audit'/n/(key+'.json'),audit)
 return dict(np.load(raw))
def source_path(n,key):return rt.ART/'sources'/n/(key+'.npz')
def extract(n,key):
 unit=n+'_source_'+key
 if rt.resume(unit):return
 rt.guard(unit);t=time.time();s=scene(n);c=camera(n,key);r=cache(n,c,'construction');cs=contours(r['alpha']);p=cpu.preprocess(model(n),c)
 pix=np.concatenate([a['pixels'] for a in cs]);query=cpu.query_contributors(p,pix);summ=[]
 for i in range(len(pix)):
  a,b=query['offsets'][i:i+2];summ.append(depth_summary(p['depth'][query['ids'][a:b]],query['weights'][a:b]))
 z=np.array([d['median'] for d in summ]);qs=np.array([[d[k] for k in ['q10','median','q90','mean','mass']] for d in summ]);xyz=lift(pix,z,c)
 wp=z/np.sqrt(np.linalg.det(np.asarray(c['K'])[:2,:2]));diag=np.linalg.norm(np.quantile(model(n)['xyz'],.99,axis=0)-np.quantile(model(n)['xyz'],.01,axis=0))
 chain=[];loc=[];kind=[];tangent=[];edges=[];rejected=[];offset=0
 for j,a in enumerate(cs):
  N=len(a['pixels']);ids=np.arange(offset,offset+N);chain.extend([j]*N);loc.extend(range(N));kind.extend([int(a['kind']=='hole')]*N)
  tangent.extend(xyz[np.roll(ids,-3)]-xyz[np.roll(ids,3)])
  for u,v in zip(ids,np.roll(ids,-1)):
   length=np.linalg.norm(xyz[u]-xyz[v]);limit=min(6*max(wp[u],wp[v]),.025*diag)
   if np.isfinite(length) and length>1e-10 and length<=limit:edges.append([u,v])
   else:rejected.append([int(u),int(v),float(length) if np.isfinite(length) else None,'depth_jump_or_no_contribution'])
  offset+=N
 tangent=np.array(tangent);tangent/=np.maximum(np.linalg.norm(tangent,axis=1)[:,None],1e-20)
 aa=np.array([d['mass'] for d in summ]);diff=np.abs(aa-r['alpha'][pix[:,1],pix[:,0]])
 assert np.max(diff)<2e-5,(n,key,'accepted sum mismatch',diff.max())
 uv,zz=project(xyz,c);err=np.linalg.norm(uv-pix,axis=1);assert np.nanmax(err)<1e-8
 path=source_path(n,key)
 rt.npz(path,pixels=pix,xyz=xyz.astype(np.float32),edges=np.array(edges,np.int32).reshape(-1,2),tangent=tangent.astype(np.float32),chain=np.array(chain,np.int32),local=np.array(loc,np.int32),kind=np.array(kind,np.int8),depth_summary=qs,world_pixel=wp,accepted_offsets=query['offsets'],accepted_ids=query['ids'],accepted_weights=query['weights'],accepted_center_z=p['depth'][query['ids']],camera_sha256=np.asarray(c['camera_sha256']),depth_definition=np.asarray('conditional all accepted alphaT weighted median center camera-z proxy; no smoothing'))
 jp=path.with_suffix('.json');rt.atomic_json(jp,dict(camera=c,chains=[{k:v for k,v in a.items() if k!='pixels'} for a in cs],query_schema='CSR accepted_offsets -> original accepted_ids / accepted_weights / accepted_center_z; all accepted, no K truncation',depth_columns=['q10','median','q90','mean','mass'],rejected_edges=rejected,source_reprojection_is_not_depth_accuracy=True))
 ref=np.full(r['rgb'].shape,255,np.uint8)
 for a in cs:cv2.polylines(ref,[a['pixels']],True,(180,50,0) if a['kind']=='hole' else (0,0,0),1,cv2.LINE_8)
 media=rt.ART/'media'/n/'construction';save_image(media/(key+'_reference.png'),ref);save_image(media/(key+'_RGB.png'),r['rgb'])
 result=dict(status='VALID_PROXY',camera=key,points=len(pix),edges=len(edges),outer_chains=sum(a['kind']=='outer' for a in cs),hole_chains=sum(a['kind']=='hole' for a in cs),rejected_edges=len(rejected),accepted_entries=len(query['ids']),accepted_mass_vs_cached_alpha_max=float(diff.max()),source_reprojection_max_px=float(np.nanmax(err)),uncertainty_q90_q10_quantiles=np.quantile(qs[:,2]-qs[:,0],[0,.5,.95,1]).tolist(),seconds=time.time()-t)
 seal(unit,[path,jp,media/(key+'_reference.png'),media/(key+'_RGB.png')],result);print('SOURCE',n,key,result['points'],result['edges'],round(time.time()-t,2),flush=True)
def collect(n):
 keys=scene(n)['roles']['construction'];src=[dict(np.load(source_path(n,k))) for k in keys];off=np.r_[0,np.cumsum([len(a['xyz']) for a in src])];data={k:np.concatenate([a[k] for a in src]) for k in ('xyz','pixels','tangent','chain','local','kind','world_pixel')};data['view']=np.concatenate([np.full(len(a['xyz']),j,np.int32) for j,a in enumerate(src)]);data['edges']=np.concatenate([a['edges']+off[j] for j,a in enumerate(src)]);return keys,src,off,data

def build_fusion(n):
 unit=n+'_fusion'
 if rt.resume(unit):return
 rt.guard(unit);t=time.time();keys,src,off,d=collect(n);xyz=d['xyz'];cams=[camera(n,k) for k in keys];pair_records=[];approved=[];reject=Counter();trees=[cKDTree(a['xyz']) for a in src]
 for a in range(len(src)):
  for b in range(a+1,len(src)):
   A=src[a];B=src[b];dist,idx=trees[b].query(A['xyz']);_,back=trees[a].query(B['xyz']);limit=2.5*np.maximum(A['world_pixel'],B['world_pixel'][idx]);near=np.flatnonzero((dist<=limit)&(back[idx]==np.arange(len(idx))))
   provisional=[]
   for i in near:
    j=int(idx[i]);rec=dict(a=int(off[a]+i),b=int(off[b]+j),distance=float(dist[i]));reason=''
    if A['kind'][i]!=B['kind'][j]:reason='boundary_class'
    elif abs(A['tangent'][i]@B['tangent'][j])<.92:reason='tangent'
    else:
     ai,aj=A['accepted_offsets'][i:i+2];bi,bj=B['accepted_offsets'][j:j+2]
     overlap=support_overlap(A['accepted_ids'][ai:aj],A['accepted_weights'][ai:aj],B['accepted_ids'][bi:bj],B['accepted_weights'][bi:bj]);rec['overlap']=overlap
     if overlap<.1:reason='no_shared_support_rolling_or_distinct'
     else:
      epi=epipolar_error(A['pixels'][i],cams[a],B['pixels'][j],cams[b]);rec['epipolar_px']=float(epi)
      if epi>1.:reason='epipolar'
      else:
       q,status=triangulate(A['pixels'][i],cams[a],B['pixels'][j],cams[b]);reason='' if status=='accepted' else status
       if not reason:
        er=max(np.linalg.norm(project([q],cams[a])[0][0]-A['pixels'][i]),np.linalg.norm(project([q],cams[b])[0][0]-B['pixels'][j]));disp=max(np.linalg.norm(q-A['xyz'][i]),np.linalg.norm(q-B['xyz'][j]));rec.update(reprojection=float(er),displacement=float(disp),triangulated=q.tolist())
        if er>2:reason='triangulation_reprojection'
        elif disp>limit[i]:reason='proxy_displacement'
    rec['reason']=reason or 'provisional';pair_records.append(rec)
    if not reason:provisional.append((i,j,len(pair_records)-1))
    else:reject[reason]+=1
   # At least three nearby order-consistent source samples in same pair of chains.
   for i,j,k in provisional:
    neighbors=[(ii,jj) for ii,jj,kk in provisional if A['chain'][ii]==A['chain'][i] and B['chain'][jj]==B['chain'][j] and abs(int(A['local'][ii])-int(A['local'][i]))<=4 and abs(int(B['local'][jj])-int(B['local'][j]))<=4]
    forward=sum((int(A['local'][ii])-int(A['local'][i]))*(int(B['local'][jj])-int(B['local'][j]))>=0 for ii,jj in neighbors)
    reverse=sum((int(A['local'][ii])-int(A['local'][i]))*(int(B['local'][jj])-int(B['local'][j]))<=0 for ii,jj in neighbors)
    if max(forward,reverse)>=3:pair_records[k]['reason']='track_accepted';approved.append(k)
    else:pair_records[k]['reason']='short_or_inconsistent_track';reject['short_or_inconsistent_track']+=1
  print('PAIR_ROW',n,a,'pairs',len(pair_records),'accepted',len(approved),flush=True)
 # Constrained union: refit and recheck every source in merged cluster.
 parent=np.arange(len(xyz));members={i:[i] for i in range(len(xyz))};centers={i:xyz[i].astype(float) for i in range(len(xyz))}
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=int(parent[i])
  return i
 accepted_merges=[]
 for k in sorted(approved,key=lambda k:(pair_records[k]['distance'],pair_records[k]['a'],pair_records[k]['b'])):
  rec=pair_records[k];a=root(rec['a']);b=root(rec['b'])
  if a==b:rec['cluster_reason']='already_same';continue
  ids=members[a]+members[b];views=d['view'][ids];reason=''
  if len(set(views.tolist()))!=len(ids):reason='same_camera_collision'
  else:
   origins=[];directions=[]
   for i in ids:
    o,r=rays([d['pixels'][i]],cams[d['view'][i]]);origins.append(o[0]);directions.append(r[0])
   R=np.asarray(directions);O=np.asarray(origins);P=np.eye(3)[None]-R[:,:,None]*R[:,None,:];M=P.sum(0)
   if np.linalg.cond(M)>1e5:reason='cluster_condition'
   else:
    q=np.linalg.solve(M,np.einsum('nij,nj->i',P,O));er=[];dis=[];depths=[]
    for i in ids:
     uv,z=project([q],cams[d['view'][i]]);er.append(np.linalg.norm(uv[0]-d['pixels'][i]));dis.append(np.linalg.norm(q-xyz[i])/d['world_pixel'][i]);depths.append(z[0])
    tang=abs(d['tangent'][ids]@d['tangent'][ids].T)
    if min(depths)<=0:reason='cluster_behind'
    elif max(er)>2:reason='cluster_all_source_reprojection'
    elif max(dis)>2.5:reason='cluster_all_source_displacement'
    elif tang.min()<.92:reason='cluster_all_tangent'
    else:rec.update(cluster_max_reprojection=float(max(er)),cluster_max_displacement_wpp=float(max(dis)))
  rec['cluster_reason']=reason or 'merged'
  if reason:reject[reason]+=1;continue
  parent[b]=a;members[a]=ids;centers[a]=q;del members[b];del centers[b];accepted_merges.append(k)
 roots=sorted(members);clusters=[members[k] for k in roots];center=np.array([centers[k] for k in roots]);f=fuse_tracks(xyz,d['edges'],clusters,center,2,d['view'])
 disp=[];errors=[]
 for q,ids in zip(f['xyz'],f['node_sources']):
  for i in ids:
   errors.append(float(np.linalg.norm(project([q],cams[d['view'][i]])[0][0]-d['pixels'][i])));disp.append(float(np.linalg.norm(q-xyz[i])))
 assert max(errors,default=0)<2.0001
 path=rt.ART/'fusion'/n/'fused.npz';rt.npz(path,xyz=f['xyz'],edges=f['edges'],raw_to_cluster=f['cluster_map'],used_clusters=f['used_clusters'],rejected_raw_edges=f['rejected_edges'])
 jp=path.with_suffix('.json');rt.atomic_json(jp,dict(node_sources=f['node_sources'],edge_sources=f['edge_sources'],raw_source_offsets=off.tolist(),source_cameras=keys,pair_records=pair_records,all_source_displacements=disp,all_source_reprojection_px=errors,unmerged_source_nodes=[int(i) for c in clusters if len(c)==1 for i in c],rejection_counts=dict(reject)))
 st=dict(status='FUSED_CANDIDATE',raw_nodes=len(xyz),raw_edges=len(d['edges']),near_reciprocal_pairs=len(pair_records),track_accepted_pairs=len(approved),cluster_merges=len(accepted_merges),multi_source_clusters=sum(len(c)>1 for c in clusters),fused_nodes=len(f['xyz']),fused_edges=len(f['edges']),duplicate_edges_removed=sum(len(g)-1 for g in f['edge_sources']),rejected_raw_edges=len(f['rejected_edges']),displacement_p95=float(np.quantile(disp,.95)) if disp else 0.,reprojection_max=max(errors,default=0.),rejection_counts=dict(reject),seconds=time.time()-t)
 seal(unit,[path,jp],st);print('FUSION',n,json.dumps(st),flush=True)

def graph_paths(edges):
 adj={};used=set();paths=[]
 for j,(a,b) in enumerate(edges):adj.setdefault(int(a),[]).append((int(b),j));adj.setdefault(int(b),[]).append((int(a),j))
 starts=sorted(adj,key=lambda a:(len(adj[a])==2,a))
 for s in starts:
  for nxt,eid in adj[s]:
   if eid in used:continue
   path=[s];cur=s
   while eid not in used:
    used.add(eid);path.append(nxt);cur=nxt
    if len(adj[cur])!=2:break
    avail=[(v,e) for v,e in adj[cur] if e not in used]
    if not avail:break
    nxt,eid=avail[0]
   paths.append(path)
 return paths

def export_graph(folder,xyz,edges,radius,node_sources,edge_sources):
 folder=rt.scoped(folder/'x').parent;xyz=np.asarray(xyz,np.float32);edges=np.asarray(edges,np.int32).reshape(-1,2);paths=graph_paths(edges);v,f=mesh.tube_mesh(xyz,edges,radius)
 files=mesh.export_mesh(folder,v,f,'tubes');rt.npz(folder/'centerlines.npz',xyz=xyz,edges=edges,radius=np.asarray(radius))
 with (folder/'centerlines.obj').open('w') as o:
  o.write('# Fixed world centers; Z up; paths immutable\n')
  for p in xyz:o.write('v %.9g %.9g %.9g\n'%tuple(p))
  for j,path in enumerate(paths):o.write('g path_%06d\nl '%j+' '.join(str(i+1) for i in path)+'\n')
 rt.atomic_json(folder/'CENTERLINES.json',dict(xyz=xyz.tolist(),paths=paths,edges=edges.tolist(),world_radius=radius,geometry_sha256=geometry_hash(xyz,edges,radius),node_sources=node_sources,edge_sources=edge_sources,depth_is_proxy=True,visibility='tube self-zbuffer; xray relative to original object'))
 from plyfile import PlyData,PlyElement
 a=np.empty(len(xyz),dtype=[('x','f4'),('y','f4'),('z','f4'),('source_count','i4')])
 for j,k in enumerate('xyz'):a[k]=xyz[:,j]
 a['source_count']=[len(x) for x in node_sources];PlyData([PlyElement.describe(a,'vertex')],text=False).write(str(folder/'control_points.ply'))
 return dict(vertices=v,faces=f,xyz=xyz,edges=edges,geometry_sha256=geometry_hash(xyz,edges,radius),paths=len(paths),short_paths=sum(len(p)<=3 for p in paths),files=[str(p) for p in folder.iterdir() if p.is_file()])

def build_asset(n):
 unit=n+'_asset'
 if rt.resume(unit):return
 rt.guard(unit);keys,src,off,d=collect(n);s=scene(n);f=dict(np.load(rt.ART/'fusion'/n/'fused.npz'));pr=json.loads((rt.ART/'fusion'/n/'fused.json').read_text());wpp=float(np.median(d['world_pixel']));dev=[]
 # Width selection observes only DEV camera projections. DEV images used later for visual diagnostics.
 for mul in [.75,1.,1.25]:
  diam=[]
  for key in s['roles']['dev']:
   c=camera(n,key);z=project(d['xyz'],c)[1];diam.extend((2*mul*wpp*np.sqrt(np.linalg.det(np.asarray(c['K'])[:2,:2]))/z[z>0]).tolist())
  q=np.quantile(diam,[.05,.5,.95,.99,1]);dev.append(dict(multiplier=mul,radius=mul*wpp,diameter_quantiles=q.tolist(),score=abs(q[1]-2),valid=bool(q[2]<=6)))
 best=min([a for a in dev if a['valid']],key=lambda x:(x['score'],x['radius']));radius=best['radius'];folder=rt.ART/'assets'/n;arms={};files=[];idx=keys.index('r_33');single=src[idx]
 arms['single']=export_graph(folder/'single',single['xyz'],single['edges'],radius,[[int(off[idx]+i)] for i in range(len(single['xyz']))],[[i] for i in range(len(single['edges']))])
 arms['rawunion']=export_graph(folder/'rawunion',d['xyz'],d['edges'],radius,[[i] for i in range(len(d['xyz']))],[[i] for i in range(len(d['edges']))])
 arms['fused']=export_graph(folder/'fused',f['xyz'],f['edges'],radius,pr['node_sources'],pr['edge_sources'])
 for i,(k,a) in enumerate(zip(keys,src)):
  g=export_graph(folder/'sources'/k,a['xyz'],a['edges'],radius,[[int(off[i]+j)] for j in range(len(a['xyz']))],[[j] for j in range(len(a['edges']))]);files+=g['files']
 for a in arms.values():files+=a['files']
 mesh.write_viewer(folder/'viewer_3d.html',arms);files.append(str(folder/'viewer_3d.html'))
 used=np.unique(np.concatenate([a['accepted_ids'] for a in src]));m=model(n);from plyfile import PlyData,PlyElement
 va=np.empty(len(used),dtype=[('x','f4'),('y','f4'),('z','f4'),('original_id','i4')]);va['original_id']=used
 for j,k in enumerate('xyz'):va[k]=m['xyz'][used,j]
 kp=folder/'original_kernel_support.ply';PlyData([PlyElement.describe(va,'vertex')],text=False).write(str(kp));files.append(str(kp))
 sp=folder/'SOURCE_INDEX.json';rt.atomic_json(sp,dict(cameras=keys,global_offsets=off.tolist(),source_data=[str(source_path(n,k).relative_to(rt.ROOT)) for k in keys],kernel_support=str(kp),accepted_depth_definition='all accepted alphaT conditional median center-z proxy',bounds='no extra smoothing; max fused displacement 2.5 source-world-pixels, all source reprojection <=2px'));files.append(str(sp))
 result=dict(status='SEALED_FIXED_THIN_CURVE_CANDIDATE',world_radius=radius,wpp=wpp,width_candidates=dev,arms={k:{a:b for a,b in v.items() if a not in ('vertices','faces','xyz','edges','files')}|dict(vertices=len(v['vertices']),faces=len(v['faces']),nodes=len(v['xyz']),edges=len(v['edges'])) for k,v in arms.items()},reserved_opened=False,visibility='asset_self_zbuffer; xray_relative_to_GS',code_sha256=rt.method_hashes())
 seal(unit,[Path(p) for p in files],result);print('ASSET_SEALED',n,radius,{k:len(v['edges']) for k,v in arms.items()},flush=True)

def evidence(alpha):
 fg=alpha>=.5;holes=ndi.binary_fill_holes(fg)&~fg;boundary=fg&~ndi.binary_erosion(fg);return dict(foreground=fg,holes=holes,boundary=boundary,distance=ndi.distance_transform_edt(~boundary))
def metric(mask,e):
 m=measure(mask,e);inside=ndi.distance_transform_edt(mask);dense=inside>3;lab,num=ndi.label(dense);counts=np.bincount(lab.ravel())[1:]
 m.update(foreground_blank_fraction=float((e['foreground']&~mask).sum()/max(e['foreground'].sum(),1)),ink_core_radius_over3_pixels=int(dense.sum()),largest_dense_core_component=int(counts.max()) if len(counts) else 0,width_distance_transform_p99=float(2*np.quantile(inside[mask],.99)) if mask.any() else 0)
 return m

def load_arms(n):
 return {k:dict(np.load(rt.ART/'assets'/n/k/'tubes.npz')) for k in ('single','rawunion','fused')}
def evaluate_view(n,key,role):
 unit=n+'_'+role+'_'+key
 if rt.resume(unit):return
 assert rt.resume(n+'_asset');c=camera(n,key);r=cache(n,c,role);e=evidence(r['alpha']);folder=rt.ART/'media'/n/role/key;folder.mkdir(parents=True,exist_ok=True);rgb=np.rint(np.clip(r['rgb'],0,1)*255).astype(np.uint8);ref=np.full_like(rgb,255);ref[e['boundary']]=0
 save_image(folder/'original.png',rgb);save_image(folder/'reference2D.png',ref);rows=[('original SH3 CPU RGB | '+key,rgb),('independent alpha contour incl holes',ref)];ms={};arms=load_arms(n);sealrec=json.loads((rt.ART/'results'/(n+'_asset.json')).read_text())
 for arm,a in arms.items():
  q=mesh.render_mesh(a['vertices'],a['faces'],c,color=(0,0,0));overlay=rgb.copy();overlay[q['mask']]=[210,30,30];save_image(folder/(arm+'.png'),q['rgb']);save_image(folder/(arm+'_overlay.png'),overlay);rows.append((arm+' fixed tubes | xray vs GS',q['rgb']));ms[arm]=metric(q['mask'],e)
  if arm=='fused':rows.append(('fused overlay | rear lines retained',overlay))
  centers=dict(np.load(rt.ART/'assets'/n/arm/'centerlines.npz'));z=project(centers['xyz'],c)[1];diam=2*float(centers['radius'])*np.sqrt(np.linalg.det(np.asarray(c['K'])[:2,:2]))/z[z>0];ms[arm]['analytic_diameter_quantiles']=np.quantile(diam,[.05,.5,.95,.99,1]).tolist() if len(diam) else []
 panel=make_panel([rows],folder/'FULL.png',title=n+' '+role+' '+key+' | actual world-radius triangle tubes; all rear geometry retained',tile_size=800)
 Image.fromarray(panel).resize((2400,round(panel.shape[0]/2)),Image.Resampling.LANCZOS).save(folder/'preview.jpg',quality=90)
 # Deterministic edge crop: 192x192 around middle row-major reference boundary pixel; not manually chosen.
 xy=np.argwhere(e['boundary']);y,x=xy[len(xy)//2];x=int(np.clip(x-96,0,608));y=int(np.clip(y-96,0,608));zrows=[(label,img[y:y+192,x:x+192]) for label,img in rows];make_panel([zrows],folder/'edgezoom.png',tile_size=384,title=f'fixed crop x={x},y={y},192x192 nearest-scale display')
 result=dict(status='EVALUATED',role=role,camera=key,camera_sha256=c['camera_sha256'],geometry_sha256={k:v['geometry_sha256'] for k,v in sealrec['arms'].items()},metrics=ms,crop_xy=[x,y],visibility='triangle asset self-zbuffer only; xray relative to original GS')
 seal(unit,list(folder.glob('*.png'))+[folder/'preview.jpg'],result);print('EVAL',n,role,key,{a:round(m['coverage3'],3) for a,m in ms.items()},flush=True)

def evaluate_all(n):
 for role in ('dev','reserved'):
  for key in scene(n)['roles'][role]:evaluate_view(n,key,role)
 unit=n+'_reserved_panel'
 if not rt.resume(unit):
  rows=[]
  for k in scene(n)['roles']['reserved']:
   folder=rt.ART/'media'/n/'reserved'/k
   rows.append([(k+' '+v,Image.open(folder/(v+'.png')).copy()) for v in ['original','reference2D','single','rawunion','fused','fused_overlay']])
  p=rt.ART/'media'/n/'reserved_eight_FULL.png';a=make_panel(rows,p,title=n+' all 8 reserved | same sealed world tubes | xray versus GS');Image.fromarray(a).resize((1800,round(a.shape[0]*1800/a.shape[1])),Image.Resampling.LANCZOS).save(p.with_name('reserved_eight_preview.jpg'),quality=92);seal(unit,[p,p.with_name('reserved_eight_preview.jpg')],dict(status='ALL_EIGHT',rows=8))

def video(n):
 unit=n+'_video'
 if rt.resume(unit):return
 assert rt.resume(n+'_asset');arms=load_arms(n);rec=json.loads((rt.ART/'results'/(n+'_asset.json')).read_text());frames=[];records=[];folder=rt.ART/'media'/n/'arc';folder.mkdir(parents=True,exist_ok=True)
 for i,c in enumerate(scene(n)['arc']):
  key=c['key'];frameunit=n+'_arc_'+key;path=folder/(f'{i:03d}.png')
  if not rt.resume(frameunit):
   r=cache(n,c,'arc');rgb=np.rint(np.clip(r['rgb'],0,1)*255).astype(np.uint8);rows=[('original SH3 | '+key,rgb)];met={};e=evidence(r['alpha'])
   for k,a in arms.items():
    q=mesh.render_mesh(a['vertices'],a['faces'],c,color=(0,0,0));rows.append((k+' fixed tubes | xray vs GS',q['rgb']));met[k]=metric(q['mask'],e)
   make_panel([rows],path,title=n+' | same static XYZ/topology/radius | no per-frame selection',tile_size=800)
   seal(frameunit,[path],dict(camera_sha256=c['camera_sha256'],geometry_sha256={k:a['geometry_sha256'] for k,a in rec['arms'].items()},metrics=met))
  frames.append(path);records.append(dict(camera=c,camera_sha256=c['camera_sha256'],geometry_sha256={k:a['geometry_sha256'] for k,a in rec['arms'].items()}));print('FRAME',n,i,flush=True)
 mp4=folder/'three_arms_33.mp4';manifest=encode_video(frames,mp4,fps=6,expected_frames=33,frame_records=records);strip=folder/'ALL_33_FRAMES.jpg';make_strip(frames,strip,columns=3,thumb_width=1000)
 seal(unit,[mp4,mp4.with_suffix('.manifest.json'),mp4.with_suffix('.probe.txt'),strip],dict(status='FULL_DECODE_PASS',decoded_frames=manifest['decoded_frames'],geometry_sha256={k:a['geometry_sha256'] for k,a in rec['arms'].items()}))

def main():
 import argparse
 a=argparse.ArgumentParser();a.add_argument('stage',choices=['extract','fusion','asset','eval','video','build']);a.add_argument('--scene',choices=['lego','chair']);args=a.parse_args();failures=[]
 for n in [args.scene] if args.scene else ['lego','chair']:
  try:
   if args.stage in ('extract','build'):
    for key in scene(n)['roles']['construction']:extract(n,key)
   if args.stage in ('fusion','build'):build_fusion(n)
   if args.stage in ('asset','build'):build_asset(n)
   if args.stage=='eval':evaluate_all(n)
   if args.stage=='video':video(n)
  except Exception as exc:
   failures.append(dict(scene=n,stage=args.stage,error=repr(exc),traceback=traceback.format_exc()));print(traceback.format_exc(),flush=True)
  _models.clear()
 rt.atomic_json(rt.ART/'results'/('RUN_'+args.stage+'_'+str(args.scene)+'.json'),dict(failures=failures,status='FAIL' if failures else 'PASS'))
 return int(bool(failures))
if __name__=='__main__':raise SystemExit(main())
