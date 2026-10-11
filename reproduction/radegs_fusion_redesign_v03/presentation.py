from common import *
from PIL import Image,ImageDraw,ImageFont
T=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/fusion_redesign_v03');d=T/'roi_pilot';a=json.loads((d/'RESULTS.json').read_text());font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
for v,r in a['render_checks'].items():
 box=tuple(r['window']);names=[v+'_full_original_spatial.png',v+'_raw.png',v+'_initial.png',v+'_fit.png'];labels=['Original Spatial RGB target','All-pixel raw (local ROI only)','Skeleton dictionary: initial','Joint opacity fit: fixed geometry'];images=[Image.open(d/n).convert('RGB').crop(box) for n in names];cw,ch=images[0].size;scale=3;cw*=scale;ch*=scale
 canvas=Image.new('RGB',(cw*2,(ch+32)*2+58),'white');draw=ImageDraw.Draw(canvas);draw.text((10,8),f'{v} / fixed center ROI pilot / 3x nearest-pixel display',font=font,fill='black');draw.text((10,31),'No heldout used; not a complete reconstruction',font=font,fill='black')
 for i,(im,label) in enumerate(zip(images,labels)):
  x=i%2*cw;y=58+i//2*(ch+32);draw.text((x+6,y+5),label,font=font,fill='black');canvas.paste(im.resize((cw,ch),Image.Resampling.NEAREST),(x,y+32))
 canvas.save(d/f'{v}_readable_3x.png')
print('Three additional presentation-only panels. Original raw renders remain unchanged.')
s=T/'synthetic';raw=Image.open(s/'duplicate_ink_negative_control.png').convert('RGB');stats=json.loads((s/'RESULTS.json').read_text())['observations'];canvas=Image.new('RGB',(760,4*(324+34)+60),'white');draw=ImageDraw.Draw(canvas);draw.text((10,10),'Identical observations -> duplicate fixed Gaussian kernels',font=font,fill='black');draw.text((10,33),'4x nearest-pixel display; synthetic mechanism control',font=font,fill='black')
for i,r in enumerate(stats):
 y=60+i*358;draw.text((10,y+5),f"repeat {r['repeat']}: {r['gaussians']} kernels / center darkness {r['center_darkness']:.6f}",font=font,fill='black');body=raw.crop((0,65+i*113+32,161,65+i*113+32+81));canvas.paste(body.resize((644,324),Image.Resampling.NEAREST),(50,y+34))
canvas.save(s/'duplicate_ink_readable.png')
