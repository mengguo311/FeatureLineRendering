"""Review actual full-lamp and isolated raster crops with frozen probe labels."""
from common import *
from PIL import Image,ImageDraw
from run_unit002 import contact
U=OUT.parent/'unit_007'
COLORS={'visible':(0,160,0),'eligible':(0,160,0),'hidden':(210,30,30),'boundary':(160,120,0),'ambiguous':(130,30,170),'unmeasured':(80,80,80),'outside':(0,0,0)}
def main():
 selection=json.loads((U/'SAMPLE_SELECTION.json').read_text())['selected'];trajectories=json.loads((U/'TRAJECTORIES.json').read_text())
 for seq,cameras in trajectories.items():
  rows={}
  for c in cameras:
   i=c['frame'];rows[i]={r['stroke_id']:r for r in json.loads((U/'raw'/f'{seq}_{i:04}.json').read_text())}
  for si,item in enumerate(selection):
   sid=item['id'];paths=[];labels=[]
   for c in cameras:
    i=c['frame'];row=rows[i][sid];raw=row['samples'];uv=np.array(raw['uv']);lo=np.floor(uv.min(axis=0)-8).astype(int);hi=np.ceil(uv.max(axis=0)+9).astype(int)
    box=tuple([max(0,int(lo[0])),max(0,int(lo[1])),min(512,int(hi[0])),min(512,int(hi[1]))])
    ink=np.array(Image.open(U/'isolated'/seq/sid/f'{i:04}.png'))
    im=Image.fromarray(255-ink).convert('RGB');draw=ImageDraw.Draw(im)
    for point,cls in zip(uv,raw['class']):
     x,y=point;draw.ellipse((x-1,y-1,x+1,y+1),fill=COLORS.get(cls,(70,70,70)))
    dest=U/'figures'/'probe_crops'/seq/f'{si:02}_{i:04}.png';dest.parent.mkdir(parents=True,exist_ok=True);im.crop(box).save(dest);paths.append(dest);labels.append(f'{seq}{i:02} | {item["stratum"]}')
   contact(paths,labels,U/'figures'/f'{seq}_probe_{si:02}_all.png',columns=6,thumb=160)
  for i in (0,len(cameras)//2,len(cameras)-1):
   paths=[];labels=[]
   for si,item in enumerate(selection):
    paths.append(U/'figures'/'probe_crops'/seq/f'{si:02}_{i:04}.png');labels.append(f'p{item["part"]} {item["id"][7:11]} {item["stratum"]}')
   contact(paths,labels,U/'figures'/f'{seq}_{i:04}_all_probes.png',columns=6,thumb=192)
  # Plain part crops expose output quality without colored sample markers.
  for part,pname in ((1,'shade'),(2,'stem'),(3,'base')):
   paths=[];labels=[]
   for c in cameras:
    i=c['frame'];a=np.load(U/'frames'/seq/f'{i:04}_reference.npz');ys,xs=np.where(a['parts']==part)
    if not len(xs):continue
    box=(max(0,int(xs.min())-8),max(0,int(ys.min())-8),min(512,int(xs.max())+9),min(512,int(ys.max())+9))
    dest=U/'figures'/'part_crops'/seq/f'{pname}_{i:04}.png';dest.parent.mkdir(parents=True,exist_ok=True)
    with Image.open(U/'frames'/seq/f'{i:04}.png') as im:im.crop(box).save(dest)
    paths.append(dest);labels.append(f'{pname} {seq}{i:02}')
   contact(paths,labels,U/'figures'/f'{seq}_{pname}_all.png',columns=6,thumb=192)
 write_json(U/'FIGURE_LEGEND.json',dict(colors=COLORS,interpretation='Actual isolated ink inverted for display; colored midpoint markers show geometry-only classification. Markers can obscure thin ink; raw isolated PNGs remain available. Green=eligible, red=hidden, amber=boundary, purple=ambiguity. Full lamp/part sheets have no markers.',scope='All18 sampled IDs/all36 frames preserved; selection not based on results.'))
if __name__=='__main__':main()
