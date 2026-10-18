from env import *
from harmonic import solve,labels,edge_weight
from geometry import correspond,local_edges
from scipy.ndimage import distance_transform_edt
import signal,traceback
ARMS=['joint_rgb','independent_rgb','joint_no_rgb']
def timeout(*a):raise TimeoutError('900s sealed-unit limit')
signal.signal(signal.SIGALRM,timeout)
def seed_labels(h,d,m,cap=2048):
 bounds=np.r_[0,m['cuts'],m['bins']]/m['bins']*(m['height_hi']-m['height_lo'])+m['height_lo'];lab=np.zeros(len(h),np.uint8)
 for k,(lo,hi) in enumerate(zip(bounds[:-1],bounds[1:]),1):
  ids=np.flatnonzero((h>=lo+.25*(hi-lo))&(h<=hi-.25*(hi-lo))&(d>=2));ids=ids[np.linspace(0,len(ids)-1,min(len(ids),cap),dtype=int)] if len(ids) else ids;lab[ids]=k
 return lab
def combine_priors(n,ids,q,w):
 g=np.bincount(ids,weights=w,minlength=n);p=np.zeros((n,3));
 for k in range(3):p[:,k]=np.bincount(ids,weights=w*q[:,k],minlength=n)
 ok=g>0;p[ok]/=g[ok,None];return g,p
def load_view(v,seed=False):
 rgb,z,a=raw('ficus',v);c=cam('ficus',v);sub=npz(R1/'A/ficus'/v/'SUBJECT.npz');mask=sub['candidate'];y,x=np.nonzero(mask);uv=np.c_[x,y];X=unproject(uv,z[y,x],c);p=z[y,x]/np.sqrt(c['fx']*c['fy']);ids=np.full(z.shape,-1,int);ids[mask]=np.arange(len(X));sl=np.zeros(len(X),np.uint8)
 if seed:
  m=json.loads((R1/'B/ficus/model/MODEL.json').read_text());sl=seed_labels(X@np.asarray(m['up']),distance_transform_edt(mask)[y,x],m)
 i,j,d=local_edges(mask,X,p)
 return dict(view=v,rgb=rgb,z=z,alpha=a,camera=c,mask=mask,subject_unknown=sub['unknown'],uv=uv,world=X,p=p,ids=ids,color=rgb[y,x],seeds=sl,i=i,j=j,d=d)
def links(a,b):
 state,q=correspond(a['world'],a['uv'],a['camera'],b['camera'],b['z'],b['alpha']);i=np.flatnonzero(state==1);j=b['ids'][q[i,1],q[i,0]];ok=j>=0;i=i[ok];j=j[ok];return i,j,state
def build_graph(data,arm):
 n=sum(len(x['world']) for x in data);color=arm!='joint_no_rgb';i=[];j=[];w=[];offset=0;meta=[];cross=0
 for x in data:
  i.append(x['i']+offset);j.append(x['j']+offset);w.append(edge_weight(x['color'][x['i']],x['color'][x['j']],x['d'],color));offset+=len(x['world'])
 if arm!='independent_rgb':
  ab,bb,sa=links(data[0],data[1]);ba,aa,sb=links(data[1],data[0]);pairs=np.unique(np.r_[np.c_[ab,bb],np.c_[aa,ba]],axis=0);a,b=pairs.T;deg_a=np.bincount(a,minlength=len(data[0]['world']));deg_b=np.bincount(b,minlength=len(data[1]['world']));ww=.5*edge_weight(data[0]['color'][a],data[1]['color'][b],np.ones(len(a)),color)/np.maximum(deg_a[a],deg_b[b]);i.append(a);j.append(b+len(data[0]['world']));w.append(ww);cross=len(a);meta=[np.bincount(sa,minlength=6).tolist(),np.bincount(sb,minlength=6).tolist()]
 return np.concatenate(i),np.concatenate(j),np.concatenate(w),dict(cross_edges=cross,correspondence_states=meta,nodes=n)
def save_result(p,v,arm,q,data,meta,extra=None):
 lab=np.zeros(data['mask'].shape,np.uint8);lab[data['mask']]=labels(q);prob=np.zeros((*lab.shape,3),np.float64);prob[data['mask']]=q;seed=np.zeros(lab.shape,np.uint8);seed[data['mask']]=data['seeds'];unknown=(data['mask']&(lab==0))|data['subject_unknown'];np.savez_compressed(p/(v+'.npz'),labels=lab,unknown=unknown,probability=prob,seeds=seed,source_uv=data['uv'],**(extra or {}))
 row=dict(view=v,arm=arm,subject_pixels=int(data['mask'].sum()),label_counts=np.bincount(lab.ravel(),minlength=4).tolist(),unknown_subject=int((data['mask']&(lab==0)).sum()),seed_counts=np.bincount(data['seeds'],minlength=4).tolist(),solver=meta);js(p/(v+'_COUNT.json'),row);return row
def fit(arm):
 p=R/'B'/arm/'fit'
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);signal.alarm(900);t=time.monotonic();data=[load_view(v,True) for v in [DEV['ficus'],AUX['ficus']]];i,j,w,gm=build_graph(data,arm);seed=np.concatenate([x['seeds'] for x in data]);q,meta=solve(len(seed),i,j,w,seed);meta.update(gm);meta['seconds']=time.monotonic()-t;np.savez_compressed(p/'GRAPH.npz',i=i,j=j,weight=w,seeds=seed,probability=q,view_offsets=np.r_[0,np.cumsum([len(x['seeds']) for x in data])]);pos=0
 for x in data:save_result(p,x['view'],arm,q[pos:pos+len(x['seeds'])],x,meta);pos+=len(x['seeds'])
 js(p/'MODEL.json',meta);seal(p);signal.alarm(0);print('FIT',arm,meta,flush=True)
def infer_target(v,arm):
 p=R/'B'/arm/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);signal.alarm(900);t=time.monotonic();target=load_view(v,False);n=len(target['world']);color=arm!='joint_no_rgb';ids=[];qs=[];ws=[];states=[]
 for bv in [DEV['ficus'],AUX['ficus']]:
  b=load_view(bv,False);saved=npz(R/'B'/arm/'fit'/(bv+'.npz'));q=saved['probability'][b['mask']];i,j,state=links(target,b);known=labels(q[j])>0;i=i[known];j=j[known];w=.5*edge_weight(target['color'][i],b['color'][j],np.ones(len(i)),color);ids.append(i);qs.append(q[j]);ws.append(w);states.append(dict(source=bv,state_counts=np.bincount(state,minlength=6).tolist(),qualified_prior_edges=len(i)))
 ii=np.concatenate(ids);qq=np.concatenate(qs);ww=np.concatenate(ws);degree=np.bincount(ii,minlength=n);ww/=np.maximum(degree[ii],1);gamma,prior=combine_priors(n,ii,qq,ww);i,j,d=target['i'],target['j'],target['d'];weight=edge_weight(target['color'][i],target['color'][j],d,color);q,meta=solve(n,i,j,weight,target['seeds'],gamma,prior);meta.update(seconds=time.monotonic()-t,prior_nodes=int((gamma>0).sum()),correspondence=states,target_height_seeds=0,build_frozen=True);save_result(p,v,arm,q,target,meta,dict(prior_gamma=gamma,prior_probability=prior));js(p/'MODEL.json',meta);seal(p);signal.alarm(0);print('TARGET',arm,v,meta,flush=True)
def view_result(v,arm):return npz(R/'B'/arm/('fit' if v in [DEV['ficus'],AUX['ficus']] else v)/(v+'.npz'))
def figures(v):
 p=R/'figures/ficus'/v
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(parents=True,exist_ok=True);rgb,_,_=raw('ficus',v);ref=npz(V1/'stageA/ficus'/v/'REFERENCE.npz');old=npz(R1/'B/ficus'/v/'profile.npz');nowdata=view_result(v,'joint_rgb');items=[('Source RGB',rgb),('Original C8 line | XRAY reference',ref['line_rgb']),('True joint GS | frozen CPU reference',ref['joint_rgb']),('r01 fixed axial labels',colors(rgb,old['labels'],old['unknown'])),('r02 multiview seeded propagation',colors(rgb,nowdata['labels'],nowdata['unknown'])),('r02 confidence | grey UNKNOWN',np.repeat(nowdata['probability'].max(2)[...,None],3,2))];panel(p/'FULL.jpg',items,'Ficus / '+v+' | r02 boundary propagation','Blue lower/pot candidate; orange middle/trunk candidate; green crown candidate. Diagnostic colors, not semantic GT or edited GS.',3)
 items=[('Source RGB',rgb),('r01 profile',colors(rgb,old['labels'],old['unknown']))]
 for arm in ARMS:
  a=view_result(v,arm);items.append((arm,colors(rgb,a['labels'],a['unknown'])))
 v2=npz(V2/'stageB/ficus'/v/'shared_rgb_only_k3.npz');items.append(('v02 shared RGB-only K3 | strong old control',colors(rgb,v2['labels'],v2['unknown'])));panel(p/'CONTROLS.jpg',items,'Ficus / '+v+' | Frozen controls','Identical native RGB/depth/mask. Build seeds and local graph budget matched; independent_rgb removes build cross-view coupling.',3)
 if v in [DEV['ficus'],AUX['ficus']]:panel(p/'SEEDS.jpg',[('Original source',rgb),('Frozen seed interiors | blank is unseeded',colors(rgb,nowdata['seeds'],np.zeros(rgb.shape[:2],bool))),('r02 main',colors(rgb,nowdata['labels'],nowdata['unknown']))],'Ficus / '+v+' | Automatic coarse seeds, not GT','r01 segment central 50%, alpha-edge distance >=2px, <=2048 per region/view. No new manual seed.',3)
 seal(p)
def main():
 import argparse;p=argparse.ArgumentParser();p.add_argument('--phase',choices=['fit','reserved'],required=True);a=p.parse_args();status('B_'+a.phase,children=[os.getpid()]);failed=[]
 for arm in ARMS:
  try:
   guard()
   if a.phase=='fit':fit(arm)
   else:
    for v in RES['ficus']:infer_target(v,arm)
  except Exception as e:signal.alarm(0);failed.append(arm);js(R/('ENGINEERING_'+a.phase+'_'+arm+'.json'),dict(error=repr(e),traceback=traceback.format_exc()))
 if not failed:
  for v in ([DEV['ficus'],AUX['ficus']] if a.phase=='fit' else RES['ficus']):figures(v)
 status('B_'+a.phase+'_DONE',children=[],failed=failed);raise SystemExit(bool(failed))
if __name__=='__main__':main()
