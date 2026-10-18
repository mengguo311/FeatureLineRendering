from env import *
from texture import describe,block_shuffle
from likelihood import ARMS,authorize_fit,fit,predict,pack
import signal,traceback

def alarm(*a):raise TimeoutError('300-second unit')
signal.signal(signal.SIGALRM,alarm)
def old(s,v,which=5):
 p=R5/'B'/s/'withdraw_conflict'/('fit' if v in [DEV[s],AUX[s]] else v)/(v+'.npz') if which==5 else R3/'inference'/s/'pooled_rgb'/v/'RESULT.npz';return npz(p)
def result(s,v,arm):return npz(R/'inference'/s/arm/v/'RESULT.npz')
def feature_arrays(s,v):
 rgb,_,_=raw(s,v);shuffled=block_shuffle(rgb);return dict(texture=describe(rgb),scrambled_texture=describe(shuffled),shuffled_rgb=shuffled)
def make_features(s,v):
 p=R/'features'/s/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);t=time.monotonic();rgb,_,_=raw(s,v);a=feature_arrays(s,v);np.savez_compressed(p/'FEATURES.npz',**a)
 coh=np.linalg.norm(2*a['texture'][...,:2]-1,axis=2);energy=a['texture'][...,2];js(p/'COUNT.json',dict(scene=s,view=v,seconds=time.monotonic()-t,shape=list(rgb.shape),feature_min=float(a['texture'].min()),feature_max=float(a['texture'].max()),block=max(1,int(round(33*min(rgb.shape[:2])/581))),source_rgb_unchanged=True))
 panel(p/'FEATURES.jpg',[('Original source RGB',rgb),('Block-shuffled RGB | null only',a['shuffled_rgb']),('Real tensor feature encoding',a['texture']),('Shuffled tensor feature encoding',a['scrambled_texture']),('Real anisotropy | fixed 0..1',np.repeat(coh[...,None],3,axis=2)),('Real contrast energy | fixed 0..1',np.repeat(energy[...,None],3,axis=2))],s+'/'+v+' | Local texture evidence','Not new source renders or semantic maps. Shuffle keeps each block RGB multiset; may create artificial edges.',3);seal(p);print('FEATURE',s,v,flush=True)
def features(s,v,arm):return npz(R/'features'/s/v/'FEATURES.npz')['scrambled_texture' if arm=='rgb_scrambled_texture' else 'texture']
def seed_data(s,arm):
 authorize_fit(s,[DEV[s],AUX[s]]);data=[];seeds={}
 for v in [DEV[s],AUX[s]]:
  sd=npz(R3/'models'/s/'pooled_rgb'/(v+'_SEEDS.npz'));uv=sd['uv'];rgb,_,_=raw(s,v);t=features(s,v,arm);x=rgb[uv[:,1],uv[:,0]];tt=t[uv[:,1],uv[:,0]];data.append((x,tt,sd['labels']));seeds[v]=dict(uv=uv,labels=sd['labels'],raw_rgb=x,texture=tt)
 return data,seeds

def fit_model(s,arm):
 p=R/'models'/s/arm
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);data,seeds=seed_data(s,arm);m=fit(data,3 if s=='ficus' else 2,arm)
 if arm=='raw_rgb':
  b=npz(R3/'models'/s/'pooled_rgb'/'MODEL.npz');np.testing.assert_array_equal(m['rgb_hist'],b['hist']);np.testing.assert_array_equal(m['threshold'],b['threshold'])
 np.savez_compressed(p/'MODEL.npz',**m)
 for v,a in seeds.items():np.savez_compressed(p/(v+'_SEEDS.npz'),**a)
 js(p/'COUNT.json',dict(scene=s,arm=arm,fit_views=[DEV[s],AUX[s]],classes=int(m['classes']),seed_counts={v:np.bincount(x['labels']).tolist() for v,x in seeds.items()},new_GT=False));seal(p);print('MODEL',s,arm,flush=True)
def infer_arrays(s,v,arm):
 b=old(s,v,3);mask=b['inference_mask'];rgb,_,_=raw(s,v);t=features(s,v,arm);m=npz(R/'models'/s/arm/'MODEL.npz');l,q,d=predict(m,rgb[mask],t[mask],arm);return pack(mask,b['unknown']&~mask,l,q,d)
def infer(s,v,arm):
 p=R/'inference'/s/arm/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);a=infer_arrays(s,v,arm);b=old(s,v,3)
 if arm=='raw_rgb':
  for k in a:np.testing.assert_array_equal(a[k],b[k],err_msg='raw exact '+k)
 np.savez_compressed(p/'RESULT.npz',**a);mask=a['inference_mask'];row=dict(scene=s,view=v,arm=arm,mask_pixels=int(mask.sum()),counts=np.bincount(a['labels'][mask],minlength=4 if s=='ficus' else 3).tolist(),unknown=int((mask&(a['labels']==0)).sum()),changed_from_raw=int((mask&(a['labels']!=b['labels'])).sum()),known_changed=int((mask&(a['labels']>0)&(b['labels']>0)&(a['labels']!=b['labels'])).sum()));js(p/'COUNT.json',row);seal(p);print('INFER',row,flush=True)
def figure(s,v):
 p=R/'figures'/s/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);rgb,_,_=raw(s,v);ref=npz(V1/'stageA'/s/v/'REFERENCE.npz');items=[('Original cached RGB',rgb)]
 for arm in ARMS:
  a=result(s,v,arm);items.append((arm+' | fixed original mask',colors(rgb,a['labels'],a['unknown'])))
 a=old(s,v);items.append(('r05 graph | strong historical context',colors(rgb,a['labels'],a['unknown'])))
 legend='Blue pot-prior / orange wood-prior / green crown-prior / gray UNKNOWN.' if s=='ficus' else 'Blue peripheral-horizontal prior / orange central-nonhorizontal prior / gray UNKNOWN. NOT semantic foreground.'
 panel(p/'FULL.jpg',items,s+'/'+v+' | r09 local texture layout',legend+' Same gain; diagnostic color overlay, NOT styled GS.',3)
 dc=npz(R7/'inference'/s/'dc_only'/v/'RESULT.npz');panel(p/'CONTEXT.jpg',[('Original C8 | readonly XRAY',ref['line_rgb']),('Original TRUE joint | readonly CPU EWA',ref['joint_rgb']),('r07 DC classification | strong context',colors(rgb,dc['labels'],dc['unknown']))],s+'/'+v+' | Immutable C8 / source references','No original line or source change. These reference renders are not newly generated in r09.',3)
 if s=='ficus':
  b=npz(V2/'stageB/ficus'/v/'shared_rgb_only_k3.npz');a=result(s,v,'rgb_texture');panel(p/'RGB_STRONG.jpg',[('Original RGB',rgb),('v02 RGB-only K3 | readonly strong baseline',colors(rgb,b['labels'],b['unknown'])),('r09 RGB + texture candidate',colors(rgb,a['labels'],a['unknown']))],s+'/'+v+' | Strong RGB-only comparison','No semantic GT; full native frame, no filling leaf gaps.',3)
 seal(p)
def run(s,reserved=False):
 vv=RES[s] if reserved else [DEV[s],AUX[s]]
 for v in vv:guard();signal.alarm(300);make_features(s,v);signal.alarm(0)
 if not reserved:
  for arm in ARMS:fit_model(s,arm)
 for v in vv:
  signal.alarm(300)
  for arm in ARMS:infer(s,v,arm)
  figure(s,v);signal.alarm(0)
def main():
 import argparse;p=argparse.ArgumentParser();p.add_argument('--phase',choices=['pilot','fit','reserved'],required=True);a=p.parse_args();status('RUN_'+a.phase,children=[os.getpid()]);failed=[]
 if a.phase=='reserved':assert (R/'reviews/03_reserved_GO.md').exists()
 for s in ['ficus'] if a.phase=='pilot' else ['ficus','scan24','scan65']:
  try:run(s,reserved=a.phase=='reserved')
  except Exception as e:
   signal.alarm(0);failed.append(s);js(R/('ENGINEERING_'+s+'_'+a.phase+'.json'),dict(error=repr(e),traceback=traceback.format_exc()));print(traceback.format_exc(),flush=True)
 status('DONE_'+a.phase,children=[],failed=failed);raise SystemExit(bool(failed))
if __name__=='__main__':main()
