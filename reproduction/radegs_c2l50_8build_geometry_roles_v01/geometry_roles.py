"""Conservative observable support roles, NOT recovered physical primitives."""
from env import *
ROLES=['single_sheet_support','two_side_boundary_or_layer_candidate','thin_filament_candidate','volumetric_or_ambiguous','UNKNOWN']
PALETTE=np.array([[.1,.7,.3],[.95,.4,.05],[.05,.7,.85],[.65,.25,.85],[.55,.55,.55]])
def fit_patch(X,weight,pixel):
 X=np.asarray(X,float);w=np.asarray(weight,float);valid=np.isfinite(X).all(1)&np.isfinite(w)&(w>0);X=X[valid];w=w[valid];out=dict(valid=False,points=X.tolist(),point_count=len(X),pixel=float(pixel),reason='insufficient_surface_samples')
 if len(X)<10:return out
 ww=w.copy()
 for _ in range(5):
  center=np.average(X,axis=0,weights=ww);d=X-center;cov=(d.T*ww)@d/ww.sum();e,U=np.linalg.eigh(cov);n=U[:,0];r=d@n;scale=max(.1*pixel,1.4826*np.median(abs(r-np.median(r))));ww=w*np.minimum(1,1.5*scale/np.maximum(abs(r),1e-20))
 rms=float(np.sqrt(np.average(r*r,weights=ww))/pixel);spread=float(e[1]/max(e[2],1e-30));fraction=float(np.mean(abs(r)<=2*pixel));ok=rms<=1 and spread>=.005 and fraction>=.8
 out.update(valid=bool(ok),center=center.tolist(),normal=n.tolist(),eigenvalues=e.tolist(),rms_pixels=rms,two_dimensional_spread=spread,inlier_fraction_2p=fraction,weights=ww.tolist(),reason='qualified_depth_patch_proxy' if ok else 'residual_or_condition_or_mixed_layer',normal_source='native-depth backprojection plane fit, NOT Gaussian minimum axis')
 return out
def classify(left,right,x):
 role=4;reason='insufficient_credible_side_support';angle=None
 if not x['center_supported']:reason='line_not_qualified_at_source_surface_or_hidden'
 elif x['ray_width_pixels']>8:role=3;reason='broad_source_center_depth_mixture_not_a_surface_proof'
 elif left.get('valid') and right.get('valid'):
  angle=float(np.degrees(np.arccos(np.clip(abs(np.dot(left['normal'],right['normal'])),0,1))))
  if angle<=15 and x['join_pixels']<=2:role=0;reason='two_observed_sides_compatible_single_depth_sheet'
  elif x['L1']>=.35 and (x['join_pixels']>4 or (angle>=25 and x['join_pixels']<=2)):role=1;reason='separated_layer_candidates' if x['join_pixels']>4 else 'joining_changed_normal_candidates'
  else:role=3;reason='geometry_or_ID_responsibility_conflict'
 elif x['alpha_center']>=.5 and max(x['alpha_left'],x['alpha_right'])<.2 and x['filament_shape']:role=2;reason='thin_visible_band_with_tube_like_source_allocation_ONLY'
 elif left.get('point_count',0)>=10 and right.get('point_count',0)>=10:role=3;reason='side_geometry_unresolved'
 score=np.zeros(5);score[role]=.7 if role!=4 else 1.;score[4]+=1-score.sum()
 return dict(role=ROLES[role],role_index=role,soft_role_scores=score.tolist(),reason=reason,normal_angle_degrees=angle,appearance_cue=x.get('rgb_side_difference',0)>.06,physical_primitive_certified=False,scores_are_uncalibrated_evidence=True)
def plane_ray_depth(patch,uv,c):
 if not patch.get('valid'):return np.full(len(uv),np.nan)
 E=np.asarray(c['extrinsic']);O=-E[:3,:3].T@E[:3,3];r=unproject(uv,np.ones(len(uv)),c)-O;n=np.asarray(patch['normal']);den=r@n;ok=abs(den)/np.maximum(np.linalg.norm(r,axis=1),1e-20)>.1
 return np.where(ok,(np.asarray(patch['center'])-O)@n/np.where(ok,den,np.nan),np.nan)
