from pathlib import Path
import hashlib,json,tarfile,shutil,datetime,numpy as np
T=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/balanced_multiview_v02');OLD=T.parent/'spatial_rgb_gaussian_demo_v01'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def js(p,o):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(o,indent=2,ensure_ascii=False));tmp.replace(p)
assert shutil.disk_usage(T).free>10*1024**3 and shutil.disk_usage('/').free>1024**3
E=T/'evidence';E.mkdir(exist_ok=True);shutil.copy2(OLD/'evidence/boundary.py',E/'boundary.py');assert sha(E/'boundary.py')=='11bbb41a762f252d9eeb4ea3f0a8399ed026139d9490bb8cf161bc815e05dd30'
rec=[];selection={}
for scene,folder in [('scan24','scan24'),('scan65','scan65_eigen_fallback_v01'),('scan63','scan63_eigen_fallback_v01')]:
 arc=T.parent/'depth_only_v01/deliveries'/folder/(scene+'_official_15k30k_raw_depth.tar');a={'scene':scene,'archive':str(arc),'archive_bytes':arc.stat().st_size,'archive_sha256':sha(arc),'files':[]}
 with tarfile.open(arc) as tar:
  manifest=json.load(tar.extractfile('DEPTH_ONLY_MANIFEST.json'));js(E/(scene+'_DELIVERY_MANIFEST.json'),manifest)
  names=['cameras/30000.json','metadata/CAMERA_AND_DEPTH_CONVENTIONS.json','metadata/PROVENANCE.json']+[f'checkpoints/30000/{v:04d}.npz' for v in range(49)]
  for name in names:
   m=tar.getmember(name);assert m.isfile() and not m.issym() and not m.islnk() and '..' not in Path(name).parts and not Path(name).is_absolute()
   if name.startswith('checkpoints'):dest=E/(scene+'_'+Path(name).name)
   elif name.startswith('cameras'):dest=E/(scene+'_cameras_30000.json')
   else:dest=E/(scene+'_'+Path(name).name)
   expected=manifest['files'][name]['sha256']
   if not dest.exists():
    tmp=dest.with_suffix('.partial')
    with tar.extractfile(m) as src,tmp.open('wb') as out:shutil.copyfileobj(src,out)
    assert sha(tmp)==expected;tmp.replace(dest)
   assert sha(dest)==expected
   a['files'].append({'archive_member':name,'path':str(dest),'sha256':expected,'bytes':dest.stat().st_size,'source_path':manifest['files'][name]['source_path']})
  cams=json.loads((E/(scene+'_cameras_30000.json')).read_text());assert len(cams)==49
  # Pose-only deterministic farthest-point coverage: position normalized by median pair separation + rotation geodesic/pi.
  ids=[c['view'] for c in cams];Es=np.array([c['extrinsic'] for c in cams]);R=Es[:,:3,:3];C=np.array([-np.linalg.solve(e[:3,:3],e[:3,3]) for e in Es]);D=np.linalg.norm(C[:,None]-C[None,:],axis=-1);scale=float(np.median(D[D>0]));rel=R[:,None]@R[None].transpose(0,1,3,2);theta=np.arccos(np.clip((np.trace(rel,axis1=2,axis2=3)-1)/2,-1,1));dist=(D/scale)**2+(theta/np.pi)**2
  order=[ids.index(v) for v in ['0000','0024','0048']];pool=[i for i,v in enumerate(ids) if v not in ['0012','0036'] and i not in order]
  while pool:
   nxt=max(pool,key=lambda i:(float(dist[i,order].min()),-int(ids[i])));order.append(nxt);pool.remove(nxt)
  sequence=[ids[i] for i in order];selection[scene]={'strategy':'greedy pose FPS starting 0000,0024,0048; squared center-distance/median + squared rotation-geodesic/pi; ties smaller view ID','translation_normalization':scale,'camera_sha256':sha(E/(scene+'_cameras_30000.json')),'sequence':sequence,'tiers':{str(n):sequence[:n] for n in [3,12,24,47]},'excluded_holdouts':['0012','0036']}
 rec.append(a);js(T/'PREPARATION_STATUS.json',{'archives_completed':len(rec),'npz_verified':len(rec)*49});print(scene,'verified49',selection[scene]['tiers']['12'],flush=True)
js(T/'SOURCE_MANIFEST.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archives':rec,'boundary_sha256':sha(E/'boundary.py'),'old_seal_hashes':{n:sha(OLD/n) for n in ['ASSET_FREEZE.json','BALANCED_ASSET_FREEZE.json','SOURCE_FREEZE.json']}});js(T/'VIEW_SELECTION.json',selection)
