"""F0: visual audit of actual RaDe-GS kernel on a frozen vanilla PLY."""
from pathlib import Path
import json,sys
import numpy as np,cv2
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src import common,render,raster_state
from src.rade_state_calibration import render_rade_frozen
cams,_=common.load_cameras('lego');g=common.load_gaussians('lego')
out=ROOT/'artifacts'/'hao_mukai_rade_foundation'/'lego_r0';out.mkdir(parents=True,exist_ok=True)
r=render_rade_frozen(g,cams[0])
keep=render.defloat_mask(g['mu'],g['opacity'])
p=raster_state.numpy_state(raster_state.render_state(g,keep,cams[0],device='cuda',K=4))
fg=r['alpha']>.05
assert fg.shape==(cams[0].H,cams[0].W) and fg.any()
assert all(np.isfinite(r[k]).all() for k in ('rgb','alpha','normal','expected_depth'))
assert (r['radii']>0).sum()>1000
np.savez_compressed(out/'rade_raw_buffers.npz',rgb=r['rgb'],alpha=r['alpha'],normal=r['normal'],expected_depth=r['expected_depth'],median_depth=r['median_depth'])
def rgb8(x):return (np.clip(x,0,1)*255).astype('uint8')[:,:,::-1]
def gray3(x):return cv2.cvtColor((np.clip(x,0,1)*255).astype('uint8'),cv2.COLOR_GRAY2BGR)
dep=r['expected_depth'];vals=dep[fg];lo,hi=np.percentile(vals,[5,95]);norm=(dep-lo)/max(hi-lo,1e-6)
depim=cv2.applyColorMap((255*np.clip(norm,0,1)).astype('uint8'),cv2.COLORMAP_TURBO);depim[~fg]=255
normal=rgb8((r['normal']+1)/2);normal[~fg]=255
proxy_depth=p['depth'].copy();pf=p['alpha']>.05;pd=proxy_depth[pf&np.isfinite(proxy_depth)];pl,ph=np.percentile(pd,[5,95]);pn=(proxy_depth-pl)/max(ph-pl,1e-6)
pdim=cv2.applyColorMap((np.clip(pn,0,1)*255).astype('uint8'),cv2.COLORMAP_TURBO);pdim[~pf]=255
ims=[rgb8(r['rgb']),gray3(r['alpha']),depim,normal,gray3(p['alpha']),pdim]
labels=['RaDe CUDA SH0 RGB (NOT trained RaDe)','RaDe CUDA alpha','RaDe CUDA expected depth','RaDe CUDA normal','Old disc proxy alpha (defloated)','Old disc proxy mean depth']
rows=[]
for i in (0,3):
 tiles=[]
 for j in range(i,i+3):
  tile=np.full((cams[0].H+58,cams[0].W,3),255,'uint8');tile[58:]=ims[j]
  cv2.putText(tile,labels[j],(12,38),cv2.FONT_HERSHEY_SIMPLEX,.83,(0,0,0),2,cv2.LINE_AA)
  tiles.append(tile)
 rows.append(np.concatenate(tiles,axis=1))
cv2.imwrite(str(out/'state_comparison.png'),np.concatenate(rows,axis=0))
meta={'attribution':'RaDe-GS kernel Zhang et al TOG 2026; Hao-Mukai poster SA 2026; compatibility wrapper by us',
      'source_commit':'HKUST-SAIL/RaDe-GS@d72f20792005ae1d6555a82aa2d15345f247604e',
      'input':'frozen vanilla GS Lego PLY, train r_0, no filter_3D and no RaDe training',
      'gaussians':len(g['mu']),'disc_after_defloater':int(keep.sum()),
      'official_kernel_projected':int((r['radii']>0).sum()),
      'coverage_alpha_gt_005':int(fg.sum()),'proxy_coverage_alpha_gt_005':int(pf.sum()),
      'mean_alpha_official':float(r['alpha'].mean()),'mean_alpha_proxy':float(p['alpha'].mean()),
      'alpha_mean_abs_difference':float(np.abs(r['alpha']-p['alpha']).mean()),
      'depth_p5_p95_official_foreground':[float(lo),float(hi)],'normal_finite':bool(np.isfinite(r['normal']).all())}
(out/'STATE.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(meta,indent=2),flush=True)
