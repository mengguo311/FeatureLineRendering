from env import *
from supported import describe_supported,shift_support
from protocol import ARMS,fit_supported,predict_supported,pack_supported
import signal,traceback
def alarm(*a):raise TimeoutError('300-second unit')
signal.signal(signal.SIGALRM,alarm)
def old(s,v,which=5):
 return npz(R5/'B'/s/'withdraw_conflict'/('fit' if v in [DEV[s],AUX[s]] else v)/(v+'.npz')) if which==5 else npz(R3/'inference'/s/'pooled_rgb'/v/'RESULT.npz')
def result(s,v,arm):
 if arm in ['raw_rgb','rgb_texture']:return npz(R9/'inference'/s/arm/v/'RESULT.npz')
 return npz(R/'inference'/s/arm/v/'RESULT.npz')
def feature_arrays(s,v):
 rgb,z,alpha=raw(s,v);w=np.where(np.isfinite(alpha),np.clip(alpha,0,1),0).astype(np.float64);sw=shift_support(w);f,e,d=describe_supported(rgb,w);sf,se,sd=describe_supported(rgb,sw)
 return dict(texture=f,eligible=e,denominators=d,shifted_texture=sf,shifted_eligible=se,shifted_denominators=sd,weight=w,shifted_weight=sw)
def make_features(s,v):
 p=R/'features'/s/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);t=time.monotonic();a=feature_arrays(s,v);rgb,z,alpha=raw(s,v);mask=old(s,v,3)['inference_mask'];np.savez_compressed(p/'FEATURES.npz',**a)
 js(p/'COUNT.json',dict(scene=s,view=v,seconds=time.monotonic()-t,shape=list(rgb.shape),mask_pixels=int(mask.sum()),support_sum=float(a['weight'].sum()),alpha_invalid=int((~np.isfinite(alpha)).sum()),alpha_out_of_range=int(((alpha<0)|(alpha>1)).sum()),mask_unavailable=int((mask&~a['eligible']).sum()),shifted_mask_unavailable=int((mask&~a['shifted_eligible']).sum()),mean_alpha_in_mask=float(a['weight'][mask].mean()),mean_alpha_outside_mask=float(a['weight'][~mask].mean()) if (~mask).any() else None))
 original=npz(R9/'features'/s/v/'FEATURES.npz')['texture'];gray=lambda x:np.repeat(x[...,None],3,axis=2)
 panel(p/'FEATURES.jpg',[('Original source RGB',rgb),('Source alpha | coverage, not subject',gray(a['weight'])),('Normalized-support texture',a['texture']),('r09 unconditional texture | readonly',original),('Shifted alpha | exact mass null',gray(a['shifted_weight'])),('Finite feature support | numerical only',gray(a['eligible'].astype(float)))],s+'/'+v+' | r10 finite observation support','Original RGB/alpha remain unchanged. Features are image-coordinate proxies, NOT source geometry.',3);seal(p);print('FEATURE',s,v,flush=True)
def features(s,v,arm):
 a=npz(R/'features'/s/v/'FEATURES.npz');pre='shifted_' if arm=='shifted_alpha_texture' else '';return a[pre+'texture'],a[pre+'eligible']
def seed_data(s,arm):
 data=[];valid=[];seeds={}
 for v in [DEV[s],AUX[s]]:
  a=npz(R3/'models'/s/'pooled_rgb'/(v+'_SEEDS.npz'));uv=a['uv'];rgb,_,_=raw(s,v);f,e=features(s,v,arm);x=rgb[uv[:,1],uv[:,0]];tt=f[uv[:,1],uv[:,0]];ee=e[uv[:,1],uv[:,0]];data.append((x,tt,a['labels']));valid.append(ee);seeds[v]=dict(uv=uv,labels=a['labels'],raw_rgb=x,texture=tt,eligible=ee)
 return data,valid,seeds
def fit_model(s,arm):
 p=R/'models'/s/arm
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);data,valid,seeds=seed_data(s,arm)
 for v,a in seeds.items():np.savez_compressed(p/(v+'_SEEDS.npz'),**a)
 m=fit_supported(s,[DEV[s],AUX[s]],data,3 if s=='ficus' else 2,valid);b=npz(R9/'models'/s/'rgb_texture'/'MODEL.npz');np.testing.assert_array_equal(m['rgb_hist'],b['rgb_hist']);np.savez_compressed(p/'MODEL.npz',**m)
 js(p/'COUNT.json',dict(scene=s,arm=arm,fit_views=[DEV[s],AUX[s]],seed_counts={v:np.bincount(a['labels']).tolist() for v,a in seeds.items()},all_original_seeds_available=True,RGB_hist_exact_r09=True));seal(p);print('MODEL',s,arm,flush=True)
def infer_arrays(s,v,arm):
 b=old(s,v,3);mask=b['inference_mask'];rgb,_,_=raw(s,v);t,e=features(s,v,arm);m=npz(R/'models'/s/arm/'MODEL.npz');l,q,d=predict_supported(m,rgb[mask],t[mask],e[mask]);return pack_supported(mask,b['unknown']&~mask,l,q,d,e)
def infer(s,v,arm):
 p=R/'inference'/s/arm/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);a=infer_arrays(s,v,arm);mask=a['inference_mask'];b=result(s,v,'rgb_texture');rawref=result(s,v,'raw_rgb');np.savez_compressed(p/'RESULT.npz',**a)
 row=dict(scene=s,view=v,arm=arm,mask_pixels=int(mask.sum()),counts=np.bincount(a['labels'][mask],minlength=4 if s=='ficus' else 3).tolist(),unknown=int((mask&(a['labels']==0)).sum()),feature_unavailable=int((mask&~a['feature_eligible']).sum()),changed_from_unconditional=int((mask&(a['labels']!=b['labels'])).sum()),changed_from_raw=int((mask&(a['labels']!=rawref['labels'])).sum()));js(p/'COUNT.json',row);seal(p);print('INFER',row,flush=True)
def figure(s,v):
 p=R/'figures'/s/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);rgb,_,_=raw(s,v);items=[('Original cached RGB',rgb)]
 for arm in ['raw_rgb','rgb_texture',*ARMS]:
  a=result(s,v,arm);items.append((arm,colors(rgb,a['labels'],a['unknown'])))
 a=old(s,v);items.append(('r05 graph | readonly strong context',colors(rgb,a['labels'],a['unknown'])))
 legend='Blue pot / orange wood / green crown PROXIES.' if s=='ficus' else 'Blue peripheral-horizontal / orange central-nonhorizontal PROXIES, NOT semantic foreground.'
 panel(p/'FULL.jpg',items,s+'/'+v+' | r10 support-normalized texture',legend+' Gray UNKNOWN. Same native frame, gain and original mask. Not styled GS.',3)
 ref=npz(V1/'stageA'/s/v/'REFERENCE.npz');panel(p/'CONTEXT.jpg',[('Original C8 | readonly XRAY',ref['line_rgb']),('Original TRUE joint | readonly CPU EWA',ref['joint_rgb']),('Original source RGB',rgb)],s+'/'+v+' | Immutable C8 / source','Historical reference renders, not new r10 renders or 2D style applied to GS.',3)
 if s=='ficus':
  a=npz(V2/'stageB/ficus'/v/'shared_rgb_only_k3.npz');b=result(s,v,'alpha_texture');panel(p/'RGB_STRONG.jpg',[('Original RGB',rgb),('v02 RGB-only K3 | readonly',colors(rgb,a['labels'],a['unknown'])),('r10 alpha-supported candidate',colors(rgb,b['labels'],b['unknown']))],s+'/'+v+' | Strong RGB-only reference','No semantic GT. Full subject and leaf gaps retained.',3)
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
  try:run(s,a.phase=='reserved')
  except Exception as e:
   signal.alarm(0);failed.append(s);js(R/('ENGINEERING_'+s+'_'+a.phase+'.json'),dict(error=repr(e),traceback=traceback.format_exc()));print(traceback.format_exc(),flush=True)
 status('DONE_'+a.phase,children=[],failed=failed);raise SystemExit(bool(failed))
if __name__=='__main__':main()
