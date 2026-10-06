"""Conditional ephemeral native screen covariance override; recomputes all T."""
import difflib,json,shutil,types
import numpy as np
import torch
from runtime import *
from operators import raw_forward
from diagnostics import row_sample,sample_image
from scipy.sparse import csr_matrix
from media import save,sheet
OLD_LINE='float3 cov = computeCov2D(p_orig, focal_x, focal_y, tan_fovx, tan_fovy, cov3D, viewmatrix);'
NEW_LINE='float3 cov = cov3D[5] == -12345.f ? make_float3(cov3D[0], cov3D[1], cov3D[2]) : computeCov2D(p_orig, focal_x, focal_y, tan_fovx, tan_fovy, cov3D, viewmatrix);'

def build_shape():
 from torch.utils.cpp_extension import load
 guard('conditional_shape_build');build=json.loads((ATTR/'artifacts/gaer_attribution_buffer_v01/BUILD.json').read_text());dest=OUT/'native_shape'
 for name,h in build['variants']['patched']['files'].items():
  src=SOURCE/name
  if sha(src)!=h:raise RuntimeError('pinned native dependency changed '+name)
  dst=dest/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 p=dest/'cuda_rasterizer/forward.cu';text=p.read_text();assert text.count(OLD_LINE)==1;p.write_text(text.replace(OLD_LINE,NEW_LINE))
 # Only alternate isolated source uses sentinel in explicit cov3D input.
 m=load(name='capacity_shape_C',sources=[str(dest/n) for n in ['ext.cpp','rasterize_points.cu','cuda_rasterizer/rasterizer_impl.cu','cuda_rasterizer/forward.cu','cuda_rasterizer/backward.cu']],extra_cuda_cflags=['-I'+str(dest/'third_party/glm'),'-include','cstdint'],verbose=False)
 atomic_json(ART/'BUILD_SHAPE.json',dict(binary=str(m.__file__),binary_sha256=sha(m.__file__),patch_sha256=sha(EXP/'native_shape.patch'),pinned_source_digest=digest(build['variants']['patched']['files']),semantics='screen cov override before inversion/radius/culling/tiles; centers and peak opacity retained; original stock +.3 covariance floor; no determinant alpha compensation',production_unchanged=True))
 return types.SimpleNamespace(_C=m)

def render_shape(m,s,model,colors,cov):
 empty=torch.empty(0,device='cuda')
 return m._C.rasterize_gaussians(torch.ones(3,device='cuda'),model['means3D'],colors,model['opacities'],empty,empty,s.scale_modifier,cov,s.viewmatrix,s.projmatrix,s.tanfovx,s.tanfovy,800,800,empty,0,s.campos,False,False)

def run_shape(scene,s,model,a,rois,groups,csr_path,strength,fit_certificate,config):
 if fit_certificate['relative_dual_gap']>.005:
  return dict(status='NOT_RUN',reason='perview original fit not adequately certified; cannot infer a shape requirement',files=[])
 line=a['line_binary'];baseline_ink=raw_forward(__import__('binding').backend(),s,model,strength[:,None].expand(-1,3).contiguous(),torch.zeros(3,device='cuda'))[1][0].cpu().numpy();residual=float(np.square(baseline_ink[line]-a['ink'][line]).mean())
 if residual<=.01:return dict(status='NOT_RUN',reason='predeclared line-domain residual condition not met',line_MSE=residual,files=[])
 m=build_shape();data=np.load(csr_path);xy=data['projected_means_xy'];conic=data['projected_conic_opacity'];cov=data['original_cov3D'];pixels=data['query_pixels_yx'];points=data['sample_points_yx'];normal=data['normal_yx'];full=csr_matrix((data['accepted_weights'],data['accepted_original_ids'],data['accepted_offsets']),shape=(len(pixels),len(model['means3D'])));D=abs(row_sample(pixels,data['minus_yx'])@full-row_sample(pixels,data['plus_yx'])@full)
 selected_groups=[g for g in groups if g['category'] in ('outline','internal_color_transition') and g['fragment']==0];offsets=[];edits=[]
 for g in selected_groups:
  rows=np.arange(g['roi']*25,(g['roi']+1)*25);normals=normal[rows][:,::-1]
  for i in g['multiD_top16']:
   weights=np.asarray(D[rows,i].todense()).ravel();z=np.sum(weights*((normals[:,0]+1j*normals[:,1])**2));angle=.5*np.angle(z) if abs(z)>1e-12 else np.arctan2(normals[12,1],normals[12,0]);n=np.array([np.cos(angle),np.sin(angle)]);t=np.array([-n[1],n[0]]);C=np.array([[conic[i,0],conic[i,1]],[conic[i,1],conic[i,2]]]);det=np.linalg.det(C)
   if det<=0 or not np.isfinite(det):continue
   C=np.linalg.inv(C);vn=float(n@C@n);vt=float(t@C@t);center=np.array(g['center_yx'][::-1]);off=float((xy[i]-center)@n);offsets.append(off);edits.append((i,n,t,vn,vt,g['roi']))
 colors=(1-strength)[:,None].expand(-1,3).contiguous();base_cov=torch.tensor(cov,device='cuda');base_raw=render_shape(m,s,model,colors,base_cov);base=base_raw[1][0].cpu().numpy();formulaerr=float(np.abs((1-base)-baseline_ink).max())
 if formulaerr>3e-6:raise RuntimeError('isolated shape original covariance baseline mismatch')
 files=[];rows=[];panels=[1-a['ink'],1-baseline_ink];metrics=[]
 for ratio in config['ratios']:
  edited=cov.copy()
  for i,n,t,vn,vt,roi in edits:
   C=vt*np.outer(t,t)+max(.3,vn/(ratio**2))*np.outer(n,n);edited[i]=[C[0,0],C[0,1],C[1,1],0,0,-12345]
  edited_cov=torch.tensor(edited,device='cuda');raw=render_shape(m,s,model,colors,edited_cov);nativeT=render_shape(m,s,model,torch.zeros_like(colors),edited_cov)[1][0].cpu().numpy();alpha=1-nativeT;rgb=raw[1].cpu().numpy().transpose(1,2,0);ink=1-rgb[...,0];panels.append(rgb);p=ART/'downloads'/scene/f'shape_ratio{ratio}.npz';npz(p,ink=ink,alpha=alpha,final_T=nativeT,edited_original_ids=np.unique([e[0] for e in edits]),screen_override_cov=edited[np.unique([e[0] for e in edits])]);files.append(rel(p));files.append(save(ART/'media'/scene/f'shape_ratio{ratio}.png',rgb));metrics.append(dict(ratio=ratio,line_MSE=float(np.square(ink[line]-a['ink'][line]).mean()),outside_ink_MSE=float(np.square(ink[~line]).mean()),edited_count=len(set(e[0] for e in edits)),full_T_recomputed=True,alpha_MSE=float(np.square(alpha-a['alpha']).mean()),alpha_coverage_changed=int(((alpha>.5)!=(a['alpha']>.5)).sum()),ROI_metrics=[dict(roi=g['roi'],category=g['category'],line_MSE=float(np.square(ink[g['center_yx'][0]-12:g['center_yx'][0]+12,g['center_yx'][1]-12:g['center_yx'][1]+12]-a['ink'][g['center_yx'][0]-12:g['center_yx'][0]+12,g['center_yx'][1]-12:g['center_yx'][1]+12]).mean())) for g in selected_groups]))
 p=ART/'media'/scene/'conditional_shape_comparison.jpg';files.append(sheet(p,[panels],['target','original footprints','normal shrink 2','normal shrink 4'],scene+' conditional native shape, gain 1',800))
 crops=[]
 for g in selected_groups:
  y,x=g['center_yx'];crops.append([np.asarray(panel)[y-12:y+12,x-12:x+12] for panel in panels])
 files.append(sheet(ART/'media'/scene/'conditional_shape_ROI_nearest.png',crops,['target','original footprints','normal shrink 2','normal shrink 4'],scene+' conditional shape frozen 24px fragments',240))
 return dict(status='COMPLETE',edited_strength_sum=float(strength[torch.tensor(sorted(set(e[0] for e in edits)),device='cuda')].sum()),condition_line_MSE=residual,baseline_formula_max_abs=formulaerr,metrics=metrics,signed_centerline_offset_quantiles=np.quantile(offsets,[0,.25,.5,.75,1]).tolist() if offsets else [],absolute_centerline_offset_quantiles=np.quantile(np.abs(offsets),[0,.25,.5,.75,1]).tolist() if offsets else [],interpretation='capability only; fixed centers can remain off line; original full-T linear oracle upper bound does not apply; no fitted shape trajectory',files=files)
