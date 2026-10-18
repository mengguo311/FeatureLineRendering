from env import *
sys.path.append(str(CODE.parent/'round03'))
from density import fit_density,lookup
ARMS=['raw_rgb','rgb_texture','rgb_scrambled_texture','texture_only']
def authorize_fit(s,vv):
 if vv!=[DEV[s],AUX[s]]:raise ValueError('frozen BUILD only')
def densities(model,x,t,arm):
 if arm not in ARMS:raise ValueError('unknown arm')
 if arm=='texture_only':return lookup(model['texture_hist'],t)
 d=lookup(model['rgb_hist'],x)
 return d if arm=='raw_rgb' else d*lookup(model['texture_hist'],t)
def fit(data,classes,arm):
 a=fit_density([(x,y) for x,t,y in data],classes);b=fit_density([(t,y) for x,t,y in data],classes);m=dict(rgb_hist=a['hist'],texture_hist=b['hist'],classes=np.asarray(classes,np.int64));threshold=[]
 for x,t,y in data:
  d=densities(m,x,t,arm);threshold.append([float(np.quantile(d[np.asarray(y)==k+1,k],.05)) for k in range(classes)])
 m['threshold']=np.mean(threshold,axis=0);return m
def predict(m,x,t,arm):
 d=densities(m,x,t,arm);q=d/d.sum(1,keepdims=True);o=np.argsort(q,axis=1);win=o[:,-1];mq=q[np.arange(len(q)),win];margin=mq-q[np.arange(len(q)),o[:,-2]];known=(mq>=.65)&(margin>=.2)&(d[np.arange(len(q)),win]>=m['threshold'][win]);return np.where(known,win+1,0).astype(np.uint8),q,d
def pack(mask,outer_unknown,l,q,d):
 shape=mask.shape;K=q.shape[1];labels=np.zeros(shape,np.uint8);labels[mask]=l;prob=np.zeros((*shape,K));prob[mask]=q;den=np.zeros_like(prob);den[mask]=d;yy,xx=np.where(mask)
 return dict(labels=labels,unknown=(mask&(labels==0))|outer_unknown,probability=prob,density=den,inference_mask=mask.copy(),source_uv=np.c_[xx,yy].astype(np.int32))
