"""Finite visible responsibility graph and local proxy sheets; no source editing."""
from env import *
from geometry_roles import plane_ray_depth

def fit_sheet(X,w,pixel_id,source_id,p):
 X=np.asarray(X,float);w=np.asarray(w,float);pix=np.asarray(pixel_id);ids=np.asarray(source_id);good=np.isfinite(X).all(1)&np.isfinite(w)&(w>0);X=X[good];w=w[good];pix=pix[good];ids=ids[good]
 n=len(np.unique(pix));ns=len(np.unique(ids));out=dict(valid=False,unique_pixels=n,unique_sources=ns,point_hypotheses=len(X),reason='insufficient_unique_pixels_or_sources')
 if n<10 or ns<3:return out
 _,ii=np.unique(pix,return_inverse=True);w=w/np.bincount(ii,weights=w)[ii];ww=w.copy()
 for _ in range(5):
  ctr=np.average(X,axis=0,weights=ww);d=X-ctr;ev,U=np.linalg.eigh((d.T*ww)@d/ww.sum());normal=U[:,0];r=d@normal;scale=max(.1*p,1.4826*np.median(abs(r-np.median(r))));ww=w*np.minimum(1,1.5*scale/np.maximum(abs(r),1e-30))
 rms=float(np.sqrt(np.average(r*r,weights=ww))/p);spread=float(ev[1]/max(ev[2],1e-30));frac=float(np.average(abs(r)<=2*p,weights=w));cost=float(np.average(np.minimum((r/p)**2,9),weights=w));out.update(valid=bool(rms<=1 and spread>=.005 and frac>=.8),center=ctr.tolist(),normal=normal.tolist(),rms_p=rms,spread=spread,inlier_mass_fraction=frac,cost=cost,reason='qualified_conditional_point_sheet_proxy' if rms<=1 and spread>=.005 and frac>=.8 else 'residual_condition_or_layer_mixture',normal_source='fitted conditional ray points, NOT source covariance min axis')
 return out

def source_distribution(ids,w):
 u,ii=np.unique(ids,return_inverse=True);v=np.bincount(ii,weights=w);v=v/max(v.sum(),1e-30);return u,v

def overlap_of(ia,wa,ib,wb):
 u=np.union1d(ia,ib);a=np.zeros(len(u));b=a.copy();a[np.searchsorted(u,ia)]=wa;b[np.searchsorted(u,ib)]=wb;return float(np.minimum(a,b).sum())

def select_sheets(X,w,pix,ids,side,p):
 single=fit_sheet(X,w,pix,ids,p);left=fit_sheet(X[side<0],w[side<0],pix[side<0],ids[side<0],p);right=fit_sheet(X[side>0],w[side>0],pix[side>0],ids[side>0],p)
 out=dict(model='REFUSED',single=single,left=left,right=right,physical_primitive_certified=False,source_overlap=None,reason='unqualified_single_and_sides')
 if not len(X):return out
 _,ii=np.unique(pix,return_inverse=True);wn=w/np.maximum(np.bincount(ii,weights=w)[ii],1e-30);ia,wa=source_distribution(ids[side<0],wn[side<0]);ib,wb=source_distribution(ids[side>0],wn[side>0]);overlap=overlap_of(ia,wa,ib,wb);out['source_overlap']=overlap
 if single['valid']:out.update(model='single',reason='single_proxy_preferred_complexity')
 if 'cost' not in single or not left['valid'] or not right['valid']:return out
 n=single['unique_pixels'];nl=left['unique_pixels'];nr=right['unique_pixels'];single_cost=single['cost'];two_cost=(nl*left['cost']+nr*right['cost'])/(nl+nr);gain=1-two_cost/max(single_cost,1e-20);bic1=n*np.log(max(single_cost,.0001))+3*np.log(n);bic2=n*np.log(max(two_cost,.0001))+6*np.log(n);out.update(single_cost=single_cost,two_cost=two_cost,relative_gain=gain,single_bic=float(bic1),two_bic=float(bic2))
 if gain>=.3 and bic2<bic1 and overlap<=.85:out.update(model='two',reason='two_proxy_residual_and_complexity_and_source_separation')
 return out

def pair_patch(a,b,p):
 out=dict(eligible=False,physical_primitive_certified=False,reason='unqualified_patch')
 if not a.get('valid') or not b.get('valid'):return out
 overlap=overlap_of(np.asarray(a['ids']),np.asarray(a['mass']),np.asarray(b['ids']),np.asarray(b['mass']));n=np.asarray(a['normal']);m=np.asarray(b['normal']);d=np.asarray(a['center'])-b['center'];ang=float(np.degrees(np.arccos(np.clip(abs(n@m),0,1))));err=float(max(abs(d@n),abs(d@m))/p);distance=float(np.linalg.norm(d)/p);ok=overlap>=.15 and ang<=20 and err<=2 and distance<=20
 out.update(eligible=bool(ok),overlap=overlap,normal_deg=ang,symmetric_plane_p=err,center_distance_p=distance,reason='qualified_multi_view_proxy_only' if ok else 'ID_overlap_or_geometry_failed');return out

def extract_points(e,p,c):
 row=e['conditional_row'].astype(int);sides=np.sign(e['side_offset']);uv=e['query_uv'];_,inv=np.unique(uv,axis=0,return_inverse=True);first={};ambiguous=set()
 for j,idx in enumerate(inv):
  if idx in first and sides[first[idx]]!=sides[j]:ambiguous.add(idx)
  else:first.setdefault(idx,j)
 unique_row=np.zeros(len(uv),bool)
 for idx,j in first.items():
  if idx not in ambiguous:unique_row[j]=True
 good=e['conditional_valid']&(e['conditional_sigma']<=4*p)&e['conditional_pixel_qualified'][row]&unique_row[row]&(sides[row]!=0)&(e['weight']>0)
 ix=np.flatnonzero(good);q=row[ix];z=e['conditional_z'][ix];X=unproject(uv[q],z,c);w=e['weight'][ix];pi=inv[q];ids=e['source_index'][ix];sd=sides[q];return dict(X=X,weight=w,pixel_id=pi,source_index=ids,side=sd,query_row=q,csr_index=ix,conditional_sigma=e['conditional_sigma'][ix],all_contributor_count=len(row),qualified_contributor_count=len(ix),unique_query_pixels=len(np.unique(inv)),ambiguous_label_pixels=len(ambiguous),qualified_original_mass=float(w.sum()),all_original_mass=float(e['weight'].sum()))

def make_partition(e,base,c):
 p=base['info']['pixel_world_proxy'];d=extract_points(e,p,c);X,w,pix,ids,side=[d[k] for k in ['X','weight','pixel_id','source_index','side']];out=select_sheets(X,w,pix,ids,side,p);out['model_before_center_geometry_gate']=out['model'];out['pixel_world_proxy']=p;out['center_supported']=base['info']['center_supported'];out['physical_primitive_certified']=False;out['patches']=[];out['all_scene_unobserved_role']='UNKNOWN'
 if not out['center_supported']:out.update(model='REFUSED',reason='original_line_center_not_qualified_hidden_or_unsupported')
 if out['model']=='two':
  left,right=out['left'],out['right'];za=plane_ray_depth(left,e['proposed_line_uv'],c);zb=plane_ray_depth(right,e['proposed_line_uv'],c);ok=np.isfinite(za-zb);join=float(np.median(abs(za[ok]-zb[ok]))/p) if ok.any() else 1e9;angle=float(np.degrees(np.arccos(np.clip(abs(np.dot(left['normal'],right['normal'])),0,1))));out.update(join_p=join,normal_angle=angle)
  if not(join>4 or (join<=2 and angle>=25)):out.update(model='REFUSED',reason='two_proxy_not_qualified_join_or_layer_separation')
 if len(w):
  _,ii=np.unique(pix,return_inverse=True);wn=w/np.maximum(np.bincount(ii,weights=w)[ii],1e-30)
 else:wn=w
 selected=[('single',np.ones(len(X),bool))] if out['model']=='single' else [('left',side<0),('right',side>0)] if out['model']=='two' else []
 membership=np.zeros((len(X),len(selected)))
 for j,(key,k) in enumerate(selected):
  pp=out[key].copy();ii,ww=source_distribution(ids[k],wn[k]);pp.update(local_patch_id=j,side=key,ids=ii.tolist(),mass=ww.tolist());out['patches'].append(pp);membership[k,j]=wn[k]
 d['patch_membership']=membership;out['counts']={k:d[k] for k in ['all_contributor_count','qualified_contributor_count','unique_query_pixels','ambiguous_label_pixels','qualified_original_mass','all_original_mass']};out['counts'].update(qualified_pixels=len(np.unique(pix)),qualified_source_ids=len(np.unique(ids)));return out,d

def pair_models(a,b):
 import itertools
 aa=a['patches'];bb=b['patches'];p=(a['pixel_world_proxy']+b['pixel_world_proxy'])/2;out=dict(eligible=False,reason='missing_or_different_local_proxy_count',pairs=[],physical_primitive_certified=False)
 if not aa or len(aa)!=len(bb):return out
 matrix=[[pair_patch(x,y,p) for y in bb] for x in aa];poss=[]
 for perm in itertools.permutations(range(len(bb))):
  z=[matrix[i][j] for i,j in enumerate(perm)]
  if all(x['eligible'] for x in z):poss.append((sum(x['overlap'] for x in z),perm,z))
 poss.sort(reverse=True,key=lambda x:x[0]);out['candidate_pair_matrix']=matrix
 if not poss:return out
 margin=poss[0][0]-poss[1][0] if len(poss)>1 else 1.;out['margin']=margin
 if margin<.05:out['reason']='ambiguous_cross_view_assignment';return out
 out.update(eligible=True,reason='two_view_qualified_local_proxy_NOT_physical_certification',pairs=[dict(a=i,b=j,**z) for i,(j,z) in enumerate(zip(poss[0][1],poss[0][2]))]);return out
