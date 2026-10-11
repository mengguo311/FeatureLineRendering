from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
base=Path(__file__).parent
root=base/'delivery/structure_primitive_demo_v04'
out=base/'parent_rgb_overlays_v01';out.mkdir(exist_ok=True)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',24)
rows=[]
for scene in ['scan24','scan65','scan63']:
 for view in ['0000','0012','0024','0036','0048']:
  rgbpath=root/'results'/f'{scene}_full'/f'{view}_rgb_reference.png'
  inkpath=rgbpath.with_name(f'{view}_optimized_ink.png')
  rgb=np.asarray(Image.open(rgbpath).convert('RGB'),dtype=np.float32)/255
  trans=np.asarray(Image.open(inkpath).convert('RGB'),dtype=np.float32)/255
  assert rgb.shape==trans.shape
  # Native black-ink transmittance; no per-view normalization/opacity adjustment.
  black=rgb*trans
  opacity=1-trans[...,0:1]
  red=rgb*(1-opacity)+np.array([1,0,0],dtype=np.float32)*opacity
  images=[Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)) for a in [rgb,black,red]]
  for suffix,im in zip(['rgb','black_overlay','red_diagnostic'],images):
   im.save(out/f'{scene}_{view}_{suffix}.png')
  w,h=images[0].size
  canvas=Image.new('RGB',(w*3,h+78),'white');d=ImageDraw.Draw(canvas)
  for i,(label,im) in enumerate(zip(['Original Gaussian model RGB','RGB + optimized black Gaussian ink','RGB + red ink (alignment diagnostic)'],images)):
   d.text((i*w+10,10),label,font=font,fill='black');d.text((i*w+10,42),scene+' / camera '+view,font=font,fill='black');canvas.paste(im,(i*w,78))
  canvas.save(out/f'{scene}_{view}_comparison.jpg',quality=95)
  rows.append({'scene':scene,'camera':view,'rgb_sha256':hashlib.sha256(rgbpath.read_bytes()).hexdigest(),'ink_sha256':hashlib.sha256(inkpath.read_bytes()).hexdigest(),'shape':list(rgb.shape),'black_formula':'rgb * native_ink_transmittance','red_formula':'rgb * T + red * (1-T)','scene_depth_occlusion':'inherited from exact-camera ink render; approximate EWA, not joint GS depth-sort'})
assert len(rows)==15
manifest={'method':'same-camera existing render composition; fixed 3D ink, no detector rerun or scene edit','count':len(rows),'rows':rows,'outputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()}}
(out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2))
import zipfile
with zipfile.ZipFile(out/'RGB_OVERLAYS.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(out.iterdir()):
  if p.suffix in ['.jpg','.json']:z.write(p,p.name)
with zipfile.ZipFile(out/'RGB_OVERLAYS.zip') as z:assert z.testzip() is None
print(json.dumps({'cameras':len(rows),'panels':len(list(out.glob('*comparison.jpg'))),'package':str(out/'RGB_OVERLAYS.zip')}))
