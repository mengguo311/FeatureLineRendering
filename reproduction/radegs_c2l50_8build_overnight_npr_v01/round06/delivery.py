from env import *
from experiment import ARMS,result,shape,old,heat

def centered(im,size=600):
 p=Image.fromarray(np.uint8(np.clip(im,0,1)*255));p.thumbnail((size,size));out=Image.new('RGB',(size,size),'white');out.paste(p,((size-p.width)//2,(size-p.height)//2));return np.asarray(out)/255.
def main():
 p=R/'delivery'
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(exist_ok=True);overview=[]
 for s in SCENES:
  items=[]
  for v in views(s):
   rgb,_,_=raw(s,v);a=shape(s,v);prior=old(s,v)
   if s=='ficus':
    ims=[('Source RGB',rgb),('r03 RGB-only | paired',colors(rgb,result(s,v,'rgb')['labels'],result(s,v,'rgb')['unknown'])),('r06 RGB + morphology',colors(rgb,result(s,v,'rgb_morph')['labels'],result(s,v,'rgb_morph')['unknown'])),('r05 graph | strong context',colors(rgb,prior['labels'],prior['unknown']))]
   else:ims=[('Source RGB',rgb),('r05 | subject not complete',colors(rgb,prior['labels'],prior['unknown'])),('SCENE coverage, NOT subject',np.repeat(np.where(a['subject_unknown'],.5,a['candidate'])[...,None],3,2)),('New morphology | NOT part labels',heat(a['feature'][...,2]))]
   for title,im in ims:
    items.append((v+' | '+title,im))
    if v==DEV[s]:overview.append((s+' | '+title,centered(im)))
  panel(p/(s+'_FOUR_VIEWS.jpg'),items,s+' | r06: negative-space information qualification','Native full frames; no model edits. Ficus morphology adds uncertainty; DTU has no valid subject shape input.',4)
 panel(p/'OVERVIEW.jpg',overview,'r06 | New morphology evidence; no new GS parts or NPR styles','DTU: whole-scene coverage cannot identify subject shape. Ficus: compare matched RGB baseline and strong graph reference.',4)
 crops=json.loads((R5/'delivery/CROPS.json').read_text());crops=[c for c in crops if c['scene']=='ficus']
 for c in crops:
  s,v=c['scene'],c['view'];x0,y0,x1,y1=c['xyxy'];rgb,_,_=raw(s,v);ims=[('Source RGB',rgb)]
  for arm in ARMS:
   a=result(s,v,arm);ims.append((arm,colors(rgb,a['labels'],a['unknown'])))
  panel(p/c['path'],[(title,im[y0:y1,x0:x1]) for title,im in ims],s+' / '+v+' | Same inherited failure crop','Explanatory crop only. Shape cannot identify hidden wood by itself; full frames retained.',4)
 js(p/'CROPS.json',crops)
 counts=[json.loads(f.read_text()) for f in (R/'inference').rglob('COUNT.json')];shapes=[json.loads(f.read_text()) for f in (R/'shape').rglob('COUNT.json')]
 js(R/'COUNTS.json',dict(scenes_with_actual_measurement=3,shape_views=len(shapes),ficus_new_native_predictions=len(counts),fit_arms=len(ARMS),reserved_predictions=6,DTU_new_part_predictions=0,stage_not_run=['DTU B','C','D','NPR'],rows=counts,input_qualification=shapes,new_GS_models=0,new_source_roles=0,new_line_groups=0,styles=0,children=[]));seal(p)
if __name__=='__main__':main()
