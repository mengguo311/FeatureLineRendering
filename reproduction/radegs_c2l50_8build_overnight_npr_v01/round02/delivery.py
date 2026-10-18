from env import *
from experiment import view_result,ARMS
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
def main():
 p=R/'delivery';p.mkdir(exist_ok=True);stats=[]
 for arm in ARMS:
  g=npz(R/'B'/arm/'fit/GRAPH.npz');n=len(g['seeds']);W=coo_matrix((np.ones(2*len(g['i'])),(np.r_[g['i'],g['j']],np.r_[g['j'],g['i']])),shape=(n,n)).tocsr();nc,cc=connected_components(W,directed=False);presence=np.zeros((nc,3),bool)
  for k in [1,2,3]:presence[cc[g['seeds']==k],k-1]=True
  types=presence.sum(1)[cc];row=dict(arm=arm,components=nc,no_seed_nodes=int((types==0).sum()),one_seed_class_nodes=int((types==1).sum()),multi_seed_class_nodes=int((types>=2).sum()),all_nodes=n,explanation='On a one-label-anchored connected component harmonic probabilities cannot infer another semantic class, regardless of RGB weights.');stats.append(row);np.savez_compressed(p/(arm+'_COMPONENTS.npz'),component_id=cc,anchor_label_count=types,view_offsets=g['view_offsets'])
  if arm=='joint_rgb':
   for vi,v in enumerate([DEV['ficus'],AUX['ficus']]):
    rgb,_,_=raw('ficus',v);d=view_result(v,arm);mask=npz(R1/'A/ficus'/v/'SUBJECT.npz')['candidate'];t=np.zeros(mask.shape,np.uint8);t[mask]=types[g['view_offsets'][vi]:g['view_offsets'][vi+1]];im=rgb.copy();im[mask&(t==0)]=.4*im[mask&(t==0)]+.6*np.array([.4,.4,.4]);im[t==1]=.4*im[t==1]+.6*np.array([.9,.7,.1]);im[t>=2]=.4*im[t>=2]+.6*np.array([.85,.15,.7]);panel(p/('COMPONENTS_'+v+'.jpg'),[('Source RGB',rgb),('r02 region candidates',colors(rgb,d['labels'],d['unknown'])),('Grey: no seed; gold: one class; magenta: competition',im)],'Ficus / '+v+' | Why boundary evidence has limited leverage','Existing qualified graph only; no new links or relaxed thresholds. Component type is graph evidence, not semantic GT.',3)
 js(p/'COMPONENT_AUDIT.json',stats)
 changes=[]
 for v in views('ficus'):
  main=view_result(v,'joint_rgb');sub=npz(R1/'A/ficus'/v/'SUBJECT.npz')['candidate'];row=dict(view=v,subject_pixels=int(sub.sum()),unknown=int((sub&(main['labels']==0)).sum()))
  for arm in ['independent_rgb','joint_no_rgb']:
   d=view_result(v,arm);row[arm+'_different']=int((main['labels']!=d['labels']).sum());row[arm+'_different_known_both']=int(((main['labels']!=d['labels'])&(main['labels']>0)&(d['labels']>0)).sum())
  changes.append(row)
 js(p/'ARM_DIFFERENCES.json',changes)
 # Full native frames in four-view boards; no per-view color or exposure adjustment.
 for s in SCENES:
  items=[]
  for v in views(s):
   rgb,_,a=raw(s,v)
   if s=='ficus':
    old=npz(R1/'B/ficus'/v/'profile.npz');new=view_result(v,'joint_rgb');items.extend([(v+' | Source',rgb),(v+' | r01',colors(rgb,old['labels'],old['unknown'])),(v+' | r02',colors(rgb,new['labels'],new['unknown']))])
   else:
    old=npz(R1/'A'/s/v/'SUBJECT.npz');ar=npz(R/'A_DIAGNOSTIC'/s/v/'LOCAL_DEPTH.npz');l=np.zeros(a.shape,np.uint8);l[ar['valid']]=2;l[ar['upright']]=1;items.extend([(v+' | Source',rgb),(v+' | r01 A failure',overlay(rgb,old['candidate'],old['unknown'])),(v+' | r02 local orientation',colors(rgb,l,(a>=.1)&~ar['valid']))])
  panel(p/(s+'_FOUR_VIEWS.jpg'),items,s+' | r02 frozen full-frame comparison','All historical views, not blind. DTU only normal-evidence diagnosis; Ficus regions remain hypotheses, UNKNOWN visible.',3)
 for v,box in [('train_r_80',[250,500,550,760]),('test_r_79',[250,440,550,730])]:
  rgb,_,_=raw('ficus',v);x0,y0,x1,y1=box;crop=lambda x:x[y0:y1,x0:x1];items=[('Source | same old explanatory crop',crop(rgb))];old=npz(R1/'B/ficus'/v/'profile.npz');items.append(('r01',crop(colors(rgb,old['labels'],old['unknown']))))
  for arm in ARMS:
   a=view_result(v,arm);items.append((arm,crop(colors(rgb,a['labels'],a['unknown']))))
  panel(p/('RIM_'+v+'.jpg'),items,'Ficus / '+v+' | Rim and trunk failure audit','Explanatory crop only, never seed, fit ROI or selection mask. Complete frames also delivered.',3)
 counts=dict(DTU=[json.loads(x.read_text()) for x in sorted((R/'A_DIAGNOSTIC').rglob('COUNT.json'))],Ficus=[json.loads(x.read_text()) for x in sorted((R/'B').rglob('*_COUNT.json'))],fit_arms=3,fit_views=2,target_arms=3,target_views=2,source_memberships=0,new_GS_models=0,styles=0,videos=0)
 js(R/'COUNTS.json',counts);print(json.dumps(dict(components=stats,differences=changes),indent=2))
if __name__=='__main__':main()
