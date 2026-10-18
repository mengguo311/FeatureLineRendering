from env import *
from experiment import result,ARMS

def centered(im,size=800):
 p=Image.fromarray(np.uint8(np.clip(im,0,1)*255));p.thumbnail((size,size));out=Image.new('RGB',(size,size),'white');out.paste(p,((size-p.width)//2,(size-p.height)//2));return np.asarray(out)/255.

def main():
 p=R/'delivery'
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(exist_ok=True);rows=[];diffs=[];overview=[]
 for s in SCENES:
  items=[]
  for v in views(s):
   rgb,_,_=raw(s,v);n=result(s,v,'coupled');old=npz(R3/'inference'/s/'pooled_rgb'/v/'RESULT.npz');m=n['inference_mask'];K=n['probability'].shape[2]
   for title,im in [('Source RGB',rgb),('r03 appearance only',colors(rgb,old['labels'],old['unknown'])),('r04 coupled inference',colors(rgb,n['labels'],n['unknown']))]:
    items.append((v+' | '+title,im))
    if v==DEV[s]:overview.append((s+' | '+title,centered(im)))
   transitions=np.bincount((old['labels'][m]*(K+1)+n['labels'][m]).astype(int),minlength=(K+1)**2).reshape(K+1,K+1)
   row=dict(scene=s,view=v,r03_to_r04_rows_old_columns_new=transitions.tolist(),r03_unknown=int((m&(old['labels']==0)).sum()),r04_unknown=int((m&(n['labels']==0)).sum()),comparisons={})
   for arm in ARMS:
    a=result(s,v,arm);both=m&(n['labels']>0)&(a['labels']>0);row['comparisons'][arm]=dict(total_label_difference=int((m&(n['labels']!=a['labels'])).sum()),both_known_class_difference=int((both&(n['labels']!=a['labels'])).sum()),unknown=int((m&(a['labels']==0)).sum()));rows.append(json.loads((R/'B'/s/arm/('fit' if v in [DEV[s],AUX[s]] else v)/(v+'_COUNT.json')).read_text()))
   diffs.append(row)
  panel(p/(s+'_FOUR_VIEWS.jpg'),items,s+' | r04 fixed four-view comparison','Gray UNKNOWN. Ficus: blue pot / orange wood / green crown PRIORS. DTU: appearance proxies, NOT parts.',3)
 panel(p/'OVERVIEW.jpg',overview,'r04 | Conditional appearance + qualified spatial graph','Source / r03 / r04. No source or C8 edits; no new GS model, no NPR style. Coherent colors are not certified part identities.',3)
 crops=[('ficus','train_r_80',(.29,.57,.60,.86),'Pot highlight: partial correction'),('ficus','train_r_7',(.22,.15,.71,.58),'Crown-internal wood absorbed by crown prior'),('ficus','test_r_14',(.23,.16,.72,.70),'Leaf / branch and UNKNOWN tradeoff'),('scan24','0036',(.08,.08,.73,.66),'Roof and background remain ambiguous'),('scan65','0036',(.20,.48,.87,.98),'Dark bone / teeth versus table')]
 croprows=[]
 for s,v,(x0,y0,x1,y1),title in crops:
  rgb,_,_=raw(s,v);h,w=rgb.shape[:2];box=(int(x0*w),int(y0*h),int(x1*w),int(y1*h));old=npz(R3/'inference'/s/'pooled_rgb'/v/'RESULT.npz');n=result(s,v,'coupled');ims=[]
  for name,a in [('Source RGB',rgb),('r03 appearance',colors(rgb,old['labels'],old['unknown'])),('r04 coupled',colors(rgb,n['labels'],n['unknown']))]:ims.append((name,a[box[1]:box[3],box[0]:box[2]]))
  fn=s+'_'+v+'_FAILURE.jpg';panel(p/fn,ims,title+' | '+s+'/'+v,'Posthoc explanation only. Full native frames retained; no ROI filtering or tuning.',3);croprows.append(dict(scene=s,view=v,xyxy=box,path=fn,posthoc_explanation_only=True))
 js(p/'CROPS.json',croprows);js(p/'ARM_DIFFERENCES.json',diffs)
 seedrows=[]
 for s in SCENES:
  for v in [DEV[s],AUX[s]]:
   rgb,_,_=raw(s,v);n=result(s,v,'coupled');sl=n['seeds'];old=npz(R3/'inference'/s/'pooled_rgb'/v/'RESULT.npz');conflict=(sl>0)&(old['labels']>0)&(sl!=old['labels']);K=n['probability'].shape[2];ct=np.bincount((old['labels'][conflict]*(K+1)+sl[conflict]).astype(int),minlength=(K+1)**2).reshape(K+1,K+1)
   seedrows.append(dict(scene=s,view=v,hard_seed_count=int((sl>0).sum()),accepted_appearance_conflict=int(conflict.sum()),rows_r03_columns_hardseed=ct.tolist(),not_GT_conflict=True))
   if s=='ficus':
    im=rgb.copy();im[conflict]=[1,0,1];panel(p/('SEEDS_'+v+'.jpg'),[('Source RGB',rgb),('Frozen hard seed proxies only',colors(rgb,sl,np.zeros(sl.shape,bool))),('Magenta: seed versus accepted appearance',im)],v+' | Hard constraints can carry label contamination','Diagnostic conflict is not GT error. No new seeds or target supervision; zero means no hard seed.',3)
 js(p/'SEED_CONFLICTS.json',seedrows)
 for v in views('ficus'):
  rgb,_,_=raw('ficus',v);n=result('ficus',v,'coupled');old=npz(R3/'inference/ficus/pooled_rgb'/v/'RESULT.npz');m=n['inference_mask'];new=m&(old['labels']==0)&(n['labels']>0);lost=m&(old['labels']>0)&(n['labels']==0);change=m&(old['labels']>0)&(n['labels']>0)&(old['labels']!=n['labels']);out=rgb.copy()
  for mask,col in [(new,[.1,.8,1]),(lost,[.8,.1,.8]),(change,[1,.6,0])]:out[mask]=.3*out[mask]+.7*np.array(col)
  panel(p/('CHANGE_'+v+'.jpg'),[('Source RGB',rgb),('Change versus r03',out),('r04 coupled',colors(rgb,n['labels'],n['unknown']))],v+' | Coverage and class changes','Cyan newly labeled; purple newly UNKNOWN; orange changed known class. No color is a GT correctness claim.',3)
 models=[json.loads(x.read_text()) for x in (R/'B').rglob('MODEL.json')]
 js(R/'COUNTS.json',dict(scenes=3,views_per_scene=4,inference_arms=4,native_outputs=len(rows),build_graph_models=12,reserved_inferences=24,new_tests=23,solver_units=len(models),solver_LU_fallback_units=sum('LU_nonzeros' in m for m in models),solver_Jacobi_repair_units=sum('same_matrix_numerical_repair' in m for m in models),total_solve_seconds=sum(m['seconds'] for m in models),original_GS_modified=0,new_GS_models=0,source_roles=0,styles=0,rows=rows));seal(p);print(json.dumps(dict(outputs=len(rows),diffs=diffs,resources=guard()),indent=2))
if __name__=='__main__':main()
