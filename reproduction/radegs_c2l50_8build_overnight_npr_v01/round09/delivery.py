from env import *
from experiment import result,old,ARMS
from audit_metrics import compare,overlap

def pad(items):
 h=max(a.shape[0] for _,a in items);w=max(a.shape[1] for _,a in items);out=[]
 for t,a in items:
  b=np.ones((h,w,3),dtype=a.dtype);b[:a.shape[0],:a.shape[1]]=a;out.append((t,b))
 return out

def main():
 status('DELIVERY',children=[os.getpid()]);p=R/'delivery';p.mkdir(exist_ok=True);stats=[];models=[];overview=[]
 for s in SCENES:
  items=[]
  for v in views(s):
   rgb,_,_=raw(s,v);a=result(s,v,'raw_rgb');b=result(s,v,'rgb_texture');n=result(s,v,'rgb_scrambled_texture');g=old(s,v);row=[(s+'/'+v+' | Original RGB',rgb),('Raw RGB | fixed proxy seeds',colors(rgb,a['labels'],a['unknown'])),('RGB + texture | new candidate',colors(rgb,b['labels'],b['unknown'])),('Shuffled texture | same color budget',colors(rgb,n['labels'],n['unknown'])),('r05 graph | strong context',colors(rgb,g['labels'],g['unknown']))];items+=row
   if v==DEV[s]:overview+=row
   for arm in ARMS:
    x=result(s,v,arm);m=x['inference_mask'];r=json.loads((R/'inference'/s/arm/v/'COUNT.json').read_text());r.update(relative_to_raw=compare(a['labels'],x['labels'],m),relative_to_shuffled=compare(n['labels'],x['labels'],m));stats.append(r)
  legend='Blue pot-prior / orange wood-prior / green crown-prior / gray UNKNOWN.' if s=='ficus' else 'Blue peripheral-horizontal prior / orange central-nonhorizontal prior / gray UNKNOWN. NOT semantic parts.'
  panel(p/(s+'_FOUR_VIEWS.jpg'),items,s+' | Four historically exposed views',legend+' Fixed gain/native pixels, diagnostic overlays only.',5)
  for arm in ARMS:
   m=npz(R/'models'/s/arm/'MODEL.npz');models.append(dict(scene=s,arm=arm,texture_overlap=overlap(m['texture_hist']).tolist(),rgb_overlap=overlap(m['rgb_hist']).tolist(),threshold=m['threshold'].tolist()))
 panel(p/'OVERVIEW.jpg',pad(overview),'r09 | Does local texture layout resolve coarse part identity?','Native frames padded white only. Same original RGB, seeds and masks. No source/line edits or NPR.',5)
 rois={'ficus':('test_r_14',(270,380,540,720)),'scan24':('0036',(0,0,520,420)),'scan65':('0036',(130,0,670,510))};receipts={}
 for s,(v,(x0,y0,x1,y1)) in rois.items():
  rgb,_,_=raw(s,v);items=[('Original RGB',rgb)]
  for arm in ARMS:
   a=result(s,v,arm);items.append((arm,colors(rgb,a['labels'],a['unknown'])))
  a=old(s,v);items.append(('r05 historical graph',colors(rgb,a['labels'],a['unknown'])))
  panel(p/(s+'_FAILURE_ROI.jpg'),[(t,a[y0:y1,x0:x1]) for t,a in items],s+'/'+v+' | Post-result failure detail','Diagnostic crop only, never selection/training mask. Full frame retained in FOUR_VIEWS.',3);receipts[s]=dict(view=v,xyxy=[x0,y0,x1,y1],post_result=True)
 js(p/'ROI_RECEIPT.json',receipts);js(R/'COUNTS.json',dict(predictions=stats,models=models,texture_views=12,texture_fields=24,model_count=len(models),prediction_count=len(stats),new_GS_models=0,new_source_renders=0,source_membership='NOT_RUN',NPR='NOT_RUN'));seal(p);status('DELIVERY_DONE',children=[])
if __name__=='__main__':main()
