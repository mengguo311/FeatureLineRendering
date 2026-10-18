from env import *
from density import fit_density,predict
from partition import dtu_seeds,infer_image,shuffle_labels,select_views
import signal,traceback
ARMS=['pooled_rgb','dev_only','shuffled_labels']
def timeout(*args):raise TimeoutError('600 second sealed unit limit')
signal.signal(signal.SIGALRM,timeout)
def load(s,v,seeds=False):
 rgb,z,a=raw(s,v);valid=np.isfinite(z)&(z>.2)&(a>=.5);seed=np.zeros(z.shape,np.uint8)
 if s=='ficus':
  sub=npz(R1/'A/ficus'/v/'SUBJECT.npz');mask=sub['candidate'];u=sub['unknown']
  if seeds:seed=npz(R2/'B/joint_rgb/fit'/(v+'.npz'))['seeds']
 else:
  mask=valid;u=(a>=.1)&~valid
  if seeds:seed=dtu_seeds(npz(R2/'A_DIAGNOSTIC'/s/v/'LOCAL_DEPTH.npz'))
 assert (seed[~mask]==0).all();return dict(rgb=rgb,z=z,alpha=a,mask=mask,subject_unknown=u,seeds=seed)
def seed_data(s,v,shuffle=False):
 d=load(s,v,True);seed=shuffle_labels(d['seeds']) if shuffle else d['seeds'];valid=seed>0;y,x=np.nonzero(valid)
 return d['rgb'][valid],seed[valid],np.c_[x,y],seed

def model(s,arm):return npz(R/'models'/s/arm/'MODEL.npz')
def saved(s,v,arm):return npz(R/'inference'/s/arm/v/'RESULT.npz')

def fit(s,arm):
 p=R/'models'/s/arm
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);signal.alarm(600);t=time.monotonic();data=[];meta=[]
 for v in select_views([DEV[s],AUX[s]],arm):
  x,y,uv,seed=seed_data(s,v,arm=='shuffled_labels');data.append((x,y));np.savez_compressed(p/(v+'_SEEDS.npz'),uv=uv,labels=y,seed_image=seed);meta.append(dict(view=v,seed_counts=np.bincount(y,minlength=4 if s=='ficus' else 3).tolist(),rgb_min=float(x.min()),rgb_max=float(x.max())))
 m=fit_density(data,3 if s=='ficus' else 2);np.savez_compressed(p/'MODEL.npz',**m);overlap=np.einsum('kabc,labc->kl',np.sqrt(m['hist']),np.sqrt(m['hist']));row=dict(scene=s,arm=arm,views=meta,seconds=time.monotonic()-t,bhattacharyya_overlap=overlap.tolist(),threshold=m['threshold'].tolist(),semantic_GT=False);js(p/'COUNT.json',row);seal(p);signal.alarm(0);print('FIT',row,flush=True)

def crossfit(s,bv,tv):
 p=R/'crossfit'/s/(bv+'_TO_'+tv)
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);x,y,_,_=seed_data(s,bv);tx,ty,uv,_=seed_data(s,tv);m=fit_density([(x,y)],3 if s=='ficus' else 2);lab,q,d=predict(m,tx);ct=np.zeros((len(m['hist']),len(m['hist'])+1),int)
 for i in range(len(m['hist'])):ct[i]=np.bincount(lab[ty==i+1],minlength=len(m['hist'])+1)
 np.savez_compressed(p/'RESULT.npz',source_seed_labels=y,target_seed_labels=ty,target_uv=uv,predicted=lab,probability=q,density=d)
 js(p/'COUNT.json',dict(scene=s,source=bv,target=tv,confusion_rows_target_proxy_cols_unknown_then_classes=ct.tolist(),known=int((lab>0).sum()),matching_proxy=int((lab==ty).sum()),total=len(ty),not_accuracy=True,threshold=m['threshold'].tolist()));seal(p);print('CROSSFIT',s,bv,tv,ct.tolist(),flush=True)

def infer(s,v,arm):
 p=R/'inference'/s/arm/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);signal.alarm(600);t=time.monotonic();data=load(s,v);m=model(s,arm);lab,u,q,d=infer_image(m,data['rgb'],data['mask']);unknown=u|data['subject_unknown'];y,x=np.nonzero(data['mask']);np.savez_compressed(p/'RESULT.npz',labels=lab,unknown=unknown,probability=q,density=d,source_uv=np.c_[x,y],inference_mask=data['mask']);row=dict(scene=s,view=v,arm=arm,eligible_pixels=int(data['mask'].sum()),unknown_eligible=int(u.sum()),label_counts=np.bincount(lab[data['mask']],minlength=len(m['hist'])+1).tolist(),no_target_seed_clamp=True,no_target_position_features=True,seconds=time.monotonic()-t)
 if s=='ficus':
  old=npz(R2/'B/joint_rgb'/('fit' if v in [DEV[s],AUX[s]] else v)/(v+'.npz'));ou=data['mask']&(old['labels']==0);row.update(r02_unknown_pixels=int(ou.sum()),r02_unknown_now_known=int((ou&(lab>0)).sum()),r02_known_now_unknown=int((data['mask']&(old['labels']>0)&(lab==0)).sum()),r02_known_both_different=int(((old['labels']>0)&(lab>0)&(old['labels']!=lab)).sum()))
 js(p/'COUNT.json',row);seal(p);signal.alarm(0);print('INFER',row,flush=True)

def figure(s,v):
 p=R/'figures'/s/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);rgb,_,_=raw(s,v);ref=npz(V1/'stageA'/s/v/'REFERENCE.npz');now=saved(s,v,'pooled_rgb')
 if s=='ficus':
  old=npz(R2/'B/joint_rgb'/('fit' if v in [DEV[s],AUX[s]] else v)/(v+'.npz'));base=colors(rgb,old['labels'],old['unknown']);base_title='r02 seeded graph | known limitation';legend='Ficus: blue lower/pot prior; orange middle/wood prior; green crown prior; gray UNKNOWN. Appearance is not physical part truth.'
 else:
  old=npz(R1/'A'/s/v/'SUBJECT.npz');base=overlay(rgb,old['candidate'],old['unknown']);base_title='r01 subject proxy | A gate failed';legend='DTU: blue peripheral-horizontal color match; orange central-nonhorizontal color match; gray UNKNOWN. NOT object labels or parts.'
 panel(p/'FULL.jpg',[('Original source RGB',rgb),('Original C8 line | XRAY reference',ref['line_rgb']),('TRUE joint GS | frozen CPU reference',ref['joint_rgb']),(base_title,base),('r03 pooled RGB likelihood | no spatial inference',colors(rgb,now['labels'],now['unknown'])),('Posterior maximum | confidence only',np.repeat(now['probability'].max(2)[...,None],3,2))],s+' / '+v+' | Nonlocal conditional appearance',legend,3)
 items=[('Original source RGB',rgb)]
 for arm in ARMS:
  d=saved(s,v,arm);items.append((arm,colors(rgb,d['labels'],d['unknown'])))
 if s=='ficus':
  r1=npz(R1/'B/ficus'/v/'profile.npz');v2=npz(V2/'stageB/ficus'/v/'shared_rgb_only_k3.npz');items.extend([('r01 fixed axial coarse blocks',colors(rgb,r1['labels'],r1['unknown'])),('v02 shared RGB-only K3 | strong baseline',colors(rgb,v2['labels'],v2['unknown']))])
 else:
  vv=npz(V2/'stageA'/s/v/'SUBJECT.npz');items.extend([('v02 subject | failed reference',overlay(rgb,vv['candidate'],vv['unknown'])),(base_title,base)])
 panel(p/'CONTROLS.jpg',items,s+' / '+v+' | Fixed arms',legend+' dev_only has one view; shuffled has matched seed/color budget.',3)
 if v in [DEV[s],AUX[s]]:
  d=load(s,v,True);panel(p/'SEEDS.jpg',[('Original source RGB',rgb),('Frozen proxy seeds | not GT',colors(rgb,d['seeds'],np.zeros(d['seeds'].shape,bool))),('New prediction | seeds not clamped',colors(rgb,now['labels'],now['unknown']))],s+' / '+v+' | Seed audit',legend,3)
 seal(p)

def main():
 import argparse;p=argparse.ArgumentParser();p.add_argument('--phase',choices=['fit','reserved'],required=True);a=p.parse_args();status(a.phase.upper(),children=[os.getpid()]);failed=[]
 for s in SCENES:
  try:
   guard()
   if a.phase=='fit':
    for arm in ARMS:fit(s,arm)
    crossfit(s,DEV[s],AUX[s]);crossfit(s,AUX[s],DEV[s])
   for v in ([DEV[s],AUX[s]] if a.phase=='fit' else RES[s]):
    for arm in ARMS:infer(s,v,arm)
    figure(s,v)
  except Exception as e:
   signal.alarm(0);failed.append(s);js(R/('ENGINEERING_'+a.phase+'_'+s+'.json'),dict(error=repr(e),traceback=traceback.format_exc()))
 status(a.phase.upper()+'_DONE',children=[],failed=failed);raise SystemExit(bool(failed))
if __name__=='__main__':main()
