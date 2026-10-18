from env import *
from features import transform
sys.path.append(str(CODE.parent/'round03'))
def authorize_fit(s,vv):
 if vv!=[DEV[s],AUX[s]]:raise ValueError('only frozen two BUILD views')
def training(x,y,arm,classes):
 f,e=transform(x,arm);y=np.asarray(y)
 if len(y)!=len(f):raise ValueError('length')
 if any(not np.any(e&(y==k)) for k in range(1,classes+1)):raise ValueError('no eligible seed class; no fallback')
 f=f[e].copy();lab=y[e].copy();perm=np.arange(len(f))
 if arm=='shuffled_chromaticity':perm=np.random.default_rng(1729).permutation(len(f));f=f[perm]
 return dict(features=f,labels=lab,eligible=e,permutation=perm)
def pack(mask,outer_unknown,l,q,d,e):
 shape=mask.shape;K=q.shape[1];labels=np.zeros(shape,np.uint8);labels[mask]=l;prob=np.zeros((*shape,K),np.float64);prob[mask]=q;den=np.zeros_like(prob);den[mask]=d;elig=np.zeros(shape,bool);elig[mask]=e;yy,xx=np.where(mask)
 return dict(labels=labels,unknown=(mask&(labels==0))|outer_unknown,probability=prob,density=den,inference_mask=mask.copy(),source_uv=np.c_[xx,yy].astype(np.int32),feature_eligible=elig)
