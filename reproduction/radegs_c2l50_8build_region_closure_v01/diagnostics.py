from env import *
from scipy.ndimage import label
from run import col,region_colors,annotate

def apparent_regions(darkness):
 # White connected components NOT touching ROI border. No closing/dilation/ink edit.
 lab,n=label(darkness<=.2);border=set(np.r_[lab[0],lab[-1],lab[:,0],lab[:,-1]])
 return [lab==i for i in range(1,n+1) if i not in border and (lab==i).sum()>=16]

def graph_image(rgb,fs,ledger,center):
 im=Image.fromarray(np.uint8(np.clip(rgb,0,1)*255));d=ImageDraw.Draw(im)
 for i,f in enumerate(fs):
  u=f['uv'];co=tuple(int(x*255) for x in col(int(f['parent'])));d.line([tuple(x) for x in u],fill=co,width=1)
  for j,ok in zip([0,-1],f['end_ok']):
   x,y=u[j];d.ellipse((x-1,y-1,x+1,y+1),fill=(30,240,30) if ok else (150,150,150))
 for e in ledger:
  if not e.get('accepted',False):continue
  a,b=e['a'],e['b'];p=np.asarray(fs[a//2]['uv'][0 if a%2==0 else -1]);q=np.asarray(fs[b//2]['uv'][0 if b%2==0 else -1]);L=np.linalg.norm(q-p)
  for t in np.arange(0,max(L,1),3):
   aa=p+(q-p)*(t/max(L,1));bb=p+(q-p)*min((t+1.5)/max(L,1),1);d.line([tuple(aa),tuple(bb)],fill=(250,0,200),width=1)
 x,y=center;d.rectangle((x-48,y-48,x+48,y+48),outline=(255,180,0),width=1);return np.asarray(im)/255

def main():
 dst=ROOT/'diagnostics';dst.mkdir(exist_ok=True);rows=[]
 for phase in ['dev','reserved']:
  for s in SCENES:
   for vp in sorted((ROOT/phase/s).glob('*')) if (ROOT/phase/s).exists() else []:
    if not (vp/'SEAL.json').exists():continue
    v=vp.name;c=cam(s,v);raw=npz(rawpath(s,v));ink=npz(vp/'INK_REFERENCE.npz')['rgb'];frame=raw['rgb'].copy();holesframe=raw['rgb'].copy()
    for cp in sorted(vp.iterdir()):
     ap=cp/'original'
     if not (ap/'FRAGMENTS.json').exists():continue
     fs=json.loads((ap/'FRAGMENTS.json').read_text());ledger=json.loads((ap/'LINK_LEDGER.json').read_text());pr=json.loads((ap/'PROVENANCE.json').read_text());center=pr['center_uv'];x,y=np.rint(center).astype(int);box=(max(0,x-48),max(0,y-48),min(c['width'],x+49),min(c['height'],y+49));x0,y0,x1,y1=box
     if x1<=x0 or y1<=y0:continue
     dark=1-ink[y0:y1,x0:x1].mean(2);holes=apparent_regions(dark);hp=raw['rgb'].copy();hm=np.zeros(raw['alpha'].squeeze().shape,np.int32)
     for j,m in enumerate(holes):hp[y0:y1,x0:x1][m]=.5*hp[y0:y1,x0:x1][m]+.5*np.array(col(j));hm[y0:y1,x0:x1][m]=j+1
     gd=graph_image(raw['rgb'],fs,ledger,center);frame=graph_image(frame,fs,ledger,center);holesframe[y0:y1,x0:x1]=hp[y0:y1,x0:x1];out=dst/s/v/cp.name;out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'RASTER_ONLY_HOLES.npz',region_id=hm,never_used_for_source_assignment=np.array(True));save(out/'GRAPH_NATIVE.jpg',gd)
     rs=json.loads((ap/'REGIONS.json').read_text());rs0=json.loads((cp/'no_line'/'REGIONS.json').read_text());mp=npz(cp/'no_line'/'REGION_MASKS.npz')['masks']
     for r,m in zip(rs0,mp):r['mask']=m
     items=[('Original source RGB',raw['rgb']),('Original C8 Gaussian ink | XRAY',ink),('Parents / green ends / magenta links',gd),('Raster holes ONLY; not new evidence',hp),('Graph cycles; gray = UNKNOWN',annotate(raw['rgb'],rs,center)),('No-line regions; not semantic labels',region_colors(raw['rgb'],rs0))]
     zoom=[]
     for title,arr in items:
      im=Image.fromarray(np.uint8(np.clip(arr,0,1)*255)).crop(box).resize((388,388),Image.Resampling.NEAREST);zoom.append((title,np.asarray(im)/255))
     panel(out/'EXPLANATION.jpg',zoom,f'{s} {v} | {cp.name}',f'raster holes {len(holes)} / graph cycles {len(rs)} / qualified {sum(r["qualified"] for r in rs)}',cols=3);rows.append(dict(scene=s,view=v,case=cp.name,raster_holes=len(holes),graph_cycles=len(rs),qualified=sum(r['qualified'] for r in rs),fragments=len(fs),diagnostic_only=True))
    panel(dst/s/v/'FULL_FRAME.jpg',[('Original source RGB',raw['rgb']),('Original C8 ink | XRAY',ink),('Visible parent fragments + hypothetical endpoint links',frame),('Apparent raster holes; no original ink changed',holesframe)],f'{s} {v} | apparent closure vs ordered endpoints','No added ink / all open structures retained / no physical surface inference',cols=2)
 js(dst/'COUNTS.json',rows)
if __name__=='__main__':main()
