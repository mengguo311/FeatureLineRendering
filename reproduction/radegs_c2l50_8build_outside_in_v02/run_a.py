from env import *
from anchor import *
import signal,traceback
def timeout(*a):raise TimeoutError('unit 900s')
signal.signal(signal.SIGALRM,timeout)
def scene(s,phase):
 p=ROOT/'stageA'/s;p.mkdir(parents=True,exist_ok=True)
 if phase=='fit':
  f=p/'model';f.mkdir(exist_ok=True)
  if (f/'SEAL.json').exists():checkseal(f);model=json.loads((f/'MODEL.json').read_text())
  else:
   t=time.monotonic();signal.alarm(900);a=[raw(s,v)[2] for v in [DEV[s],AUX[s]]];ss=samples(s,[DEV[s],AUX[s]]);isolate=isolated_coverage(a)
   m=None if isolate else fit_support_plane(ss['world'],ss['pixel_scale'],ss['view_id'],ss['peripheral'],ss['central'])
   model=dict(scene=s,mode='isolated_coverage_proxy' if isolate else 'joint_support_plane_proxy' if m is not None else 'REFUSED',plane=m,fit_views=[DEV[s],AUX[s]],seconds=time.monotonic()-t)
   np.savez_compressed(f/'FIT_SAMPLES.npz',**ss);js(f/'MODEL.json',model);signal.alarm(0);seal(f);print(s,model,flush=True)
 else:model=json.loads((p/'model/MODEL.json').read_text())
 vs=[DEV[s],AUX[s]] if phase=='fit' else RES[s]
 for v in vs:
  guard();q=p/v
  if (q/'SEAL.json').exists():checkseal(q);continue
  q.mkdir(exist_ok=True);signal.alarm(900);rgb,z,a=raw(s,v);c=cam(s,v);old=npz(V1/'stageA'/s/v/'SUBJECT.npz');ref=npz(V1/'stageA'/s/v/'REFERENCE.npz')
  if model['mode']=='isolated_coverage_proxy':m,u=coverage_mask(z,a)
  elif model['mode']=='joint_support_plane_proxy':m,u=plane_mask(z,a,c,model['plane'])
  else:m=np.zeros(z.shape,bool);u=a>=.1
  np.savez_compressed(q/'SUBJECT.npz',candidate=m,unknown=u)
  js(q/'COUNT.json',dict(scene=s,view=v,candidate_pixels=int(m.sum()),unknown_pixels=int(u.sum()),candidate_fraction=float(m.mean()),mode=model['mode'],source_reference_reused_readonly=True,not_semantic_GT=True))
  panel(q/'COMPARISON.jpg',[('Original frozen source RGB',rgb),('v01 subject + uncertainty (unchanged)',overlay(rgb,old['candidate'],old['unknown'])),('v02 shared-depth subject + UNKNOWN',overlay(rgb,m,u)),('Original C8 ink | XRAY (read-only)',ref['line_rgb']),('Original TRUE joint | CPU approximation',ref['joint_rgb']),('v02 scope / white candidate, grey UNKNOWN',grey(np.where(u,.45,m.astype(float))))],s+' / '+v+' | Stage A v01 versus v02','v02 uses joint DEV+AUX depth samples; no C8 input. Colors: green subject / orange unknown. NOT semantic GT.',3)
  panel(q/'CONTROLS.jpg',[('Original RGB',rgb),('Whole-scene alpha >= .5 / NOT subject GT',overlay(rgb,a>=.5)),('v01 RGB-only background contrast',overlay(rgb,old['rgb_alpha_control'])),('v02 depth-anchored proposal',overlay(rgb,m,u))],s+' / '+v+' | Subject controls','All native pixels retained in candidate/background/unknown. No hole filling or largest-component selection.',2)
  signal.alarm(0);seal(q);print('A_VIEW',s,v,int(m.sum()),flush=True)
 if phase=='reserved':
  t=p/'transfer';t.mkdir(exist_ok=True)
  rows=[]
  for v,tv in [(DEV[s],AUX[s]),(AUX[s],DEV[s]),(DEV[s],RES[s][0]),(DEV[s],RES[s][1])]:
   m=npz(p/v/'SUBJECT.npz')['candidate'];tm=npz(p/tv/'SUBJECT.npz')['candidate'];row,ar=directed_overlap(s,v,tv,m,tm);row.update(source=v,target=tv);rows.append(row);np.savez_compressed(t/(v+'__'+tv+'.npz'),**ar)
  js(t/'COUNTS.json',rows);seal(t)
def main():
 import argparse;p=argparse.ArgumentParser();p.add_argument('--phase',choices=['fit','reserved'],required=True);a=p.parse_args();state('STAGE_A_'+a.phase.upper(),children=[os.getpid()]);fail=[]
 for s in SCENES:
  try:scene(s,a.phase)
  except Exception as e:
   signal.alarm(0);d=dict(scene=s,error=repr(e),traceback=traceback.format_exc());js(ROOT/f'ENGINEERING_FAILURE_A_{a.phase}_{s}.json',d);fail.append(s);print(d,flush=True)
 state('STAGE_A_'+a.phase.upper()+'_DONE',children=[],failures=fail);raise SystemExit(bool(fail))
if __name__=='__main__':main()
