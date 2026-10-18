"""Measurements of hypothetical image closure, never modifications to C8 ink."""
from env import *
from skimage.draw import polygon

def closure_score(gaps,perimeter,open_structure=False):
 if open_structure:return None
 return float(np.clip(1-np.linalg.norm(gaps)/max(perimeter,1e-15),0,1))
def link_gate(a,b,ta,tb,za,zb,p,va,vb,gap=6.,angle=60.,layer=3.):
 if not va or not vb:return False,'unknown_or_occluded_end'
 d=np.asarray(b)-a;L=float(np.linalg.norm(d))
 if L>gap:return False,'gap'
 if not np.isfinite(za+zb+p) or abs(za-zb)>layer*p:return False,'different_layer'
 if L>1e-9:
  u=d/L;ca=float(np.dot(ta,u));cb=float(np.dot(tb,-u))
  if min(ca,cb)<np.cos(np.deg2rad(angle)):return False,'direction'
 return True,'local_hypothesis'
def visible_state(z,surface,alpha,f):
 z=np.asarray(z);s=np.asarray(surface);a=np.asarray(alpha);out=np.full(z.shape,'unknown',dtype='<U24');ok=np.isfinite(z)&np.isfinite(s)&(z>.2)&(s>.2)&(a>=.5);tol=np.maximum(.01*s,6*s/f)
 out[ok&(abs(z-s)<=tol)]='visible';out[ok&(z-s>tol)]='occluded';out[ok&(s-z>tol)]='front_inconsistent';return out
def region_mask(rings,shape):
 mask=np.zeros(shape,bool)
 for p in rings:
  rr,cc=polygon(np.asarray(p)[:,1],np.asarray(p)[:,0],shape);mask[rr,cc]^=True
 return mask
def independent_count(view_observations):return len(set(tuple(x) for x in view_observations))
def can_assign(boundary_qualified,transfer_fraction,iou):return bool(boundary_qualified and transfer_fraction>=.5 and iou>=.5)
