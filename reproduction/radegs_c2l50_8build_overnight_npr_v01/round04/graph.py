from env import *
from geometry import correspond,local_edges
from coupling import edge_weight

def view_seed_policy(seed,is_build):return np.asarray(seed).copy() if is_build else np.zeros_like(seed)
def load(s,v,seed=False):
 rgb,z,a=raw(s,v);base=npz(R3/'inference'/s/'pooled_rgb'/v/'RESULT.npz');mask=base['inference_mask'];y,x=np.nonzero(mask);uv=np.c_[x,y];c=cam(s,v);X=unproject(uv,z[y,x],c);p=z[y,x]/np.sqrt(c['fx']*c['fy']);ids=np.full(z.shape,-1,np.int64);ids[mask]=np.arange(len(X));sl=np.zeros(len(X),np.uint8)
 if seed:sl=npz(R3/'models'/s/'pooled_rgb'/(v+'_SEEDS.npz'))['seed_image'][mask]
 i,j,d=local_edges(mask,X,p)
 return dict(scene=s,view=v,rgb=rgb,z=z,alpha=a,camera=c,mask=mask,subject_unknown=base['unknown']&~mask,uv=uv,world=X,p=p,ids=ids,color=rgb[y,x],seeds=sl,i=i,j=j,d=d,unary=base['probability'][mask],accepted=base['labels'][mask]>0)

def links(a,b):
 state,q=correspond(a['world'],a['uv'],a['camera'],b['camera'],b['z'],b['alpha']);i=np.flatnonzero(state==1);j=b['ids'][q[i,1],q[i,0]];ok=j>=0;return i[ok],j[ok],state

def build_graph(data,arm):
 n=sum(len(x['world']) for x in data);color=arm!='geometry_pair';i=[];j=[];w=[];offset=0;cross=0;states=[]
 if arm=='unary_seeded':return np.empty(0,int),np.empty(0,int),np.empty(0,float),dict(nodes=n,cross_edges=0,correspondence_states=[])
 for x in data:
  i.append(x['i']+offset);j.append(x['j']+offset);w.append(edge_weight(x['color'][x['i']],x['color'][x['j']],x['d'],color));offset+=len(x['world'])
 if len(data)==2 and arm!='no_cross':
  ab,bb,sa=links(data[0],data[1]);ba,aa,sb=links(data[1],data[0]);pairs=np.unique(np.r_[np.c_[ab,bb],np.c_[aa,ba]],axis=0);a,b=pairs.T;da=np.bincount(a,minlength=len(data[0]['world']));db=np.bincount(b,minlength=len(data[1]['world']));ww=.5*edge_weight(data[0]['color'][a],data[1]['color'][b],np.ones(len(a)),color)/np.maximum(da[a],db[b]);i.append(a);j.append(b+len(data[0]['world']));w.append(ww);cross=len(a);states=[np.bincount(sa,minlength=6).tolist(),np.bincount(sb,minlength=6).tolist()]
 return np.concatenate(i),np.concatenate(j),np.concatenate(w),dict(nodes=n,cross_edges=cross,correspondence_states=states)

def transfer_priors(n,ids,q,w,classes):
 deg=np.bincount(ids,minlength=n);ww=w/np.maximum(deg[ids],1);g=np.bincount(ids,weights=ww,minlength=n);p=np.zeros((n,classes))
 for k in range(classes):p[:,k]=np.bincount(ids,weights=ww*q[:,k],minlength=n)
 ok=g>0;p[ok]/=g[ok,None];return g,p
