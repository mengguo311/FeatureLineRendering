from env import *
from experiment import ARMS,result,old,rendered
from display_labels import legend

def main():
 d=R/'delivery';d.mkdir(exist_ok=True);items=[]
 for s in SCENES:
  vs=views(s);it=[]
  for v in vs:
   rgb,_,_=raw(s,v);it.append((v+' | original RGB',rgb))
   for arm in ARMS:
    a=result(s,v,arm);it.append((arm+' | '+v,colors(rgb,a['labels'],a['unknown'])))
   native=[('Original cached RGB',rgb)]
   for arm in ARMS:
    a=result(s,v,arm);native.append((arm,colors(rgb,a['labels'],a['unknown'])))
   prev=old(s,v);native.append(('r05 graph | strong historical context',colors(rgb,prev['labels'],prev['unknown'])))
   if s=='ficus':
    vv=npz(V2/'stageB/ficus'/v/'shared_rgb_only_k3.npz');native.append(('v02 RGB-only K3 | historical baseline',colors(rgb,vv['labels'],vv['unknown'])))
   else:
    vv=old(s,v,3);native.append(('r03 pooled RGB | original seed semantics',colors(rgb,vv['labels'],vv['unknown'])))
   nd=d/'native'/s/v;nd.mkdir(parents=True,exist_ok=True)
   panel(nd/'FULL_CORRECTED.jpg',native,s+' / '+v+' | r07 controlled appearance evidence',legend(s),3)
  panel(d/(s+'_FOUR_VIEWS.jpg'),it,s+' | r07 all four historically seen views',legend(s),4)
  v=RES[s][0] if s=='ficus' else DEV[s];rgb,_,_=raw(s,v);items.append((s+' '+v+' | source',rgb))
  for arm in ARMS:
   a=result(s,v,arm);items.append((arm,colors(rgb,a['labels'],a['unknown'])))
 panel(d/'OVERVIEW.jpg',items,'r07 | Does source SH angular appearance explain the partition errors?','Three actual source-only color arms; identical geometry and visibility. These overlays are NOT NPR models.',4)
 # Secondary diagnostic crops only, no classifier mask or tuning input.
 rois={'ficus':dict(view='test_r_14',pot=[220,500,590,790],crown=[140,90,650,510]),'scan24':dict(view='0036',subject_platform=[70,60,715,550]),'scan65':dict(view='0036',skull_table=[130,50,690,560])}
 js(d/'DIAGNOSTIC_ROIS.json',dict(posthoc_visual_only=True,used_for_fit=False,rois=rois))
 for s,rr in rois.items():
  v=rr['view'];rgb,_,_=raw(s,v)
  for name,box in rr.items():
   if name=='view':continue
   x0,y0,x1,y1=box;arr=[('Original RGB',rgb)]
   for arm in ARMS:
    a=result(s,v,arm);arr.append((arm,colors(rgb,a['labels'],a['unknown'])))
   prev=old(s,v);arr.append(('r05 strong graph context',colors(rgb,prev['labels'],prev['unknown'])));arr.append(('DC source appearance',rendered(s,v,'dc_only')['rgb']))
   panel(d/(s+'_'+name+'_FAILURE.jpg'),[(t,a[y0:y1,x0:x1]) for t,a in arr],s+' / '+v+' | '+name+' diagnostic crop',legend(s)+' Crop is inspection only.',3)
 seal(d)
if __name__=='__main__':main()
