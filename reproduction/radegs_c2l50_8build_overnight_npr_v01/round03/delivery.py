from env import *
from experiment import saved,ARMS,load,model
from evaluation import getlab

def centered(im,size=800):
 pi=Image.fromarray(np.uint8(np.clip(im,0,1)*255));pi.thumbnail((size,size));out=Image.new('RGB',(size,size),'white');out.paste(pi,((size-pi.width)//2,(size-pi.height)//2));return np.asarray(out)/255.

def main():
 p=R/'delivery';p.mkdir(exist_ok=True);assert not (p/'SEAL.json').exists();rows=[];overview=[];saturation=[]
 for s in SCENES:
  items=[]
  for v in views(s):
   rgb,z,a=raw(s,v);new=saved(s,v,'pooled_rgb');oldsub=npz(R1/'A'/s/v/'SUBJECT.npz')
   if s=='ficus':
    old=npz(R2/'B/joint_rgb'/('fit' if v in [DEV[s],AUX[s]] else v)/(v+'.npz'));baseline=colors(rgb,old['labels'],old['unknown']);bl='r02 graph'
   else:baseline=overlay(rgb,oldsub['candidate'],oldsub['unknown']);bl='r01 failed subject'
   for label,im in [('Source RGB',rgb),(bl,baseline),('r03 conditional color',colors(rgb,new['labels'],new['unknown']))]:items.append((v+' | '+label,im))
   saturation.append(dict(scene=s,view=v,values_below0=int((rgb<0).sum()),values_above1=int((rgb>1).sum()),pixels_outside_0_1=int(((rgb<0)|(rgb>1)).any(2).sum()),min=float(rgb.min()),max=float(rgb.max()),feature_policy='integer RGB histogram indices saturate to edge bins; no raw edit'))
   for arm in ARMS:rows.append(json.loads((R/'inference'/s/arm/v/'COUNT.json').read_text()))
   if v==DEV[s]:
    for label,im in [('Source RGB',rgb),(bl,baseline),('r03 conditional color',colors(rgb,new['labels'],new['unknown']))]:overview.append((s+' | '+label,centered(im)))
  panel(p/(s+'_FOUR_VIEWS.jpg'),items,s+' | r03 fixed four-view comparison','All historically exposed. Diagnostic colors only; no GS edits. Ficus: pot/wood/crown priors; DTU: peripheral/central appearance proxies, NOT parts.',3)
 panel(p/'OVERVIEW.jpg',overview,'r03 | Nonlocal appearance: Ficus partial signal, DTU subject not qualified','Original source / preceding method / new fixed inference. No source groups, no NPR styles, no new Gaussian model.',3)
 # Failure crops are selected only for explanation after frozen inference; not selectors.
 crops=[('ficus','train_r_80',(.29,.57,.60,.86),'Pot highlight is not wood'),('ficus','test_r_79',(.29,.58,.62,.88),'Soil / pot rim / wood ambiguity'),('scan24','0036',(.08,.08,.73,.66),'Roof and background share appearance'),('scan65','0036',(.20,.48,.87,.98),'Dark bone / teeth confused with table')]
 croprows=[]
 for s,v,(x0,y0,x1,y1),title in crops:
  rgb,_,_=raw(s,v);h,w=rgb.shape[:2];box=(int(x0*w),int(y0*h),int(x1*w),int(y1*h));im=[]
  for name,a in [('Source RGB',rgb),('pooled_rgb',colors(rgb,saved(s,v,'pooled_rgb')['labels'],saved(s,v,'pooled_rgb')['unknown'])),('dev_only',colors(rgb,saved(s,v,'dev_only')['labels'],saved(s,v,'dev_only')['unknown']))]:im.append((name,a[box[1]:box[3],box[0]:box[2]]))
  fn=s+'_'+v+'_FAILURE.jpg';panel(p/fn,im,title+' | '+s+' / '+v,'Posthoc explanatory crop only; full native frames retained. No GT labels, no ROI filtering.',3);croprows.append(dict(scene=s,view=v,xyxy=box,path=fn,after_inference_diagnostic_only=True))
 js(p/'CROPS.json',croprows);js(p/'RGB_DOMAIN.json',saturation)
 # Map new assignments over old UNKNOWN without calling them recovered true parts.
 diffs=[]
 for v in views('ficus'):
  rgb,_,_=raw('ficus',v);n=saved('ficus',v,'pooled_rgb');dv=saved('ficus',v,'dev_only');b=getlab(v,'r02_graph');mask=load('ficus',v)['mask'];newknown=mask&(b==0)&(n['labels']>0);lost=mask&(b>0)&(n['labels']==0);change=mask&(b>0)&(n['labels']>0)&(b!=n['labels']);out=rgb.copy();out[newknown]=.3*out[newknown]+.7*np.array([.1,.8,1]);out[lost]=.3*out[lost]+.7*np.array([.8,.1,.8]);out[change]=.3*out[change]+.7*np.array([1,.6,0]);panel(p/('CHANGE_'+v+'.jpg'),[('Source RGB',rgb),('Change vs r02 graph',out),('New fixed labels',colors(rgb,n['labels'],n['unknown']))],v+' | Attribution of changed coverage','Cyan: old UNKNOWN now labeled; purple: newly UNKNOWN; orange: changed known class. NONE is a GT correctness claim.',3)
  both=(dv['labels']>0)&(n['labels']>0)&mask;diffs.append(dict(view=v,old_unknown_new_known=int(newknown.sum()),old_known_new_unknown=int(lost.sum()),both_known_changed=int(change.sum()),pooled_vs_dev_different=int((n['labels']!=dv['labels']).sum()),pooled_dev_both_known_changed=int((both&(n['labels']!=dv['labels'])).sum()),pooled_newly_known_over_dev=int((mask&(dv['labels']==0)&(n['labels']>0)).sum())))
 js(p/'ARM_DIFFERENCES.json',diffs)
 js(R/'COUNTS.json',dict(scenes=3,views_per_scene=4,inference_arms=3,native_inference_outputs=len(rows),models=9,crossfit_directions=6,new_tests=20,original_GS_modified=0,new_GS_models=0,source_roles=0,styles=0,rows=rows));seal(p);print(json.dumps(dict(inference_count=len(rows),differences=diffs,resources=guard()),indent=2))
if __name__=='__main__':main()
