"""Actual frozen-tube isolated profiles plus dense-ink diagnostics, no geometry changes."""
import runtime as rt
import pipeline as pp
import mesh_tools as mesh
from core import project
import numpy as np,json,cv2

def profiles(n,c,arm):
 folder=rt.ART/'assets'/n/arm;g=dict(np.load(folder/'centerlines.npz'));a=dict(np.load(folder/'tubes.npz'));j=json.loads((folder/'CENTERLINES.json').read_text());p,z=project(g['xyz'],c);e=g['edges'];mid=p[e].mean(1);vec=p[e[:,1]]-p[e[:,0]];length=np.linalg.norm(vec,axis=1)
 edge_lookup={tuple(sorted(x)):i for i,x in enumerate(e.tolist())};pid=np.zeros(len(e),np.int32)
 for k,path in enumerate(j['paths']):
  for x,y in zip(path,path[1:]):pid[edge_lookup[tuple(sorted((x,y)))]]=k
 r=mesh.render_mesh(a['vertices'],a['faces'],c,color=(0,0,0));owner=r['face_index'];valid=np.flatnonzero((length>=3)&(mid[:,0]>=10)&(mid[:,0]<790)&(mid[:,1]>=10)&(mid[:,1]<790)&np.all(z[e]>0,axis=1));sample=valid[np.linspace(0,len(valid)-1,min(len(valid),256)).astype(int)] if len(valid) else [];width=[];records=[];counts={'too_short_or_offscreen':int(len(e)-len(valid)),'sampled':len(sample),'crowded':0,'no_center_ink':0}
 peredge=len(a['faces'])//len(e);assert peredge==28
 mask=r['mask'].astype(np.float32)
 for ei in sample:
  x,y=mid[ei];ix,iy=int(round(x)),int(round(y));wins=owner[iy-4:iy+5,ix-4:ix+5];ids=np.unique(wins[wins>=0]//peredge)
  # An isolated profile may contain neighbouring cylinders on this same frozen path.
  if np.any(pid[ids]!=pid[ei]):counts['crowded']+=1;continue
  t=np.array([-vec[ei,1],vec[ei,0]])/length[ei];s=np.arange(-10,10.001,.125,dtype=np.float32);uv=mid[ei]+s[:,None]*t
  value=cv2.remap(mask,uv[:,0].astype(np.float32)[None],uv[:,1].astype(np.float32)[None],cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)[0]>=.5
  center=np.flatnonzero(value&(abs(s)<=1.5))
  if not len(center):counts['no_center_ink']+=1;continue
  k=int(center[np.argmin(abs(s[center]))]);l=k;h=k
  while l>0 and value[l-1]:l-=1
  while h+1<len(s) and value[h+1]:h+=1
  diameter=float((h-l+1)*.125);width.append(diameter);records.append(dict(edge=int(ei),path=int(pid[ei]),midpoint_px=mid[ei].tolist(),diameter_px=diameter))
 return dict(camera=c['key'],camera_sha256=c['camera_sha256'],arm=arm,counts=counts,isolated_profiles=len(width),diameter_p50_p95_p99_max=np.quantile(width,[.5,.95,.99,1]).tolist() if width else None,profile_p95_over6=bool(np.quantile(width,.95)>6) if width else None,records=records,definition='actual 800px tube raster; normal bilinear mask profile threshold .5 at projected edge midpoint; edge projected length >=3px; 9x9 winner patch contains only one immutable path; deterministic at most256 edge samples. Alias/joints/caps still affect measurement; crowded cases excluded here but included in full-ink metrics.')

def main():
 for n in ('lego','chair'):
  unit=n+'_width_audit'
  if rt.resume(unit):continue
  assert rt.resume(n+'_asset');rows=[]
  for key in pp.scene(n)['roles']['dev']+pp.scene(n)['roles']['reserved']:
   for arm in ('single','rawunion','fused'):rows.append(profiles(n,pp.camera(n,key),arm))
   print('WIDTH',n,key,flush=True)
  p=rt.ART/'results'/(n+'_WIDTH_PROFILES.json');rt.atomic_json(p,dict(actual_world_tubes=True,rows=rows));pp.seal(unit,[p],dict(status='MEASURED',profile_count=sum(a['isolated_profiles'] for a in rows),nonempty_p95_max=max(a['diameter_p50_p95_p99_max'][1] for a in rows if a['isolated_profiles']),full_ink_dense_regions='all perview metrics include large intersection/crowded ink, independently of isolated profiles'))
if __name__=='__main__':main()
