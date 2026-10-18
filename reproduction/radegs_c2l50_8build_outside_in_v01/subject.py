"""Image-only subject proposals. No ink input, no semantic GT, no global depth cut."""
from env import *
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix,csr_matrix
from scipy.sparse.csgraph import maximum_flow,breadth_first_order,connected_components
from sklearn.mixture import GaussianMixture
import warnings
CFG=json.loads((ROOT/'CONFIG_FREEZE.json').read_text())['stageA']

def energy(m,d0,d1,i,j,w):return float(np.where(m,d1,d0).sum()+(w*(m[i]!=m[j])).sum())
def binary_cut(d0,d1,i,j,w):
 d0=np.asarray(d0,float).ravel();d1=np.asarray(d1,float).ravel();n=len(d0);q=CFG['capacity_scale'];off=np.minimum(d0,d1);d0=d0-off;d1=d1-off
 assert np.isfinite(d0).all() and np.isfinite(d1).all() and np.isfinite(w).all() and (np.asarray(w)>=0).all()
 ids=np.arange(n);rows=np.r_[np.full(n,n),ids,i,j];cols=np.r_[ids,np.full(n,n+1),j,i];values=np.r_[d0,d1,w,w];cap=coo_matrix((np.rint(values*q).astype(np.int64),(rows,cols)),shape=(n+2,n+2)).tocsr();cap.eliminate_zeros()
 flow=maximum_flow(cap,n,n+1,method='dinic');res=cap-flow.flow;res.data=(res.data>0).astype(np.int64);res.eliminate_zeros();reachable=breadth_first_order(res,n,directed=True,return_predecessors=False);m=np.zeros(n,bool);m[reachable[reachable<n]]=True;return m

def seeds(rgb,alpha,z,shift=0.):
 h,w=alpha.shape;yy,xx=np.mgrid[:h,:w];border=(xx<CFG['border_fraction']*w)|(xx>=(1-CFG['border_fraction'])*w)|(yy<CFG['border_fraction']*h)|(yy>=(1-CFG['border_fraction'])*h)
 b=CFG['palette_bins'];bins=np.clip(np.floor(rgb[border]*b),0,b-1).astype(int);keys=(bins[:,0]*b+bins[:,1])*b+bins[:,2];counts=np.bincount(keys,minlength=b**3);key=counts.argmax();fraction=counts[key]/len(keys)
 if fraction<CFG['palette_min_border_fraction']:raise ValueError('BACKGROUND_PALETTE_UNIDENTIFIED')
 center=np.median(rgb[border][keys==key],axis=0);dist=np.linalg.norm(rgb-center,axis=2)
 bg=(border&(dist<CFG['bg_seed_color_distance']))|((alpha<CFG['alpha_background'])&(dist<CFG['bg_seed_color_distance']))
 e=((xx/w-(.5+shift))/CFG['seed_rx'])**2+((yy/h-CFG['seed_y'])/CFG['seed_ry'])**2<1
 fg=e&(dist>CFG['fg_seed_color_distance'])&(alpha>CFG['alpha_seed'])&np.isfinite(z)&(z>CFG['near_clip']);fg&=~bg
 if fg.sum()<CFG['min_seed_pixels'] or bg.sum()<CFG['min_seed_pixels']:raise ValueError('INSUFFICIENT_AUTOMATIC_SEEDS')
 return fg,bg,dist,dict(background_rgb=center.tolist(),dominant_border_fraction=float(fraction),foreground_seed_pixels=int(fg.sum()),background_seed_pixels=int(bg.sum()),shift=shift)

def edges(rgb,alpha,z,c,depth=True):
 h,w=alpha.shape;ids=np.arange(h*w).reshape(h,w);i=np.r_[ids[:,:-1].ravel(),ids[:-1].ravel()];j=np.r_[ids[:,1:].ravel(),ids[1:].ravel()];x=rgb.reshape(-1,3);a=alpha.ravel();d=z.ravel();dc=((x[i]-x[j])**2).sum(1)
 weight=CFG['pair_gamma']*np.exp(-dc/(2*CFG['pair_color_sigma']**2));valid=np.isfinite(d)&(d>.2)&(a>=CFG['alpha_reliable']);both=valid[i]&valid[j]
 if depth:
  dz=np.zeros(len(i));dz[both]=abs(d[i[both]]-d[j[both]])*np.sqrt(c['fx']*c['fy'])/((d[i[both]]+d[j[both]])*.5);weight[both]*=np.exp(-np.minimum(dz[both]/CFG['pair_depth_sigma_worldpixels'],20)**2/2)
 return i,j,weight,both

def fit_cost(rgb,m):
 x=rgb.reshape(-1,3).astype(np.float64);mask=m.ravel();cost=[];meta=[]
 for label in [False,True]:
  idx=np.flatnonzero(mask==label)
  if len(idx)<CFG['min_seed_pixels']:raise ValueError('EMPTY_CLASS_AFTER_CUT')
  idx=idx[np.linspace(0,len(idx)-1,min(len(idx),CFG['gmm_sample_budget_per_class']),dtype=int)];unique=len(np.unique(x[idx],axis=0));k=min(CFG['gmm_components'],unique)
  g=GaussianMixture(n_components=k,covariance_type=CFG['gmm_covariance_type'],reg_covar=CFG['gmm_reg_covar'],max_iter=CFG['gmm_max_iter'],random_state=CFG['random_seed'],n_init=1)
  with warnings.catch_warnings(record=True) as warns:g.fit(x[idx])
  cost.append(-g.score_samples(x));meta.append(dict(label=int(label),samples=len(idx),components=k,converged=bool(g.converged_),warnings=[str(v.message) for v in warns]))
 costs=np.stack(cost);costs-=costs.min(0);costs=np.minimum(costs,CFG['unary_clip']);return costs,meta

def propose(rgb,alpha,z,c,shift):
 fg,bg,dist,receipt=seeds(rgb,alpha,z,shift);m=(dist>CFG['fg_seed_color_distance'])&(alpha>=CFG['alpha_background']);m[fg]=True;m[bg]=False;i,j,w,both=edges(rgb,alpha,z,c);logs=[]
 for it in range(CFG['outer_iterations']):
  costs,meta=fit_cost(rgb,m);margin=abs(costs[1]-costs[0]).reshape(m.shape);d0,d1=costs;d0[fg.ravel()]=CFG['hard_seed_cost'];d1[fg.ravel()]=0;d1[bg.ravel()]=CFG['hard_seed_cost'];d0[bg.ravel()]=0
  new=binary_cut(d0,d1,i,j,w).reshape(m.shape);logs.append(dict(iteration=it,changed=int((new!=m).sum()),foreground=int(new.sum()),energy=energy(new.ravel(),d0,d1,i,j,w),gmm=meta));m=new
 receipt.update(iterations=logs,reliable_depth_edges=int(both.sum()),total_graph_edges=len(i));return m,margin,receipt,fg,bg

def consensus(masks,alpha,z,margin):
 stack=np.stack(masks);main=stack[len(masks)//2];un=stack.any(0);inter=stack.all(0);uncertain=(stack.mean(0)>0)&(stack.mean(0)<1)
 unknown=uncertain|((alpha>=CFG['alpha_background'])&((alpha<CFG['alpha_reliable'])|~np.isfinite(z)|(z<=.2)))|(margin<CFG['uncertain_unary_margin'])
 return dict(candidate=main,possible=un,certain=inter&~unknown,unknown=unknown,seed_agreement=stack.mean(0).astype(np.float32))

def depth_component(z,alpha,c):
 h,w=z.shape;ids=np.arange(h*w).reshape(h,w);i=np.r_[ids[:,:-1].ravel(),ids[:-1].ravel()];j=np.r_[ids[:,1:].ravel(),ids[1:].ravel()];a=alpha.ravel();d=z.ravel();valid=np.isfinite(d)&(d>.2)&(a>=.5);good=valid[i]&valid[j]
 with np.errstate(invalid='ignore',divide='ignore'):jump=abs(d[i]-d[j])*np.sqrt(c['fx']*c['fy'])/((d[i]+d[j])*.5)
 good&=jump<=CFG['depth_connected_control_neighbor_worldpixels'];graph=coo_matrix((np.ones(int(good.sum())*2),(np.r_[i[good],j[good]],np.r_[j[good],i[good]])),shape=(h*w,h*w)).tocsr();_,labels=connected_components(graph,directed=False)
 yy,xx=np.mgrid[:h,:w];r=CFG['depth_connected_seed_radius_fraction'];seed=(((xx/w-.5)**2+(yy/h-.5)**2)<r*r)&valid.reshape(h,w);rootids=np.unique(labels[seed.ravel()]);return (np.isin(labels,rootids)&valid).reshape(h,w)

def gated_stage(previous):return 'READY' if previous=='GO' else 'NOT_RUN'

def run_arrays(rgb,alpha,z,c):
 out=[];marg=[];receipts=[];seed_masks=[]
 for sh in CFG['seed_x_shifts']:
  m,margin,receipt,fg,bg=propose(rgb,alpha,z,c,sh);out.append(m);marg.append(margin);receipts.append(receipt);seed_masks.append((fg,bg))
 arrays=consensus(out,alpha,z,marg[1]);arrays['masks']=np.stack(out);arrays['margin']=marg[1].astype(np.float32);arrays['fg_seed']=seed_masks[1][0];arrays['bg_seed']=seed_masks[1][1];_,_,d,_=seeds(rgb,alpha,z,0)
 arrays['rgb_alpha_control']=(d>CFG['rgb_alpha_control_distance'])&(alpha>=CFG['alpha_background']);arrays['alpha_control']=alpha>=.5;arrays['depth_control']=depth_component(z,alpha,c)
 return arrays,receipts
