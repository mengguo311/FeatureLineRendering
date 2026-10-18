from env import *
from experiment import result,old,ARMS,seed_data
from audit_metrics import compare,overlap

def pad(items):
 h=max(a.shape[0] for _,a in items);w=max(a.shape[1] for _,a in items);out=[]
 for t,a in items:
  b=np.ones((h,w,3),dtype=a.dtype);b[:a.shape[0],:a.shape[1]]=a;out.append((t,b))
 return out

def main():
 status('DELIVERY',children=[os.getpid()]);p=R/'delivery';p.mkdir(exist_ok=True);stats=[];hist=[];overview=[]
 for s in SCENES:
  items=[]
  for v in views(s):
   rgb,_,_=raw(s,v);a=result(s,v,'raw_rgb');c=result(s,v,'chromaticity');g=old(s,v);row=[(s+'/'+v+' | Original RGB',rgb),('Raw RGB | fixed proxy seeds',colors(rgb,a['labels'],a['unknown'])),('Chromaticity | new candidate',colors(rgb,c['labels'],c['unknown'])),('r05 graph | strong baseline',colors(rgb,g['labels'],g['unknown']))];items+=row
   if v==DEV[s]:overview+=row
   for arm in ARMS:
    x=result(s,v,arm);m=x['inference_mask'];f=result(s,v,'rgb_floor');r=json.loads((R/'inference'/s/arm/v/'COUNT.json').read_text());r.update(relative_to_raw=compare(a['labels'],x['labels'],m),relative_to_same_floor=compare(f['labels'],x['labels'],m));stats.append(r)
  legend='Blue pot-prior / orange wood-prior / green crown-prior / gray UNKNOWN.' if s=='ficus' else 'Blue peripheral-horizontal prior / orange central-nonhorizontal prior / gray UNKNOWN; NOT semantic parts.'
  panel(p/(s+'_FOUR_VIEWS.jpg'),items,s+' | Four historically exposed views | no tuning',legend+' Native frames; diagnostic overlays, not styled GS.',4)
  for arm in ARMS:
   m=npz(R/'models'/s/arm/'MODEL.npz');hist.append(dict(scene=s,arm=arm,overlap=overlap(m['hist']).tolist(),threshold=m['threshold'].tolist()))
 panel(p/'OVERVIEW.jpg',pad(overview),'r08 | Scalar intensity quotient: preserve shape or erase evidence?','Native frames padded white only. No new GS models or NPR. Color labels are proxy priors, not physical parts.',4)
 # Post-result diagnostic crops only; never used for selection/training.
 rois={'ficus':('test_r_14',(270,430,540,720)),'scan24':('0036',(0,0,500,400)),'scan65':('0036',(130,0,670,510))};roi_receipt={}
 for s,(v,(x0,y0,x1,y1)) in rois.items():
  rgb,_,_=raw(s,v);rr=[('Original RGB',rgb)]
  for arm in ['raw_rgb','rgb_floor','chromaticity','shuffled_chromaticity']:
   a=result(s,v,arm);rr.append((arm,colors(rgb,a['labels'],a['unknown'])))
  a=old(s,v);rr.append(('r05 historical graph',colors(rgb,a['labels'],a['unknown'])))
  panel(p/(s+'_FAILURE_ROI.jpg'),[(t,a[y0:y1,x0:x1]) for t,a in rr],s+'/'+v+' | Post-result diagnostic ROI','Crop is explanatory only, NOT a selection mask. Full frame retained in FOUR_VIEWS and figures.',3);roi_receipt[s]=dict(view=v,xyxy=[x0,y0,x1,y1],post_result_diagnostic=True)
 js(p/'ROI_RECEIPT.json',roi_receipt);js(R/'COUNTS.json',dict(predictions=stats,models=hist,model_count=len(hist),prediction_count=len(stats),new_GS_models=0,source_membership='NOT_RUN',NPR='NOT_RUN',new_source_renders=0));seal(p);status('DELIVERY_DONE',children=[])
if __name__=='__main__':main()
