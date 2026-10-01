"""Run independently reconstructed Hao–Mukai source equations, not official code."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import cv2,torch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src import common,render,raster_state
from src.hao_mukai_source_2026 import compute_fields

parser=argparse.ArgumentParser()
parser.add_argument('--scene',choices=['lego','chair'],required=True)
parser.add_argument('--view',type=int,default=0)
args=parser.parse_args()
assert args.view==0,'Only preregistered TRAIN camera 0 is allowed'
root=ROOT/'artifacts'/'hao_mukai_source_2026_repro'/args.scene
root.mkdir(parents=True,exist_ok=True)
cams,_=common.load_cameras(args.scene)
g=common.load_gaussians(args.scene)
keep=render.defloat_mask(g['mu'],g['opacity'])
st=raster_state.render_state(g,keep,cams[args.view],device='cuda',K=4,include_topk_attributes=True)
s=raster_state.numpy_state(st)
fields=compute_fields(s)
for name,f in fields.items():
 assert f.shape==(cams[0].H,cams[0].W) and np.isfinite(f).all(),name
 assert np.min(f)>=-1e-6,name
rgb=np.clip(s['albedo'],0,1)
sl=np.clip(fields['S_L'],0,1)
# Source output is the continuous field. Black-on-white mapping is OUR display-only preview.
continuous=(255*(1-sl)).astype(np.uint8)
cv2.imwrite(str(root/'stroke_density_continuous_ours_display.png'),continuous)
cv2.imwrite(str(root/'rgb_disc_proxy.png'),(rgb[:,:,::-1]*255).astype(np.uint8))
np.savez_compressed(root/'typed_fields.npz',**fields)
# Source fields remain untouched; a P99-positive normalization is OUR DISPLAY-ONLY choice.
positive=sl[sl>0]
sl_hi=float(np.quantile(positive,.99)) if len(positive) else 1.
contrast=(255*(1-np.clip(sl/max(sl_hi,1e-8),0,1))).astype(np.uint8)
cv2.imwrite(str(root/'stroke_density_p99_display_only.png'),contrast)
selected=['E_A','E_D','E_N','E_C','E_G','E_V','L','S_L','E_T']
thumb_w=640;thumb_h=480
panels=[]
for k in ['RGB disc proxy']+selected+['1-S_L P99 display']:
 if k=='RGB disc proxy':
  img=(rgb[:,:,::-1]*255).astype(np.uint8)
 elif k=='1-S_L P99 display':
  img=cv2.cvtColor(contrast,cv2.COLOR_GRAY2BGR)
 else:
  v=fields[k]
  # Paper normalizes fields independently ONLY for visualization; P99-positive is our display convention.
  pos=v[v>0];hi=float(np.quantile(pos,.99)) if len(pos) else 1.
  img=cv2.applyColorMap((np.clip(v/max(hi,1e-8),0,1)*255).astype(np.uint8),cv2.COLORMAP_MAGMA)
 img=cv2.resize(img,(thumb_w,thumb_h),interpolation=cv2.INTER_AREA)
 tile=np.full((thumb_h+54,thumb_w,3),255,np.uint8)
 tile[54:]=img
 cv2.putText(tile,k,(12,36),cv2.FONT_HERSHEY_SIMPLEX,.88,(15,15,15),2,cv2.LINE_AA)
 panels.append(tile)
while len(panels)%4:panels.append(np.full_like(panels[0],255))
grid=np.concatenate([np.concatenate(panels[i:i+4],axis=1) for i in range(0,len(panels),4)],axis=0)
cv2.imwrite(str(root/'typed_field_panel.png'),grid)
stat={'attribution':'Weiren Hao and Tomohiko Mukai, SIGGRAPH Asia 2026 Posters; independent reconstruction, NOT official code',
      'source':'https://mukai-lab.org/content/SA2026PosterHao.pdf',
      'scene':args.scene,'camera':cams[0].name,'camera_index':0,'output_contract':'per-frame 2D continuous raster fields, no fixed 3D ink',
      'renderer':'existing vanilla GS disc proxy, NOT source RaDe-GS',
      'fragment_count':int(s['n_frag']),'gaussian_count':int(len(g['mu'])),'kept_count':int(keep.sum()),
      'valid_object_pixels':int((s['alpha']>.05).sum()),
      'display_only_p99_positive_S_L':sl_hi,
      'fields':{k:{'p50':float(np.quantile(v,.5)),'p95':float(np.quantile(v,.95)),
                   'p99':float(np.quantile(v,.99)),'nonzero_pixels':int((v>1e-6).sum())} for k,v in fields.items()},
      'figures':['typed_field_panel.png','stroke_density_continuous_ours_display.png','stroke_density_p99_display_only.png','rgb_disc_proxy.png']}
(root/'STATS.json').write_text(json.dumps(stat,indent=2,ensure_ascii=False)+'\n')
print('SCENE',args.scene,'CAMERA',cams[0].name,'FRAGS',s['n_frag'],'S_L_PIXELS',stat['fields']['S_L']['nonzero_pixels'],'S_L_P99',stat['fields']['S_L']['p99'],'PANEL',root/'typed_field_panel.png',flush=True)
del st
if torch.cuda.is_available():torch.cuda.empty_cache()
