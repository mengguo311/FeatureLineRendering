from env import *
from experiment import result,ARMS,old_result

def centered(im,size=800):
 p=Image.fromarray(np.uint8(np.clip(im,0,1)*255));p.thumbnail((size,size));out=Image.new('RGB',(size,size),'white');out.paste(p,((size-p.width)//2,(size-p.height)//2));return np.asarray(out)/255.
def main():
 p=R/'delivery'
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir(exist_ok=True);rows=[];diffs=[];overview=[];seedrows=[]
 for s in SCENES:
  items=[]
  for v in views(s):
   rgb,_,_=raw(s,v);o=old_result(s,v);a=result(s,v,ARMS[0]);b=result(s,v,ARMS[1]);m=a['inference_mask'];K=a['probability'].shape[2];row=dict(scene=s,view=v,r04_unknown=int((m&(o['labels']==0)).sum()),arms={})
   for title,im in [('Source RGB',rgb),('r04 hard seeds',colors(rgb,o['labels'],o['unknown'])),('r05 conflict withdrawal',colors(rgb,a['labels'],a['unknown'])),('r05 random withdrawal',colors(rgb,b['labels'],b['unknown']))]:
    items.append((v+' | '+title,im))
    if v==DEV[s]:overview.append((s+' | '+title,centered(im,600)))
   for arm in ARMS:
    n=result(s,v,arm);both=m&(o['labels']>0)&(n['labels']>0);row['arms'][arm]=dict(unknown=int((m&(n['labels']==0)).sum()),total_label_change=int((m&(o['labels']!=n['labels'])).sum()),both_known_change=int((both&(o['labels']!=n['labels'])).sum()),transitions=np.bincount((o['labels'][m]*(K+1)+n['labels'][m]).astype(int),minlength=(K+1)**2).reshape(K+1,K+1).tolist());rows.append(json.loads((R/'B'/s/arm/('fit' if v in [DEV[s],AUX[s]] else v)/(v+'_COUNT.json')).read_text()))
   row['conflict_vs_random_known_class_change']=int((m&(a['labels']>0)&(b['labels']>0)&(a['labels']!=b['labels'])).sum());diffs.append(row)
   if v in [DEV[s],AUX[s]]:seedrows.extend(json.loads((R/'figures'/s/v/'SEED_COUNTS.json').read_text()))
  panel(p/(s+'_FOUR_VIEWS.jpg'),items,s+' | Fixed four-view, matched seed-withdrawal budget','Native full frames. Gray UNKNOWN; colors are proxy identities, not semantic truth. Source and C8 untouched.',4)
 panel(p/'OVERVIEW.jpg',overview,'r05 | Cross-build-view contradiction versus random hard-seed withdrawal','Source / original hard constraints / contradiction withdrawal / same-count random. No new GS groups or NPR styles.',4)
 crops=json.loads((R4/'delivery/CROPS.json').read_text())
 for c in crops:
  s,v=c['scene'],c['view'];x0,y0,x1,y1=c['xyxy'];rgb,_,_=raw(s,v);ims=[('Source RGB',rgb)];o=old_result(s,v);ims.append(('r04 hard seeds',colors(rgb,o['labels'],o['unknown'])))
  for arm in ARMS:
   n=result(s,v,arm);ims.append((arm,colors(rgb,n['labels'],n['unknown'])))
  panel(p/c['path'],[(n,x[y0:y1,x0:x1]) for n,x in ims],s+' / '+v+' | Same r04 failure crop','Crop inherited from r04, used for explanation only. All native full frames retained; no ROI rule or fitting.',4)
 js(p/'CROPS.json',crops);js(p/'ARM_DIFFERENCES.json',diffs);js(p/'SEED_COUNTS.json',seedrows)
 # Exact correspondence/contrast ledger, original seed UV and accepted alternate-class evidence.
 for s in SCENES:
  for v in [DEV[s],AUX[s]]:
   other=AUX[s] if v==DEV[s] else DEV[s];ev=npz(R3/'crossfit'/s/(other+'_TO_'+v)/'RESULT.npz');conf=(ev['predicted']>0)&(ev['predicted']!=ev['target_seed_labels']);np.savez_compressed(p/(s+'_'+v+'_CONTRADICTIONS.npz'),**ev,contradiction=conf)
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 audit=json.loads((R/'mechanism_audit/COUNTS.json').read_text());fig,axes=plt.subplots(3,2,figsize=(13,10))
 for ix,scene in enumerate(SCENES):
  for iy,arm in enumerate(ARMS):
   rr=[r for r in audit if r['scene']==scene and r['arm']==arm];ax=axes[ix,iy];bottom=np.zeros(len(rr))
   for key,col,lab in [('final_original','#5790b7','Retains original class'),('final_other','#e18437','Different known class'),('final_unknown','#999999','UNKNOWN')]:
    vals=np.array([r[key] for r in rr]);ax.bar([r['view'] for r in rr],vals,bottom=bottom,color=col,label=lab);bottom+=vals
   for j,r in enumerate(rr):ax.text(j,bottom[j]+3,str(r['withdrawn']),ha='center')
   ax.set_ylim(0,max(bottom.max()*1.15,1));ax.set_title(scene+' / '+arm);ax.set_ylabel('Withdrawn hard-seed pixels')
 axes[0,0].legend(fontsize=8);fig.suptitle('r05 | Constraint withdrawal is not label correction (no GT)',fontsize=14);fig.tight_layout();fig.savefig(p/'MECHANISM_COUNTS.jpg',dpi=150);plt.close(fig)
 models=[json.loads(x.read_text()) for x in (R/'B').rglob('MODEL.json')]
 js(R/'COUNTS.json',dict(scenes=3,views_per_scene=4,new_inference_arms=2,native_outputs=len(rows),build_graph_models=6,reserved_inferences=12,new_tests=18,solver_units=len(models),total_solve_seconds=sum(m['seconds'] for m in models),new_GS_models=0,source_roles=0,styles=0,original_GS_modified=0,rows=rows));seal(p)
 print(json.dumps(dict(outputs=len(rows),seed_counts=seedrows,differences=diffs,resources=guard()),indent=2))
if __name__=='__main__':main()
