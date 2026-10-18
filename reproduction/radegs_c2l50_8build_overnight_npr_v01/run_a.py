from env import *
from upright import *
import signal,traceback
def timeout(*a):raise TimeoutError('unit limit900s')
signal.signal(signal.SIGALRM,timeout)
def infer_scene(s):
 rr=np.asarray([c['extrinsic'] for c in reg()[s]['cameras'] if c['view'] in reg()[s]['build_views']])[:,:3,:3];axis=infer_up(rr[:,0],-rr[:,1]);old=json.loads((V2/'stageA'/s/'model/MODEL.json').read_text());data=npz(V2/'stageA'/s/'model/FIT_SAMPLES.npz');m=None
 if old['mode']=='isolated_coverage_proxy':mode='isolated_coverage_proxy'
 elif axis['qualified']:m=fit_support(data['world'],data['pixel_scale'],data['view_id'],data['peripheral'],data['central'],axis['up']);mode='upright_support_plane' if m else 'UNKNOWN_no_qualified_plane'
 else:mode='UNKNOWN_no_qualified_axis'
 return dict(scene=s,axis=axis,plane=m,mode=mode,fit_views=[DEV[s],AUX[s]],source_samples_readonly=str(V2/'stageA'/s/'model/FIT_SAMPLES.npz'))
def predict(s,v,m):
 _,z,a=raw(s,v);valid=np.isfinite(z)&(z>.2)&(a>=.5);u=(a>=.1)&~valid;mask=np.zeros_like(valid);distance=np.full(z.shape,np.nan,np.float32)
 if m['mode']=='isolated_coverage_proxy':mask=valid.copy()
 elif m['plane']:
  y,x=np.nonzero(valid);uv=np.c_[x,y];c=cam(s,v);X=unproject(uv,z[y,x],c);p=z[y,x]/np.sqrt(c['fx']*c['fy']);lab=plane_labels(X,p,m['plane']);mask[y,x]=lab==1;u[y,x]=lab==-1;distance[y,x]=(X@np.asarray(m['plane']['normal'])+m['plane']['offset'])/p
 else:u=a>=.1
 return dict(candidate=mask,unknown=u,signed_plane_distance_p=distance)
def scene(s,phase):
 p=R/'A'/s/'model';p.mkdir(parents=True,exist_ok=True)
 if (p/'SEAL.json').exists():checkseal(p);m=json.loads((p/'MODEL.json').read_text())
 else:
  signal.alarm(900);m=infer_scene(s);js(p/'MODEL.json',m);seal(p);signal.alarm(0)
 for v in ([DEV[s],AUX[s]] if phase=='fit' else RES[s]):
  guard();q=R/'A'/s/v
  if (q/'SEAL.json').exists():checkseal(q);continue
  q.mkdir(parents=True);signal.alarm(900);ar=predict(s,v,m);np.savez_compressed(q/'SUBJECT.npz',**ar);rgb,z,a=raw(s,v);old=npz(V2/'stageA'/s/v/'SUBJECT.npz');ref=npz(V1/'stageA'/s/v/'REFERENCE.npz')
  panel(q/'FULL.jpg',[('Original source RGB',rgb),('Original C8 line | XRAY',ref['line_rgb']),('TRUE joint source + C8 | frozen CPU reference',ref['joint_rgb']),('v02 unconstrained support / UNKNOWN',overlay(rgb,old['candidate'],old['unknown'])),('r01 upright-qualified support / UNKNOWN',overlay(rgb,ar['candidate'],ar['unknown'])),('r01 mask: white candidate / grey UNKNOWN',np.repeat(np.where(ar['unknown'],.45,ar['candidate'])[...,None],3,2))],s+' / '+v+' | r01 subject identity test','Green candidate; orange UNKNOWN. No morphology, line input, color clustering or scene-specific threshold.',3)
  js(q/'COUNT.json',dict(scene=s,view=v,mode=m['mode'],candidate_pixels=int(ar['candidate'].sum()),unknown_pixels=int(ar['unknown'].sum()),changed_from_v02=int(np.count_nonzero(ar['candidate']!=old['candidate']))));seal(q);signal.alarm(0);print(s,v,m['mode'],int(ar['candidate'].sum()),flush=True)
def main():
 import argparse;p=argparse.ArgumentParser();p.add_argument('--phase',choices=['fit','reserved'],required=True);args=p.parse_args();status('A_'+args.phase,children=[os.getpid()]);fail=[]
 for s in SCENES:
  try:scene(s,args.phase)
  except Exception as e:signal.alarm(0);fail.append(s);js(R/('ENGINEERING_A_'+args.phase+'_'+s+'.json'),dict(error=repr(e),traceback=traceback.format_exc()))
 status('A_'+args.phase+'_DONE',children=[],failed_scenes=fail);raise SystemExit(bool(fail))
if __name__=='__main__':main()
