from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import sys,json,hashlib
u=Path(sys.argv[1]);mapping=json.loads(Path(sys.argv[2]).read_text());out=Path(sys.argv[3]);out.mkdir(exist_ok=True,parents=True)
def font(n):return ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',n)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
views=['0012','0036'];stages=['original','after'];ims={};provenance=[]
for v in views:
 for s in stages:
  p=u/mapping[v][s];im=Image.open(p).convert('RGB');assert im.size==(777,581);ims[v,s]=im;provenance.append(dict(view=v,stage=s,path=str(p),sha256=sha(p)))
m=24;head=112;label=40;w,h=777,581;W=2*w+3*m;H=head+2*(h+label)+72
panel=Image.new('RGB',(W,H),'#f4f6f8');d=ImageDraw.Draw(panel);d.text((m,16),'Full scan65 line-Gaussian model | center collapse',font=font(32),fill='#172d42');d.text((m,63),'All 279,616 kernels kept / 3,655 existing groups processed / UNKNOWN remains unchanged',font=font(23),fill='#40576a')
for row,v in enumerate(views):
 for col,s in enumerate(stages):
  x=m+col*(w+m);y=head+row*(h+label);d.text((x,y+6),'View '+v+' | '+('ORIGINAL' if s=='original' else 'FULL MODEL: CENTERS ONLY'),font=font(25),fill='#172d42' if col==0 else '#146b39');panel.paste(ims[v,s],(x,y+label));assert panel.crop((x,y+label,x+w,y+label+h)).tobytes()==ims[v,s].tobytes()
d.text((m,H-58),'Same fixed 3D asset in both views. Original covariance, opacity, colors and row IDs preserved.',font=font(22),fill='#40576a');panel.save(out/'FULL_MODEL_BEFORE_AFTER.png')
for v in views:
 boxes=[(0,0,388,290),(388,0,777,290),(0,290,388,581),(388,290,777,581)];cw=778;ch=582;head=112;gap=44;W=2*cw+3*m;H=head+4*(ch+gap)+72;sheet=Image.new('RGB',(W,H),'#f4f6f8');draw=ImageDraw.Draw(sheet);draw.text((m,16),'View '+v+' | all four fixed quadrants',font=font(30),fill='#172d42');draw.text((m,60),'Left: original / Right: centers only / 2x nearest-neighbor display, no selected regions',font=font(23),fill='#40576a')
 for row,box in enumerate(boxes):
  for col,s in enumerate(stages):
   im=ims[v,s].crop(box);im=im.resize((im.width*2,im.height*2),Image.NEAREST);x=m+col*(cw+m);y=head+row*(ch+gap);draw.text((x,y+5),'Q'+str(row+1)+' | '+('ORIGINAL' if col==0 else 'CENTERS ONLY'),font=font(24),fill='#172d42' if col==0 else '#146b39');sheet.paste(im,(x,y+gap));assert sheet.crop((x,y+gap,x+im.width,y+gap+im.height)).tobytes()==im.tobytes()
 draw.text((m,H-58),'All pixels covered once by these four fixed quadrants; original camera frame boundaries retained.',font=font(22),fill='#40576a');sheet.save(out/('VIEW_'+v+'_ALL_QUADRANTS_2X.png'))
(out/'PANEL_PROVENANCE.json').write_text(json.dumps(dict(native_sources=provenance,full_panels_native_scale=True,quadrant_magnification=2,interpolation='nearest',source_pixels_exact=True),indent=2)+'\n')
print('PANELS_CREATED_FROM_EXACT_SAVED_PIXELS')
