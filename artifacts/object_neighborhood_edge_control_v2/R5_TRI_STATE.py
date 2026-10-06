"""Conditional support-proxy engineering only; no old low/far TEST access."""
import sys,json,time,os
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/object_neighborhood_edge_control_v2/src'))

def classify_interval(lower,upper,epsilon,margin=1e-9):
 lower=max(0,float(lower));upper=float(upper)
 if upper+1e-8<lower:raise ValueError('invalid interval')
 state='support_far' if lower-margin>epsilon else 'support_near' if upper+margin<=epsilon else 'uncertain'
 return {'lower':lower,'upper':upper,'epsilon':epsilon,'numerical_margin':margin,'state':state,'physical_contact':None,'retain_for_high_recall':state!='support_far'}

def aabb_pairs(mu,L,labels,k=3,epsilon=.02):
 ext=k*np.sqrt(np.square(L).sum(2));radius=np.linalg.norm(ext,axis=1);tree=cKDTree(mu);pairs=[]
 for i in range(len(mu)):
  if labels[i]<=0:continue
  js=tree.query_ball_point(mu[i],radius[i]+radius.max()+epsilon)
  for j in js:
   if j>i and labels[j]>0 and labels[j]!=labels[i] and np.all(np.abs(mu[j]-mu[i])<=ext[j]+ext[i]+epsilon):pairs.append((i,j))
 return sorted(pairs)

def distance_interval(a,La,b,Lb,k=3,epsilon=.02,budget=150):
 a,b,La,Lb=[np.asarray(x,float) for x in (a,b,La,Lb)];delta=b-a;dist=float(np.linalg.norm(delta));n=delta/max(dist,1e-20);lo=max(0.,dist-k*np.linalg.norm(La.T@n)-k*np.linalg.norm(Lb.T@n));hi=dist
 if lo-1e-9>epsilon:return {**classify_interval(lo,hi,epsilon),'solver_success':True,'method':'separating-support lower bound'}
 for p in (a,b,(a+b)/2):
  if np.linalg.norm(np.linalg.solve(La,p-a))<=k and np.linalg.norm(np.linalg.solve(Lb,p-b))<=k:return {**classify_interval(0,0,epsilon),'solver_success':True,'method':'feasible shared point'}
 scale=max(dist,k*np.linalg.norm(La),k*np.linalg.norm(Lb),1e-8);d=delta/scale;A=La*k/scale;B=Lb*k/scale
 def project(x):
  z=x.reshape(2,3);return (z/np.maximum(np.linalg.norm(z,axis=1,keepdims=True),1)).ravel()
 def objective(x):r=d+B@x[3:]-A@x[:3];return r@r
 def gradient(x):r=d+B@x[3:]-A@x[:3];return 2*np.r_[-A.T@r,B.T@r]
 r=minimize(objective,np.zeros(6),jac=gradient,method='SLSQP',constraints=[{'type':'ineq','fun':lambda x:1-x[:3]@x[:3]},{'type':'ineq','fun':lambda x:1-x[3:]@x[3:]}],options={'ftol':1e-12,'maxiter':budget})
 x=project(r.x);diff=d+B@x[3:]-A@x[:3];hi=float(np.linalg.norm(diff));n=diff/max(hi,1e-20);lo=max(0,float(n@d-np.linalg.norm(A.T@n)-np.linalg.norm(B.T@n)))
 # Explicit finite projected fallback; straddling threshold remains uncertain, never raises merely for budget exhaustion.
 if lo*scale<=epsilon<hi*scale:
  step=1/(2*np.linalg.norm(np.concatenate([A,-B],axis=1),2)**2+1e-20)
  for _ in range(300):x=project(x-step*gradient(x))
  diff=d+B@x[3:]-A@x[:3];hi=float(np.linalg.norm(diff));n=diff/max(hi,1e-20);lo=max(0,float(n@d-np.linalg.norm(A.T@n)-np.linalg.norm(B.T@n)))
 return {**classify_interval(lo*scale,hi*scale,epsilon),'solver_success':bool(r.success),'method':'feasible point upper + separating support lower; limited SLSQP/projected budget'}

def main():
 from runtime import OUT,ART,atomic_json,sha,result
 frozen=json.loads((ART/'R5_FREEZE.json').read_text());assert sha(__file__)==frozen['script_sha256']
 core=json.loads((ART/'FINAL.json').read_text());cov=json.loads((ART/'results/O_cov.json').read_text());probe=ART/'results/R4_known_scale.json';p=json.loads(probe.read_text()) if probe.exists() else None
 base=json.loads((ART/'results/R0.json').read_text());potential=1-cov['metrics']['summary']['dev-out']['edge_mse_linear']/base['metrics']['summary']['dev-out']['edge_mse_linear'];probe_potential=p and p['perturb_valid'] and p['relative_improvement']>=.5
 if potential<.1 and not probe_potential:
  result('R5',{'status':'CONDITIONAL_NOT_RUN','reason':'neither natural nor known-UID scale control shows predeclared useful potential; implementation math tests only, no selector benchmark'});return
 import torch
 from data import CHECKPOINT,IDENTITY,LABELS
 cap,_=torch.load(CHECKPOINT,map_location='cpu');mu=cap[1].detach().numpy();sc=cap[4].detach().exp().numpy();q=cap[5].detach().numpy();q/=np.linalg.norm(q,axis=1,keepdims=True);w,x,y,z=q.T
 R=np.empty((len(q),3,3));R[:,0,0]=1-2*(y*y+z*z);R[:,0,1]=2*(x*y-w*z);R[:,0,2]=2*(x*z+w*y);R[:,1,0]=2*(x*y+w*z);R[:,1,1]=1-2*(x*x+z*z);R[:,1,2]=2*(y*z-w*x);R[:,2,0]=2*(x*z-w*y);R[:,2,1]=2*(y*z+w*x);R[:,2,2]=1-2*(x*x+y*y);L=R*sc[:,None,:]
 ids=json.loads(IDENTITY.read_text());labels=np.asarray(ids['label']);mass=np.load(LABELS)['band_mass'];reliable=np.flatnonzero(labels>0);large=np.argsort(-np.linalg.norm(3*np.sqrt((L*L).sum(2)),axis=1));chosen=np.unique(np.r_[np.argsort(-mass)[:32],[i for i in large if labels[i]>0][:32]])
 m,ell,lab=mu[chosen],L[chosen],labels[chosen];start=time.monotonic();pairs=aabb_pairs(m,ell,lab,3,.02);query=time.monotonic()-start;rows=[];start=time.monotonic()
 for i,j in pairs:rows.append({'uid_a':ids['uid'][int(chosen[i])],'uid_b':ids['uid'][int(chosen[j])],**distance_interval(m[i],ell[i],m[j],ell[j],3,.02)})
 solve=time.monotonic()-start;counts={k:sum(x['state']==k for x in rows) for k in ('support_near','support_far','uncertain')}
 semantic=[
  {'case':'true_contact_planes','surface_GT_distance':0.,'surface_relation':'contact_GT','surface_definition':{'A':{'z':0.,'x':[-1,0],'y':[-.8,.8]},'B':{'z':0.,'x':[0,1],'y':[-.8,.8]}},'support':distance_interval([-.25,0,0],np.eye(3)*.1,[.25,0,0],np.eye(3)*.1,3,.02)},
  {'case':'near_noncontact','surface_GT_distance':.03,'surface_relation':'near_noncontact','surface_definition':{'A':{'z':0.,'x':[-1,0],'y':[-.8,.8]},'B':{'z':0.,'x':[.03,1.03],'y':[-.8,.8]}},'support':distance_interval([-.3,0,0],np.eye(3)*.1,[.33,0,0],np.eye(3)*.1,3,.02)},
  {'case':'far_surfaces_large_support_proxy','surface_GT_distance':3.,'surface_relation':'separated_GT','surface_definition':{'A':{'z':0.,'x':[-1,1],'y':[-.8,.8]},'B':{'z':-3.,'x':[-1,1],'y':[-.8,.8]}},'support':distance_interval([0,0,0],np.eye(3),[0,0,-3],np.eye(3),3,.02)}]

 out={'status':'COMPLETED_DIAGNOSTIC_SUBSET','trigger':'known-UID scale recovery >=50% or natural O_cov dev improvement >=10%','original_epsilon_preserved':.02,'straddling_original_interval':classify_interval(.0199949668,.0200196488,.02),'predeclared_subset_rule':'top32 original training band mass union top32 support extents with positive labels; not full selector or formal benchmark','subset_N':len(chosen),'actual_pairs':len(pairs),'counts':counts,'query_seconds':query,'bounds_solve_seconds':solve,'rows':rows,'semantic_cases':semantic,'oracle_contact_epsilon':.001,'oracle_near_epsilon':.05,'semantic_note':'analytic proxy examples, not image experiments or measured physical contact; large Gaussian supports can connect truly separated surfaces','unknown_label_policy':'excluded from cross-object decisions, preserved unknown; near union uncertain is high-recall candidate only','full_selection_cost':'not rerun 10659-Gaussian selector; historical C1=404.5s remains full cost reference','no_old_low_far_test_reads':True}
 result('R5',out);identity={'script_sha256':sha(__file__),'base_checkpoint_sha256':sha(CHECKPOINT),'labels_sha256':sha(LABELS),'trigger_result_sha256':sha(probe) if probe_potential else sha(ART/'results/O_cov.json')};atomic_json(OUT/'seals/R5.json',{'unit':'R5','status':'COMPLETED','identity':identity,'outputs':{str((ART/'results/R5.json').relative_to(ROOT)):sha(ART/'results/R5.json')}});print(json.dumps({'R5':out['status'],'subset_N':len(chosen),'pairs':len(pairs),'counts':counts},indent=2))
if __name__=='__main__':main()
