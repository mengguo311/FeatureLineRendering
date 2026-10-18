from env import *
from upright import CFG
def plane_audit(s):
 data=npz(V2/'stageA'/s/'model/FIT_SAMPLES.npz');X=data['world'];p=data['pixel_scale'];per=data['peripheral'];cen=data['central'];v=data['view_id'];up=np.asarray(json.loads((R/'A'/s/'model/MODEL.json').read_text())['axis']['up']);pool=np.flatnonzero(per);pool=pool[np.linspace(0,len(pool)-1,min(len(pool),8000),dtype=int)];ci=np.flatnonzero(cen);ci=ci[np.linspace(0,len(ci)-1,min(len(ci),2000),dtype=int)];rng=np.random.default_rng(1729);rows=[]
 for i in range(768):
  pts=X[rng.choice(pool,3,replace=False)];n=np.cross(pts[1]-pts[0],pts[2]-pts[0]);norm=np.linalg.norm(n)
  if norm<1e-12:continue
  n/=norm;d=-n@pts[0];angle=float(np.degrees(np.arccos(np.clip(abs(n@up),0,1))));good=abs(X[pool]@n+d)/p[pool]<=2.5;fra=[float(good[v[pool]==j].mean()) for j in np.unique(v)];cf=float((abs(X[ci]@n+d)/p[ci]<=2.5).mean());rows.append([i,angle,*fra,cf])
 ar=np.array(rows);old=json.loads((V2/'stageA'/s/'model/MODEL.json').read_text())['plane'];angle=float(np.degrees(np.arccos(np.clip(abs(np.asarray(old['normal'])@up),0,1)))) if old else None;ok=ar[:,1]<=20;qualified=ok&(ar[:,2:4].min(1)>=.15)&(ar[:,4]<=.35);summary=dict(scene=s,hypotheses=len(ar),orientation_pass=int(ok.sum()),coverage_and_center_pass=int(qualified.sum()),v02_plane_angle_to_up=angle,best_min_view_support_with_qualified_orientation=float(ar[ok,2:4].min(1).max()) if ok.any() else None,diagnostic_only_no_threshold_changes=True);return ar,summary
def collage(s,mode):
 items=[]
 for v in views(s):
  rgb,_,_=raw(s,v)
  if mode=='A':
   old=npz(V2/'stageA'/s/v/'SUBJECT.npz');new=npz(R/'A'/s/v/'SUBJECT.npz');items.extend([(v+' | source RGB',rgb),(v+' | v02',overlay(rgb,old['candidate'],old['unknown'])),(v+' | r01',overlay(rgb,new['candidate'],new['unknown']))])
  else:
   old=npz(V2/'stageB'/s/v/'shared_xyz_lab_width_k3.npz');new=npz(R/'B'/s/v/'profile.npz');null=npz(R/'B'/s/v/'equal_thirds.npz');items.extend([(v+' | v02 K3',colors(rgb,old['labels'],old['unknown'])),(v+' | r01 profile',colors(rgb,new['labels'],new['unknown'])),(v+' | equal thirds null',colors(rgb,null['labels'],null['unknown']))])
 panel(R/'delivery'/(s+'_'+mode+'_FOUR_VIEWS.jpg'),items,s+' | r01 all four frozen historical views','Complete native frames. Same palette is not semantic certification. UNKNOWN is retained, not erased.',3)
def main():
 q=R/'delivery';q.mkdir(exist_ok=True);rows=[]
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 for s in ['scan24','scan65']:
  ar,row=plane_audit(s);np.savez_compressed(q/(s+'_PLANE_HYPOTHESES.npz'),hypotheses=ar);rows.append(row);fig,ax=plt.subplots(figsize=(7,5));ax.scatter(ar[:,1],ar[:,2:4].min(1),s=8,c=ar[:,4],vmin=0,vmax=1);ax.axvline(20,c='r',ls='--');ax.axhline(.15,c='r',ls='--');ax.set(xlabel='Angle to calibrated upright proxy (degrees)',ylabel='Minimum peripheral support across views',title=s+' | All frozen hypotheses; color = central overlap');fig.tight_layout();fig.savefig(q/(s+'_PLANE_DIAGNOSTIC.png'),dpi=150);plt.close(fig)
 js(q/'PLANE_AUDIT.json',rows)
 for s in SCENES:collage(s,'A')
 collage('ficus','B');roirows=[]
 for v,box in [('train_r_80',[250,500,550,760]),('test_r_79',[250,440,550,730])]:
  rgb,_,_=raw('ficus',v);a=npz(R/'B/ficus'/v/'profile.npz');b=npz(R/'B/ficus'/v/'equal_thirds.npz');x0,y0,x1,y1=box;crop=lambda x:x[y0:y1,x0:x1];panel(q/('FICUS_RIM_'+v+'.jpg'),[('Source crop',crop(rgb)),('Profile: pot rim leaks into middle layer',crop(colors(rgb,a['labels'],a['unknown']))),('Equal thirds: trunk leaks into lower layer',crop(colors(rgb,b['labels'],b['unknown'])))],'Ficus '+v+' | Failure detail; full frames also delivered','Explanatory crop only. Never used in sampling, fitting or thresholds.',3);roirows.append(dict(view=v,box_xyxy=box,explanatory_not_algorithm_input=True))
 js(q/'EXPLANATORY_ROIS.json',roirows)
 # Overview thumbnails preserve aspect; native evidence remains in scene units.
 frames=[]
 for s in SCENES:
  v=DEV[s];rgb,_,_=raw(s,v);old=npz(V2/'stageA'/s/v/'SUBJECT.npz');new=npz(R/'A'/s/v/'SUBJECT.npz')
  oldim=overlay(rgb,old['candidate'],old['unknown']);newim=overlay(rgb,new['candidate'],new['unknown'])
  if s=='ficus':
   a=npz(V2/'stageB/ficus'/v/'shared_xyz_lab_width_k3.npz');b=npz(R/'B/ficus'/v/'profile.npz');oldim=colors(rgb,a['labels'],a['unknown']);newim=colors(rgb,b['labels'],b['unknown'])
  for label,im in [('Source',rgb),('v02',oldim),('r01',newim)]:
   pi=Image.fromarray(np.uint8(np.clip(im,0,1)*255));pi.thumbnail((800,800));canvas=Image.new('RGB',(800,800),'white');canvas.paste(pi,((800-pi.width)//2,(800-pi.height)//2));frames.append((s+' | '+label,np.asarray(canvas)/255))
 panel(q/'OVERVIEW.jpg',frames,'Overnight r01 | Upright support + axial structural hypotheses','DTU subject gate NO_GO; Ficus coarse interiors PARTIAL. Native panels and negative examples retained.',3)
 js(R/'COUNTS.json',dict(A=[json.loads(p.read_text()) for p in sorted((R/'A').rglob('COUNT.json'))],B=[json.loads(p.read_text()) for p in sorted((R/'B').rglob('COUNTS.json'))],source_regions=0,new_GS_models=0,styles=0,videos=0,primary_views_per_scene=4))
 print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
