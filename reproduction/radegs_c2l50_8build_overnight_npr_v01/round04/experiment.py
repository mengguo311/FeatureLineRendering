from env import *
from graph import load,links,build_graph,transfer_priors
from coupling import solve_graph,unary_prior,combine_priors,labels,edge_weight
from output import pack
import signal,traceback
ARMS=['coupled','no_cross','geometry_pair','unary_seeded']
def timeout(*a):raise TimeoutError('900 second unit deadline')
signal.signal(signal.SIGALRM,timeout)
def result(s,v,arm):return npz(R/'B'/s/arm/('fit' if v in [DEV[s],AUX[s]] else v)/(v+'.npz'))
def infer_arrays(data,arm):
 i,j,w,gm=build_graph(data,arm);n=sum(len(x['world']) for x in data);degree=np.bincount(np.r_[i,j],weights=np.r_[w,w],minlength=n);seeds=np.concatenate([x['seeds'] for x in data]);prior=np.concatenate([x['unary'] for x in data]);accepted=np.concatenate([x['accepted'] for x in data]);gamma,u=unary_prior(prior,accepted,degree);q,meta=solve_graph(n,i,j,w,seeds,gamma,u);meta.update(gm)
 return dict(i=i,j=j,weight=w,seeds=seeds,probability=q,gamma=gamma,prior=u,view_offsets=np.r_[0,np.cumsum([len(x['world']) for x in data])]),meta

def save_view(p,s,v,arm,q,data,meta,extra=None):
 ar=pack(q,data);ar.update(extra or {});np.savez_compressed(p/(v+'.npz'),**ar);lab=ar['labels'];base=npz(R3/'inference'/s/'pooled_rgb'/v/'RESULT.npz');m=data['mask'];both=m&(base['labels']>0)&(lab>0);seed=data['seeds'];unarylab=labels(data['unary']);row=dict(scene=s,view=v,arm=arm,subject_or_scene_valid_pixels=int(m.sum()),unknown_eligible=int((m&(lab==0)).sum()),label_counts=np.bincount(lab[m],minlength=q.shape[1]+1).tolist(),old_r03_unknown_now_known=int((m&(base['labels']==0)&(lab>0)).sum()),old_r03_known_now_unknown=int((m&(base['labels']>0)&(lab==0)).sum()),old_r03_known_both_changed=int((both&(base['labels']!=lab)).sum()),hard_seed_count=int((seed>0).sum()),hard_seed_conflicts_with_accepted_appearance=int(((seed>0)&data['accepted']&(seed!=unarylab)).sum()),solver=meta)
 js(p/(v+'_COUNT.json'),row);return row

def fit(s,arm):
 p=R/'B'/s/arm/'fit'
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);signal.alarm(900);t=time.monotonic();data=[load(s,v,True) for v in [DEV[s],AUX[s]]];ar,meta=infer_arrays(data,arm);meta['seconds']=time.monotonic()-t;np.savez_compressed(p/'GRAPH.npz',**ar);pos=0
 for d in data:save_view(p,s,d['view'],arm,ar['probability'][pos:pos+len(d['world'])],d,meta);pos+=len(d['world'])
 js(p/'MODEL.json',meta);seal(p);signal.alarm(0);print('FIT',s,arm,meta,flush=True)

def target_arrays(s,v,arm):
 d=load(s,v,False);n=len(d['world']);K=d['unary'].shape[1];i,j,w,gm=build_graph([d],arm);degree=np.bincount(np.r_[i,j],weights=np.r_[w,w],minlength=n);ga,pa=unary_prior(d['unary'],d['accepted'],degree);gb=np.zeros(n);pb=np.zeros((n,K));states=[]
 if arm!='unary_seeded':
  ids=[];qs=[];ws=[]
  for bv in [DEV[s],AUX[s]]:
   b=load(s,bv,False);q=result(s,bv,arm)['probability'][b['mask']];ii,jj,state=links(d,b);known=labels(q[jj])>0;ii=ii[known];jj=jj[known];ww=.5*edge_weight(d['color'][ii],b['color'][jj],np.ones(len(ii)),arm!='geometry_pair');ids.append(ii);qs.append(q[jj]);ws.append(ww);states.append(dict(view=bv,state_counts=np.bincount(state,minlength=6).tolist(),qualified_known_prior_edges=len(ii)))
  gb,pb=transfer_priors(n,np.concatenate(ids),np.concatenate(qs),np.concatenate(ws),K)
 g,p=combine_priors(ga,pa,gb,pb);q,meta=solve_graph(n,i,j,w,d['seeds'],g,p);meta.update(gm);meta.update(appearance_prior_nodes=int((ga>0).sum()),projection_prior_nodes=int((gb>0).sum()),correspondence=states,target_height_seeds=0)
 return q,d,meta,dict(appearance_gamma=ga,projection_gamma=gb,combined_prior=p,combined_gamma=g)

def target(s,v,arm):
 p=R/'B'/s/arm/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);signal.alarm(900);t=time.monotonic();q,d,meta,ar=target_arrays(s,v,arm);meta['seconds']=time.monotonic()-t;save_view(p,s,v,arm,q,d,meta,ar);js(p/'MODEL.json',meta);seal(p);signal.alarm(0);print('TARGET',s,v,arm,meta,flush=True)

def figures(s,v):
 p=R/'figures'/s/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);rgb,_,_=raw(s,v);ref=npz(V1/'stageA'/s/v/'REFERENCE.npz');old=npz(R3/'inference'/s/'pooled_rgb'/v/'RESULT.npz');now=result(s,v,'coupled');legend='Ficus: blue pot-prior / orange wood-prior / green crown-prior. DTU: blue peripheral / orange central appearance. Gray UNKNOWN; NOT semantic GT.'
 panel(p/'FULL.jpg',[('Original source RGB',rgb),('Original C8 line | XRAY reference',ref['line_rgb']),('TRUE joint GS | frozen CPU reference',ref['joint_rgb']),('r03 pure conditional appearance',colors(rgb,old['labels'],old['unknown'])),('r04 coupled unary + qualified graph',colors(rgb,now['labels'],now['unknown'])),('r04 confidence | not semantic probability',np.repeat(now['probability'].max(2)[...,None],3,2))],s+' / '+v+' | r04 complementary evidence',legend,3)
 items=[('Original source RGB',rgb),('r03 pure appearance',colors(rgb,old['labels'],old['unknown']))]
 for arm in ARMS:
  x=result(s,v,arm);items.append((arm,colors(rgb,x['labels'],x['unknown'])))
 panel(p/'CONTROLS.jpg',items,s+' / '+v+' | Fixed four arms',legend+' geometry_pair still uses appearance unary. unary_seeded is the matched seed-only control.',3)
 if s=='ficus':
  r2=npz(R2/'B/joint_rgb'/('fit' if v in [DEV[s],AUX[s]] else v)/(v+'.npz'));v2=npz(V2/'stageB/ficus'/v/'shared_rgb_only_k3.npz');panel(p/'MECHANISMS.jpg',[('Source RGB',rgb),('v02 RGB-only K3',colors(rgb,v2['labels'],v2['unknown'])),('r02 pure seeded propagation',colors(rgb,r2['labels'],r2['unknown'])),('r03 pure appearance',colors(rgb,old['labels'],old['unknown'])),('r04 combined',colors(rgb,now['labels'],now['unknown'])),('r04 no pairwise color',colors(rgb,result(s,v,'geometry_pair')['labels'],result(s,v,'geometry_pair')['unknown']))],v+' | New coupling versus standalone mechanisms',legend,3)
 seal(p)

def main():
 import argparse;p=argparse.ArgumentParser();p.add_argument('--phase',choices=['fit','reserved'],required=True);p.add_argument('--scene',choices=SCENES+['all'],default='all');a=p.parse_args();scenes=SCENES if a.scene=='all' else [a.scene];status(a.phase.upper(),children=[os.getpid()],scenes=scenes);fail=[]
 for s in scenes:
  try:
   guard()
   for arm in ARMS:
    if a.phase=='fit':fit(s,arm)
    else:
     for v in RES[s]:target(s,v,arm)
   for v in ([DEV[s],AUX[s]] if a.phase=='fit' else RES[s]):figures(s,v)
  except Exception as e:signal.alarm(0);fail.append(s);js(R/('ENGINEERING_'+a.phase+'_'+s+'.json'),dict(error=repr(e),traceback=traceback.format_exc()))
 status(a.phase.upper()+'_DONE',children=[],failed=fail);raise SystemExit(bool(fail))
if __name__=='__main__':main()
