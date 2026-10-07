import runtime as rt
import pipeline as pp
import mesh_tools as mesh
from core import project
from media_tools import make_panel
import numpy as np,json,cv2

def profile(mask,mid,normal):
 s=np.arange(-10,10.001,.125,dtype=np.float32);p=mid+s[:,None]*normal;v=cv2.remap(mask.astype(np.float32),p[:,0].astype(np.float32)[None],p[:,1].astype(np.float32)[None],cv2.INTER_LINEAR)[0]>=.5;idx=np.flatnonzero(v&(abs(s)<=1.5))
 if not len(idx):return None
 k=int(idx[np.argmin(abs(s[idx]))]);a=b=k
 while a>0 and v[a-1]:a-=1
 while b+1<len(v) and v[b+1]:b+=1
 return float((b-a+1)*.125)
def main():
 for n in ('lego','chair'):
  unit=n+'_width_tails'
  if rt.resume(unit):continue
  data=json.loads((rt.ART/'results'/(n+'_WIDTH_PROFILES.json')).read_text())['rows'];candidates=[]
  for arm in ('single','rawunion','fused'):
   allrec=[dict(x,arm=arm,camera=r['camera']) for r in data if r['arm']==arm for x in r['records']]
   candidates+=sorted(allrec,key=lambda x:x['diameter_px'],reverse=True)[:4]
  rows=[];results=[]
  for a in candidates:
   arm=a['arm'];c=pp.camera(n,a['camera']);folder=rt.ART/'assets'/n/arm;g=dict(np.load(folder/'centerlines.npz'));full=dict(np.load(folder/'tubes.npz'));edge=g['edges'][a['edge']];v,f=mesh.tube_mesh(g['xyz'],[edge],float(g['radius']));one=mesh.render_mesh(v,f,c,color=(0,0,0));whole=mesh.render_mesh(full['vertices'],full['faces'],c,color=(0,0,0));uv,z=project(g['xyz'][edge],c);mid=uv.mean(0);t=uv[1]-uv[0];normal=np.array([-t[1],t[0]])/np.linalg.norm(t);own=profile(one['mask'],mid,normal);x,y=np.clip(np.rint(mid)-32,0,736).astype(int)
   photos=[]
   for image in (whole['rgb'],one['rgb']):
    im=image.copy();q=np.rint([mid-10*normal,mid+10*normal]).astype(int);cv2.line(im,tuple(q[0]),tuple(q[1]),(230,50,50),1);photos.append(im[y:y+64,x:x+64])
   rows.append([(f"{arm} {a['camera']} edge{a['edge']} full-path profile={a['diameter_px']:.3f}px",photos[0]),(f"same frozen cylinder rendered alone={own}px",photos[1])]);results.append(dict(a,isolated_same_cylinder_diameter=own,crop_xy=[int(x),int(y)]))
  p=rt.ART/'media'/n/'WIDTH_TAILS.png';make_panel(rows,p,title=n+' worst same-path profiles; red = measurement normal; no geometry change',tile_size=256,label_height=64)
  j=rt.ART/'results'/(n+'_WIDTH_TAILS.json');rt.atomic_json(j,dict(cases=results,interpretation='Original profile isolation only rejected OTHER winning paths in9x9 patch. Same-path nonlocal folds/overlaps can remain, so it is a candidate-isolation diagnostic, not strict individual-cylinder width. Worst records and full masks retained; separate actual single-cylinder raster identifies the difference.'))
  pp.seal(unit,[p,j],dict(status='MEASURED_WORST_TAILS',cases=len(results),max_individual_cylinder_width=max(a['isolated_same_cylinder_diameter'] or 0 for a in results)));print('TAILS',n,max(a['isolated_same_cylinder_diameter'] or 0 for a in results),flush=True)
if __name__=='__main__':main()
