import runtime as rt
import pipeline as pp
import mesh_tools as mesh
from core import project
import json,ast,hashlib
import numpy as np,cv2
from scipy.spatial import cKDTree

def near_duplicate(g,wpp):
 p=g['xyz'];e=g['edges'];mid=p[e].mean(1);vec=p[e[:,1]]-p[e[:,0]];ln=np.linalg.norm(vec,axis=1);t=vec/ln[:,None];tree=cKDTree(mid);dis,idx=tree.query(mid,k=min(13,len(mid)));pairs=[]
 for i in range(len(e)):
  for distance,j in zip(dis[i,1:],idx[i,1:]):
   if j<=i or distance>.5*wpp or len(set(e[i].tolist())&set(e[j].tolist())):continue
   if abs(t[i]@t[j])>=.96:pairs.append([i,int(j),float(distance)])
 return dict(count=len(pairs),definition='midpoint distance<=.5*wpp, abs tangent dot>=.96, no shared endpoint, among12 nearest midpoints; conservative diagnostic not exact duplicate identity',pairs=pairs)

def main():
 for n in ('lego','chair'):
  unit=n+'_supplement'
  if rt.resume(unit):continue
  folder=rt.ART/'assets'/n;record=json.loads((rt.ART/'results'/(n+'_asset.json')).read_text());assets={k:dict(np.load(folder/k/'tubes.npz')) for k in ('fused','rawunion','single')}
  for k in pp.scene(n)['roles']['construction']:assets['source '+k]=dict(np.load(folder/'sources'/k/'tubes.npz'))
  path=folder/'viewer_with_sources.html';mesh.write_viewer(path,assets);text=path.read_text().replace('固定三维轮廓区域','固定细三维轮廓线候选').replace('固定实体三角面 / Z-up','固定细世界管线 / Z-up').replace('<small id="info">','<small><a href="SOURCE_INDEX.json">source-camera / pixel / depth CSR</a> · <a href="PROVENANCE_NAMESPACES.json">provenance index namespaces</a> · source 切换仅显示独立对照，不改变 fused 几何</small><small id="info">');path.write_text(text)
  # Syntax-only validation; there is no installed browser assumed.
  script=text.split('<script>',1)[1].split('</script>',1)[0];js=rt.OUT/'tmp'/(n+'_viewer.js');js.write_text(script)
  import shutil,subprocess
  syntax='NOT_RUN_NO_NODE'
  if shutil.which('node'):
   p=subprocess.run(['node','--check',str(js)],capture_output=True,text=True);assert p.returncode==0,p.stderr;syntax='PASS_NODE_SYNTAX'
  # Verify every embedded array uses exactly the sealed exported mesh.
  data=json.loads(script.split('const assets=',1)[1].split(';const canvas=',1)[0]);import base64
  for k,a in assets.items():
   assert base64.b64decode(data[k]['vertices'])==np.asarray(a['vertices'],dtype='<f4').tobytes();assert base64.b64decode(data[k]['faces'])==np.asarray(a['faces'],dtype='<u4').tobytes()
  counts=[]
  for k in pp.scene(n)['roles']['construction']:
   c=pp.camera(n,k);K=np.asarray(c['K']);assert np.allclose(K,[[800/(2*np.tan(c['FoVx']/2)),0,399.5],[0,800/(2*np.tan(c['FoVy']/2)),399.5],[0,0,1]],atol=1e-9)
   raw=pp.cache(n,c,'construction');cs,h=cv2.findContours((raw['alpha']>=.5).astype(np.uint8),cv2.RETR_TREE,cv2.CHAIN_APPROX_NONE);small=sum(cv2.arcLength(c,True)<16 for c in cs);counts.append(dict(camera=k,all_contours=len(cs),excluded_perimeter_under16=small,kept=len(cs)-small))
  dupe={}
  for arm in ('single','rawunion','fused'):dupe[arm]=near_duplicate(dict(np.load(folder/arm/'centerlines.npz')),record['wpp'])
  p=rt.ART/'results'/(n+'_SUPPLEMENT.json');rt.atomic_json(p,dict(small_contour_exclusions=counts,near_duplicates=dupe,viewer=dict(path=str(path),embedded_assets=len(assets),byte_arrays_match_sealed_meshes=True,js_syntax=syntax,browser_interaction_tested=False)))
  pp.seal(unit,[path,p],dict(status='PASS_STATIC_VIEWER_AND_COUNTS',viewer_assets=len(assets),duplicate_counts={k:v['count'] for k,v in dupe.items()},small_contours_excluded=sum(c['excluded_perimeter_under16'] for c in counts)))
  print('SUPPLEMENT',n,{k:v['count'] for k,v in dupe.items()},syntax,flush=True)
if __name__=='__main__':main()
