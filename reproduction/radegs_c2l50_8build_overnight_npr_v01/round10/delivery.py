from env import *
from experiment import result,old,ARMS
from audit_metrics import compare,overlap
def pad(items):
 h=max(a.shape[0] for _,a in items);w=max(a.shape[1] for _,a in items);out=[]
 for t,a in items:
  b=np.ones((h,w,3),dtype=a.dtype);b[:a.shape[0],:a.shape[1]]=a;out.append((t,b))
 return out
def main():
 status('DELIVERY',children=[os.getpid()]);p=R/'delivery';p.mkdir(exist_ok=False);stats=[];models=[];features=[];overview=[]
 for s in SCENES:
  items=[]
  for v in views(s):
   rgb,_,_=raw(s,v);rawref=result(s,v,'raw_rgb');u=result(s,v,'rgb_texture');a=result(s,v,'alpha_texture');n=result(s,v,'shifted_alpha_texture');g=old(s,v);row=[(s+'/'+v+' | Original RGB',rgb),('r09 unconditional | readonly',colors(rgb,u['labels'],u['unknown'])),('r10 alpha-supported texture',colors(rgb,a['labels'],a['unknown'])),('r10 shifted-alpha null',colors(rgb,n['labels'],n['unknown'])),('r05 graph | strong readonly context',colors(rgb,g['labels'],g['unknown']))];items+=row
   if v==DEV[s]:overview+=row
   features.append(json.loads((R/'features'/s/v/'COUNT.json').read_text()))
   for arm in ARMS:
    x=result(s,v,arm);m=x['inference_mask'];r=json.loads((R/'inference'/s/arm/v/'COUNT.json').read_text());r.update(relative_to_raw=compare(rawref['labels'],x['labels'],m),relative_to_unconditional=compare(u['labels'],x['labels'],m),relative_to_null=compare(n['labels'],x['labels'],m));stats.append(r)
  legend='Blue pot / orange wood / green crown PROXIES.' if s=='ficus' else 'Blue peripheral-horizontal / orange central-nonhorizontal PROXIES, NOT semantic foreground.'
  panel(p/(s+'_FOUR_VIEWS.jpg'),items,s+' | Four historical views | r10 observation support',legend+' Gray UNKNOWN. Original mask/gain/native pixels unchanged.',5)
  for arm in ARMS:
   m=npz(R/'models'/s/arm/'MODEL.npz');models.append(dict(scene=s,arm=arm,texture_overlap=overlap(m['texture_hist']).tolist(),threshold=m['threshold'].tolist()))
 panel(p/'OVERVIEW.jpg',pad(overview),'r10 | Does finite source coverage prevent background texture mixing?','Alpha is scene coverage, NOT semantic segmentation. Native frames padded only. No source/ink edit or NPR.',5)
 rois={'ficus':('test_r_14',(270,380,540,720)),'scan24':('0036',(0,0,520,420)),'scan65':('0036',(130,0,670,510))};receipt={}
 for s,(v,(x0,y0,x1,y1)) in rois.items():
  rgb,_,_=raw(s,v);items=[('Original RGB',rgb)]
  for arm in ['raw_rgb','rgb_texture',*ARMS]:
   a=result(s,v,arm);items.append((arm,colors(rgb,a['labels'],a['unknown'])))
  a=old(s,v);items.append(('r05 graph',colors(rgb,a['labels'],a['unknown'])))
  panel(p/(s+'_FAILURE_ROI.jpg'),[(t,a[y0:y1,x0:x1]) for t,a in items],s+'/'+v+' | Fixed explanatory crop from r09','Not algorithm ROI or mask. Full frames retained; same gain and labels.',3);receipt[s]=dict(view=v,xyxy=[x0,y0,x1,y1],diagnostic_only=True,inherited_r09=True)
 a=npz(R/'analytic/COUNTERFACTUAL.npz');items=[(k,np.repeat(np.repeat(a[k],3,axis=0),3,axis=1)) for k in ['rgb_white','rgb_noise','normalized_white','normalized_noise','unconditional_white','unconditional_noise']]
 panel(p/'ANALYTIC.jpg',items,'Analytic control | same thin object, changed background','Synthetic mechanism test only. Nearest-neighbor display enlargement; saved numeric arrays unchanged.',3)
 js(p/'ROI_RECEIPT.json',receipt);js(R/'COUNTS.json',dict(features=features,models=models,predictions=stats,new_model_count=len(models),new_prediction_count=len(stats),new_feature_view_count=len(features),readonly_baseline_predictions=24,new_GS_models=0,new_source_renders=0,NPR='NOT_RUN'));seal(p);status('DELIVERY_DONE',children=[])
if __name__=='__main__':main()
