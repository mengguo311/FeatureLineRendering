"""Post-hoc fixed-view depth outlier audit; preserves original masks and gates."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'): os.environ[key]='2'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import json
import numpy as np
from scipy import ndimage
from PIL import Image,ImageDraw
import core
W=Path(__file__).resolve().parents[2]
R=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_001')
cfg=json.loads((W/'docs/partwise_sketch_hatching/round_001/PROTOCOL.json').read_text())
m=np.load(R/'assets/lamp_mesh.npz');mesh=core.finalize_mesh(m['vertices'],m['faces'],m['parts'])
c=core.camera(30,20,4.5,1024,1200)
depth,parts=core.raster_surface(mesh,c);depth=depth[::2,::2];parts=parts[::2,::2]
ref=np.load(R/'references/analytic_az030.npz');rd=ref['depth'];rp=ref['parts']
interior=ndimage.distance_transform_edt(~core.contour_mask(rp))>2
valid=(rp>0)&(parts>0)&interior&np.isfinite(rd)&np.isfinite(depth)
error=np.zeros_like(depth);error[valid]=abs(rd[valid]-depth[valid])
y,x=np.nonzero(valid&(error>.01))
records=[{'x':int(xx),'y':int(yy),'analytic_depth':float(rd[yy,xx]),'mesh_depth':float(depth[yy,xx]),'part_reference':int(rp[yy,xx]),'part_mesh':int(parts[yy,xx]),'absolute_error_world':float(error[yy,xx])} for yy,xx in zip(y,x)]
value={'scope':'Post-hoc diagnostic replay of azimuth 30, same source/asset/camera, no change to frozen p95 gate or exclusions','valid_pixels':int(valid.sum()),'pixels_above_frozen_0_01_world_threshold':len(records),'outliers':records}
(R/'DEPTH_AUDIT.json').write_text(json.dumps(value,indent=2)+'\n')
panel=Image.new('RGB',(1024,552),'white');draw=ImageDraw.Draw(panel)
base=Image.open(R/'stills/mixed_az030.png').convert('RGB');overlay=base.copy();d=ImageDraw.Draw(overlay)
for yy,xx in zip(y,x): d.ellipse((xx-3,yy-3,xx+3,yy+3),fill='red')
heat=np.ones((512,512,3));q=np.clip(error/.01,0,1);heat[...,1]-=q;heat[...,2]-=q
panel.paste(overlay,(0,40));panel.paste(Image.fromarray(np.uint8(heat*255)),(512,40))
draw.text((10,12),'Depth outliers > 0.01 world (red markers enlarged)',fill='black')
draw.text((522,12),'Absolute depth error / 0.01 (clipped at red)',fill='black')
panel.save(R/'figures/depth_outlier_audit.png')
print(json.dumps(value,indent=2))
