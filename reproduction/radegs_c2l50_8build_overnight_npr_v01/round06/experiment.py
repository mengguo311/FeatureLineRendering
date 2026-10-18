from env import *
from morphology import describe
from likelihood import fit,predict,shuffle
from protocol import authorize_fit,fit_views,pack
import signal,traceback
ARMS=['rgb','rgb_morph','rgb_shuffled_morph']
def alarm(*a):raise TimeoutError('600 second unit limit')
signal.signal(signal.SIGALRM,alarm)
def old(s,v,which=5):
 p=R5/'B'/s/'withdraw_conflict'/('fit' if v in [DEV[s],AUX[s]] else v)/(v+'.npz') if which==5 else R3/'inference'/s/'pooled_rgb'/v/'RESULT.npz'
 return npz(p)
def masks(s,v):
 if s=='ficus':
  a=npz(R1/'A'/s/v/'SUBJECT.npz');return a['candidate'],a['unknown']
 _,z,a=raw(s,v);m=np.isfinite(z)&(z>.2)&(a>=.5);return m,(a>=.1)&~m
def shape_arrays(s,v):
 m,u=masks(s,v);return dict(**describe(m,u),candidate=m,subject_unknown=u)
def shape(s,v):return npz(R/'shape'/s/v/'FEATURES.npz')
def result(s,v,arm):return npz(R/'inference'/s/arm/v/'RESULT.npz')
def make_shape(s,v):
 p=R/'shape'/s/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);signal.alarm(600);a=shape_arrays(s,v);np.savez_compressed(p/'FEATURES.npz',**a);m=a['candidate'];row=dict(scene=s,view=v,mask_pixels=int(m.sum()),unknown_pixels=int(a['subject_unknown'].sum()),shape_reliable=int(a['eligible'].sum()),frame_unknown=int(a['frame_unknown'].sum()),spread_quantiles=np.quantile(a['spread'][m],[0,.5,.9,1]).tolist(),bbox_diagonal=float(a['bbox_diagonal']),qualified_subject=s=='ficus',semantics='isolated coverage proxy' if s=='ficus' else 'SCENE coverage only; part fit refused');js(p/'COUNT.json',row);seal(p);signal.alarm(0);print('SHAPE',row,flush=True)
def seed_data(arm):
 data=[];arrays={}
 for v in fit_views('ficus'):
  rgb,_,_=raw('ficus',v);s=npz(R3/'models/ficus/pooled_rgb'/(v+'_SEEDS.npz'));uv=s['uv'];a=shape('ficus',v);f=a['feature'][uv[:,1],uv[:,0]];e=a['eligible'][uv[:,1],uv[:,0]];original_f=f.copy();original_e=e.copy()
  if arm=='rgb_shuffled_morph':f,e=shuffle(f,e)
  data.append((rgb[uv[:,1],uv[:,0]],s['labels'],f,e));arrays[v]=dict(uv=uv,labels=s['labels'],feature=f,eligible=e,original_feature=original_f,original_eligible=original_e)
 return data,arrays
def fit_model(arm):
 p=R/'models'/arm
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);data,arrays=seed_data(arm);m=fit(data,3);np.savez_compressed(p/'MODEL.npz',**m)
 for v,a in arrays.items():np.savez_compressed(p/(v+'_SEEDS.npz'),**a)
 base=npz(R3/'models/ficus/pooled_rgb/MODEL.npz')
 for x,y in [('rgb_hist','hist'),('rgb_threshold','threshold'),('classes','classes')]:np.testing.assert_array_equal(m[x],base[y])
 js(p/'COUNT.json',dict(arm=arm,fit_views=fit_views('ficus'),rgb_baseline_exact=True,seed_counts={v:np.bincount(a['labels'],minlength=4).tolist() for v,a in arrays.items()},reliable_shape_seeds={v:np.bincount(a['labels'][a['eligible']],minlength=4).tolist() for v,a in arrays.items()},shape_threshold=m['shape_threshold'].tolist()));seal(p)
def infer_arrays(v,arm):
 a=shape('ficus',v);m=a['candidate'];rgb,_,_=raw('ficus',v);model=npz(R/'models'/arm/'MODEL.npz');lab,q,rd=predict(model,rgb[m],a['feature'][m],a['eligible'][m],use_shape=arm!='rgb');out=pack(m,a['subject_unknown'],lab,q);out['morphology_used']=a['eligible'] if arm!='rgb' else np.zeros_like(m);return out
def infer(v,arm):
 p=R/'inference/ficus'/arm/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);t=time.monotonic();a=infer_arrays(v,arm);np.savez_compressed(p/'RESULT.npz',**a);m=a['inference_mask'];b=old('ficus',v,3)
 if arm=='rgb':
  for k in ['labels','unknown','probability','inference_mask','source_uv']:np.testing.assert_array_equal(a[k],b[k])
 row=dict(scene='ficus',view=v,arm=arm,counts=np.bincount(a['labels'][m],minlength=4).tolist(),unknown=int((m&(a['labels']==0)).sum()),morphology_used=int(a['morphology_used'].sum()),rgb_fallback=int((m&~a['morphology_used']).sum()),change_from_rgb=int((m&(a['labels']!=b['labels'])).sum()),known_class_change=int((m&(a['labels']>0)&(b['labels']>0)&(a['labels']!=b['labels'])).sum()),seconds=time.monotonic()-t);js(p/'COUNT.json',row);seal(p);print('INFER',row,flush=True)
def heat(a):return np.stack([a,.2*np.ones_like(a),1-a],-1)
def figure(s,v):
 p=R/'figures'/s/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);rgb,_,_=raw(s,v);a=shape(s,v);ref=npz(V1/'stageA'/s/v/'REFERENCE.npz');maskim=np.repeat(np.where(a['subject_unknown'],.5,a['candidate'])[...,None],3,2)
 items=[('Source RGB | immutable',rgb),('Original C8 ink | XRAY reference',ref['line_rgb']),('TRUE joint | frozen CPU full-SH reference',ref['joint_rgb']),('Subject proxy' if s=='ficus' else 'SCENE coverage, NOT subject',maskim),('Normalized distance to negative space',heat(a['feature'][...,0])),('Large-scale occupancy | no labels',heat(a['feature'][...,2]))]
 panel(p/'EVIDENCE.jpg',items,s+' / '+v+' | r06 morphology input qualification','No RGB/ink used in shape. Gray unknown. DTU background coverage invalidates subject interpretation.',3)
 if s=='ficus':
  items=[('Original source RGB',rgb)]
  for arm in ARMS:
   d=result(s,v,arm);items.append((arm,colors(rgb,d['labels'],d['unknown'])))
  prev=old(s,v);items.append(('r05 graph | read-only strong context',colors(rgb,prev['labels'],prev['unknown'])));b=npz(V2/'stageB/ficus'/v/'shared_rgb_only_k3.npz');items.append(('v02 RGB-only | read-only baseline',colors(rgb,b['labels'],b['unknown'])))
  panel(p/'FULL.jpg',items,s+' / '+v+' | New morphology information versus null','Blue pot-prior; orange wood-prior; green crown-prior; gray UNKNOWN. Diagnostic labels, not source GS membership.',3)
 else:
  prev=old(s,v);sub=npz(R1/'A'/s/v/'SUBJECT.npz');panel(p/'FULL.jpg',[('Original RGB',rgb),('r05 color labels | not complete subject',colors(rgb,prev['labels'],prev['unknown'])),('r01 subject | failed reference',overlay(rgb,sub['candidate'],sub['unknown'])),('Scene coverage includes table/platform',maskim)],s+' / '+v+' | A failed: new B part fit NOT_RUN','Full scene alpha is not object segmentation. Morphology alone has no qualified subject input here.',2)
 seal(p)
def main():
 import argparse;p=argparse.ArgumentParser();p.add_argument('--phase',choices=['fit','reserved'],required=True);a=p.parse_args();status('RUN_'+a.phase,children=[os.getpid()]);failed=[]
 for s in ['ficus','scan24','scan65']:
  try:
   guard();vv=([DEV[s],AUX[s]] if a.phase=='fit' else RES[s])
   for v in vv:make_shape(s,v)
   if s=='ficus':
    if a.phase=='fit':
     for arm in ARMS:fit_model(arm)
    for v in vv:
     for arm in ARMS:infer(v,arm)
   for v in vv:figure(s,v)
  except Exception as ex:
   signal.alarm(0);failed.append(s);js(R/('ENGINEERING_'+s+'_'+a.phase+'.json'),dict(error=repr(ex),traceback=traceback.format_exc()));print(traceback.format_exc(),flush=True)
 status('DONE_'+a.phase,children=[],failed=failed);raise SystemExit(bool(failed))
if __name__=='__main__':main()
