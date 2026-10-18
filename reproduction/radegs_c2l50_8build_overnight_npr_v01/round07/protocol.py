from env import *
def authorize_fit(scene,view_list,classes=None):
 if scene not in SCENES or list(view_list)!=[DEV[scene],AUX[scene]]:raise ValueError('only frozen DEV+AUX permitted')
 if classes is not None and classes!=(3 if scene=='ficus' else 2):raise ValueError('DTU subject proxies only; no part fit')
 return True
def pack(mask,subject_unknown,labels,probability):
 out=np.zeros(mask.shape,np.uint8);out[mask]=labels;q=np.zeros((*mask.shape,probability.shape[1]),probability.dtype);q[mask]=probability;y,x=np.nonzero(mask)
 return dict(labels=out,unknown=(mask&(out==0))|subject_unknown,probability=q,inference_mask=mask.copy(),source_uv=np.c_[x,y])
def calibrate(render,reference,rgb,z,alpha):
 for a,b in [('rgb','source_rgb'),('alpha','source_alpha'),('median_center_z','source_center_z')]:np.testing.assert_array_equal(render[a],reference[b])
 good=np.isfinite(z)&(z>.2)&np.isfinite(render['median_center_z'])&(render['median_center_z']>.2)&(alpha>.5)
 d=np.abs(render['median_center_z'][good]-z[good])/z[good]
 row=dict(full_reference_exact=True,rgb_mae=float(np.abs(render['rgb']-rgb).mean()),alpha_mae=float(np.abs(render['alpha']-alpha).mean()),depth_relative_p95=float(np.quantile(d,.95)) if len(d) else None,depth_pixels=int(good.sum()),depth_semantics='center-depth vs cached surface proxy; NOT equality')
 assert row['rgb_mae']<=.02 and row['alpha_mae']<=.02 and row['depth_relative_p95'] is not None and row['depth_relative_p95']<=.15,row
 return row
