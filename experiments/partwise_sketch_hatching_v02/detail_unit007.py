"""Post-evaluation explanatory figure; no metric, input or threshold changes."""
from common import *
from PIL import Image,ImageDraw
U=OUT.parent/'unit_007'
def main():
 rows={r['stroke_id']:r for r in json.loads((U/'raw/orbit_0000.json').read_text())}
 ids=['p1:seed0099:layer0','p2:seed0021:layer0','p3:seed0048:layer1']
 canvas=Image.new('RGB',(1040,930),'white');d=ImageDraw.Draw(canvas)
 records=[]
 for index,sid in enumerate(ids):
  row=rows[sid];uv=np.array(row['samples']['uv']);lo=np.floor(uv.min(axis=0)-6).astype(int);hi=np.ceil(uv.max(axis=0)+7).astype(int)
  box=(max(0,int(lo[0])),max(0,int(lo[1])),min(512,int(hi[0])),min(512,int(hi[1])))
  y=index*310;d.text((8,y+6),f'{sid} | orbit00 | pooled ID status: UNMEASURED',fill='black')
  d.text((8,y+24),f'Frame classes: {row["summary"]["class_counts"]}',fill='black')
  full=Image.open(U/'frames/orbit/0000.png').convert('RGB');fd=ImageDraw.Draw(full);fd.rectangle(box,outline=(180,0,180),width=2);full=full.resize((256,256));canvas.paste(full,(8,y+48))
  ink=np.array(Image.open(U/'isolated/orbit'/sid/'0000.png'));plain=Image.fromarray(255-ink).convert('RGB').crop(box)
  annotated=Image.fromarray(255-ink).convert('RGB');draw=ImageDraw.Draw(annotated)
  colors={'visible':(0,160,0),'hidden':(220,0,0),'boundary':(170,120,0),'ambiguous':(130,30,170)}
  for (x0,y0),cls in zip(uv,row['samples']['class']):draw.ellipse((x0-1,y0-1,x0+1,y0+1),fill=colors.get(cls,'gray'))
  marked=annotated.crop(box)
  for col,im,label in ((280,plain,'Actual isolated ink'),(650,marked,'Geometry classes; green eligible')):
   scale=min(340/im.width,225/im.height);im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.NEAREST);canvas.paste(im,(col,y+70));d.text((col,y+50),label,fill='black')
  records.append(dict(stroke_id=sid,frame=0,crop=box,class_counts=row['summary']['class_counts']))
 canvas.save(U/'figures/coverage_limits_enlarged.png')
 write_json(U/'COVERAGE_FIGURE.json',dict(selection='Post-evaluation explanatory choice: one unmeasured low shade, high occluded stem, shortest base; fixed frame0. Not a new test or tuned exclusion.',display='Nearest enlarged crops; display magnification is not physical line width. Purple rectangle is context crop. Markers can hide thin ink, hence plain ink alongside.',rows=records))
if __name__=='__main__':main()
