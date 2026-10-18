from env import *
def authorize_fit(s):
 if s!='ficus':raise ValueError('no qualified subject mask: no part fit permitted')
 return True
def fit_views(s):
 authorize_fit(s);return [DEV[s],AUX[s]]
def pack(mask,subject_unknown,labels,probability):
 out=np.zeros(mask.shape,np.uint8);out[mask]=labels;q=np.zeros((*mask.shape,probability.shape[1]),probability.dtype);q[mask]=probability;y,x=np.nonzero(mask)
 return dict(labels=out,unknown=(mask&(out==0))|subject_unknown,probability=q,inference_mask=mask.copy(),source_uv=np.c_[x,y])
