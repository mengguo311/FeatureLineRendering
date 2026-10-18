from env import *
from features import ARMS,transform
from protocol import authorize_fit,training,pack
from density import fit_density,predict
import signal,traceback

def alarm(*a):raise TimeoutError('300 second unit')
signal.signal(signal.SIGALRM,alarm)
def old(s,v,which=5):
 p=R5/'B'/s/'withdraw_conflict'/('fit' if v in [DEV[s],AUX[s]] else v)/(v+'.npz') if which==5 else R3/'inference'/s/'pooled_rgb'/v/'RESULT.npz';return npz(p)
def result(s,v,arm):return npz(R/'inference'/s/arm/v/'RESULT.npz')
def seed_data(s,arm):
 authorize_fit(s,[DEV[s],AUX[s]]);data=[];seeds={}
 for v in [DEV[s],AUX[s]]:
  sd=npz(R3/'models'/s/'pooled_rgb'/(v+'_SEEDS.npz'));uv=sd['uv'];rgb,_,_=raw(s,v);x=rgb[uv[:,1],uv[:,0]];t=training(x,sd['labels'],arm,3 if s=='ficus' else 2);data.append((t['features'],t['labels']));seeds[v]=dict(uv=uv,original_labels=sd['labels'],raw_rgb=x,**t)
 return data,seeds

def fit_model(s,arm):
 p=R/'models'/s/arm
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);data,seeds=seed_data(s,arm);m=fit_density(data,3 if s=='ficus' else 2)
 if arm=='raw_rgb':
  baseline=npz(R3/'models'/s/'pooled_rgb'/'MODEL.npz')
  for k in m:np.testing.assert_array_equal(m[k],baseline[k],err_msg='r03 exact model '+k)
 np.savez_compressed(p/'MODEL.npz',**m)
 for v,x in seeds.items():np.savez_compressed(p/(v+'_SEEDS.npz'),**x)
 overlap=[[float(np.minimum(m['hist'][i],m['hist'][j]).sum()) for j in range(int(m['classes']))] for i in range(int(m['classes']))]
 js(p/'COUNT.json',dict(scene=s,arm=arm,fit_views=[DEV[s],AUX[s]],classes=int(m['classes']),seed_counts={v:np.bincount(x['labels']).tolist() for v,x in seeds.items()},seed_ineligible={v:int((~x['eligible']).sum()) for v,x in seeds.items()},histogram_overlap=overlap,semantic_GT=False));seal(p);print('MODEL',s,arm,flush=True)

def infer_arrays(s,v,arm):
 b=old(s,v,3);mask=b['inference_mask'];rgb,_,_=raw(s,v);f,e=transform(rgb[mask],arm);m=npz(R/'models'/s/arm/'MODEL.npz');K=int(m['classes']);l=np.zeros(len(f),np.uint8);q=np.zeros((len(f),K));d=q.copy()
 if e.any():l[e],q[e],d[e]=predict(m,f[e])
 return pack(mask,b['unknown']&~mask,l,q,d,e)
def infer(s,v,arm):
 p=R/'inference'/s/arm/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);a=infer_arrays(s,v,arm);b=old(s,v,3)
 if arm=='raw_rgb':
  for k in ['labels','unknown','probability','density','inference_mask','source_uv']:np.testing.assert_array_equal(a[k],b[k],err_msg='r03 exact prediction '+k)
 np.savez_compressed(p/'RESULT.npz',**a);m=a['inference_mask'];row=dict(scene=s,view=v,arm=arm,mask_pixels=int(m.sum()),counts=np.bincount(a['labels'][m],minlength=4 if s=='ficus' else 3).tolist(),unknown=int((m&(a['labels']==0)).sum()),ineligible=int((m&~a['feature_eligible']).sum()),changed_from_raw=int((m&(a['labels']!=b['labels'])).sum()),known_changed=int((m&(a['labels']>0)&(b['labels']>0)&(a['labels']!=b['labels'])).sum()));js(p/'COUNT.json',row);seal(p);print('INFER',row,flush=True)
def figure(s,v):
 p=R/'figures'/s/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);rgb,_,_=raw(s,v);ref=npz(V1/'stageA'/s/v/'REFERENCE.npz');items=[('Original cached RGB',rgb)]
 for arm in ARMS:
  a=result(s,v,arm);items.append((arm+' | fixed mask',colors(rgb,a['labels'],a['unknown'])))
 b=old(s,v);items.append(('r05 coupled graph | strong context',colors(rgb,b['labels'],b['unknown'])))
 legend='Blue pot-prior; orange wood-prior; green crown-prior; gray UNKNOWN.' if s=='ficus' else 'Blue peripheral-horizontal seed prior; orange central-nonhorizontal seed prior; gray UNKNOWN. NOT semantic foreground.'
 panel(p/'FULL.jpg',items,s+' / '+v+' | r08 scalar-intensity quotient',legend+' Diagnostic overlays only; fixed gain / native frame.',3)
 dc=npz(R7/'inference'/s/'dc_only'/v/'RESULT.npz');b=old(s,v,3);panel(p/'CONTEXT.jpg',[('Original C8 ink | frozen XRAY reference',ref['line_rgb']),('Original TRUE joint | frozen CPU EWA',ref['joint_rgb']),('r07 DC | readonly color counterfactual',colors(rgb,dc['labels'],dc['unknown']))],s+' / '+v+' | Unchanged source / C8 context','No new GS rendering, geometry, line sampling or NPR styling in r08.',3)
 if s=='ficus':
  b=npz(V2/'stageB/ficus'/v/'shared_rgb_only_k3.npz');panel(p/'RGB_STRONG.jpg',[('Original RGB',rgb),('v02 RGB-only K3 | historical strong baseline',colors(rgb,b['labels'],b['unknown'])),('r08 chromaticity | fixed seed priors',colors(rgb,result(s,v,'chromaticity')['labels'],result(s,v,'chromaticity')['unknown']))],s+' / '+v+' | Strong RGB-only comparison','Candidate colors are not semantic ground truth; original holes retained.',3)
 seal(p)
def run(s,fit=False,reserved=False):
 if fit:
  for arm in ARMS:fit_model(s,arm)
 for v in RES[s] if reserved else [DEV[s],AUX[s]]:
  guard();signal.alarm(300)
  for arm in ARMS:infer(s,v,arm)
  figure(s,v);signal.alarm(0)
def main():
 import argparse;p=argparse.ArgumentParser();p.add_argument('--phase',choices=['pilot','fit','reserved'],required=True);a=p.parse_args();status('RUN_'+a.phase,children=[os.getpid()]);failed=[]
 if a.phase=='reserved':assert (R/'reviews/03_reserved_GO.md').exists()
 for s in ['ficus'] if a.phase=='pilot' else ['ficus','scan24','scan65']:
  try:run(s,fit=a.phase!='reserved',reserved=a.phase=='reserved')
  except Exception as e:
   signal.alarm(0);failed.append(s);js(R/('ENGINEERING_'+s+'_'+a.phase+'.json'),dict(error=repr(e),traceback=traceback.format_exc()));print(traceback.format_exc(),flush=True)
 status('DONE_'+a.phase,children=[],failed=failed);raise SystemExit(bool(failed))
if __name__=='__main__':main()
