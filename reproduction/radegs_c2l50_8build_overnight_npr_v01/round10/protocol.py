from env import *
sys.path.append(str(CODE.parent/'round09'))
from likelihood import fit,predict,authorize_fit,pack
ARMS=['alpha_texture','shifted_alpha_texture']
def fit_supported(scene,views,data,classes,valid):
 authorize_fit(scene,views)
 if len(valid)!=len(data) or any(len(v)!=len(d[0]) or not np.asarray(v,bool).all() for d,v in zip(data,valid)):raise ValueError('Unavailable BUILD seed: refuse arm; no budget reduction')
 return fit(data,classes,'rgb_texture')
def predict_supported(model,x,t,valid):
 valid=np.asarray(valid,bool)
 if valid.shape!=(len(x),):raise ValueError('validity shape')
 l,q,d=predict(model,x,t,'rgb_texture');l[~valid]=0;q[~valid]=0;d[~valid]=0
 return l,q,d
def pack_supported(mask,outer_unknown,l,q,d,eligible):
 out=pack(mask,outer_unknown,l,q,d);out['feature_eligible']=np.asarray(eligible,bool).copy();return out
