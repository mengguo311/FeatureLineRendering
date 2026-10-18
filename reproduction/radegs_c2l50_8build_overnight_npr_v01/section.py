from env import np,json,R
from scipy.ndimage import gaussian_filter1d
C=json.loads((R/'CONFIG.json').read_text())['section']
def split_profile(width,valid):
 w=np.asarray(width,float);v=np.asarray(valid,bool)&np.isfinite(w)&(w>0);n=len(w)
 if v.mean()<C['min_valid_fraction']:return dict(qualified=False,reason='insufficient_observed_bins',valid_fraction=float(v.mean()),cuts=None)
 # Normalized smoothing of descriptor only; original missing bins remain unobserved.
 f=np.where(v,np.log(np.maximum(w,1e-30)),0.);mass=gaussian_filter1d(v.astype(float),C['profile_smoothing_sigma_bins']);f=gaussian_filter1d(f,C['profile_smoothing_sigma_bins'])/np.maximum(mass,1e-15)
 def stats(a,b):
  q=f[a:b][v[a:b]];return (float(((q-q.mean())**2).sum()),float(q.mean())) if len(q) else (float('inf'),0.)
 base=stats(0,n)[0];best=None;m=C['min_segment_bins']
 for a in range(m,n-2*m+1):
  for b in range(a+m,n-m+1):
   st=[stats(0,a),stats(a,b),stats(b,n)];s=sum(t[0] for t in st)
   if best is None or s<best[0]:best=(s,a,b,[t[1] for t in st])
 s,a,b,means=best;ratio1=float(np.exp(means[1]-means[0]));ratio2=float(np.exp(means[1]-means[2]));improvement=float(1-s/base) if base>1e-12 else 0.;good=bool(ratio1<=C['width_middle_ratio'] and ratio2<=C['width_middle_ratio'] and improvement>=C['log_sse_improvement'])
 return dict(qualified=good,reason='broad_narrow_broad' if good else 'no_qualified_bottleneck',cuts=[a,b],segment_width=np.exp(means).tolist(),middle_lower_ratio=ratio1,middle_upper_ratio=ratio2,sse_single=base,sse_three=s,relative_improvement=improvement,valid_fraction=float(v.mean()))
def cross_sections(X,view,up,bins):
 X=np.asarray(X,float);u=np.asarray(up,float);q=np.eye(3)[np.argmin(abs(u))];e=np.cross(u,q);e/=np.linalg.norm(e);f=np.cross(u,e);xy=X@np.array([e,f]).T;h=X@u;lo,hi=np.quantile(h,[.01,.99]);idx=np.floor((h-lo)/(hi-lo)*bins).astype(int);ids=np.unique(view);width=np.full((len(ids),bins),np.nan);count=np.zeros_like(width,int)
 for j,vi in enumerate(ids):
  for b in range(bins):
   pts=xy[(view==vi)&(idx==b)];count[j,b]=len(pts)
   if len(pts)>=C['min_points_per_view_bin']:width[j,b]=np.linalg.norm(np.quantile(pts,.95,axis=0)-np.quantile(pts,.05,axis=0))
 valid=np.isfinite(width).all(0)&(width>0).all(0)&(len(ids)>=C['minimum_view_count']);common=np.full(bins,np.nan)
 if len(ids)>=2:common[valid]=np.median(width[:,valid],axis=0)
 return dict(width_by_view=width,counts=count,width_common=common,valid=valid,height_lo=np.array(lo),height_hi=np.array(hi),up=u,horizontal_basis=np.array([e,f]),view_ids=ids)
def profile_labels(h,lo,hi,cuts,bins):
 h=np.asarray(h);t=(h-lo)/(hi-lo)*bins;lab=(1+(t>=cuts[0]).astype(int)+(t>=cuts[1]).astype(int)).astype(np.int16);unknown=(t<0)|(t>bins)|~np.isfinite(t)
 for c in cuts:unknown|=abs(t-c)<=C['boundary_unknown_bins']
 lab[unknown]=0;return lab
def fit_sections(X,view,up):
 ar=cross_sections(X,view,up,C['bins']);m=split_profile(ar['width_common'],ar['valid']);single=[split_profile(w,np.isfinite(w)) for w in ar['width_by_view']];consistent=m['qualified'] and all(s['qualified'] and max(abs(np.asarray(s['cuts'])-m['cuts']))<=C['cut_view_disagreement_bins'] for s in single)
 m.update(qualified=bool(consistent),independent_view_models=single,height_lo=float(ar['height_lo']),height_hi=float(ar['height_hi']),up=list(up),bins=C['bins'],crossview_cut_consistency=bool(consistent),sample_count=len(X),view_counts={str(int(i)):int((view==i).sum()) for i in np.unique(view)})
 if not consistent:m['reason']='profile_or_crossview_bottleneck_not_qualified'
 return m,ar
