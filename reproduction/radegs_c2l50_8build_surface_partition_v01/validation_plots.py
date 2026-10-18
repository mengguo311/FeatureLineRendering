from env import *
from plots import responsibility_render,marked,plot_image,plt
from responsibility import measure_difference
from measure import unique_rows

def reordered_evidence(e,v):
 z={k:q.copy() for k,q in e.items()};rows=[dict(ids=e['source_index'][lo:hi],weight=v['reordered_weight'][lo:hi]) for lo,hi in zip(e['csr_offsets'][:-1],e['csr_offsets'][1:])];lr,_=unique_rows(rows,e['query_uv'],e['side_offset']<0);rr,_=unique_rows(rows,e['query_uv'],e['side_offset']>0);d=measure_difference(lr,rr);z.update(participant_ids=d['ids'],left_mass=d['left'],right_mass=d['right'],differential_responsibility=d['difference']);return z

def order_plot(e,v,r,w,h):
 x=v['ordering_stats'];fig,axes=plt.subplots(2,1,constrained_layout=True);axes[0].plot(x[:,0],'.-',c='purple',label='Source responsibility L1 change');axes[0].set_ylim(0,2.05);axes[0].set_ylabel('L1 (0..2)');axes[0].legend(fontsize=8);ok=e['patch_valid']&(e['conditional_stats'][:,4]>=.8)&(x[:,4]>=.8)&np.isfinite(x[:,5:7]).all(1);ii=np.flatnonzero(ok);axes[1].plot(ii,x[ok,5],'.-',c='gray',label='Center order + conditional depth');axes[1].plot(ii,x[ok,6],'.-',c='teal',label='Conditional order + conditional depth');axes[1].set_xlabel('Frozen query pixel');axes[1].set_ylabel('Error vs frozen readout / p');axes[1].legend(fontsize=8);axes[0].set_title('ROI-only ordering counterfactual; not official rendering',fontsize=9);return plot_image(fig,w,h)

def verdict_plot(s,v,ca,w,h):
 fig,ax=plt.subplots();ax.axis('off');rows=[]
 for arm in ['line','shifted_12px','source_geometry_axis','shuffled_sides']:
  r=json.loads((ROOT/'round3/validation'/s/v/ca/arm/'RESULT.json').read_text());st=[z['state'] for z in r['frozen_patch_validation']];rows.append([arm,round(r['mean_responsibility_L1'],3),r['matched_error_pixels'],','.join(st) if st else 'NO FROZEN PATCH'])
 t=ax.table(cellText=rows,colLabels=['Arm','Mean L1','Depth pixels','Frozen-plane check'],loc='center',cellLoc='center',colWidths=[.25,.13,.15,.47]);t.auto_set_font_size(False);t.set_fontsize(7);t.scale(1,2.7);ax.set_title('Fixed R2 planes, no reserved-view refitting\nOccluded/unobserved is NOT a negative vote',fontsize=10);return plot_image(fig,w,h)

def run(s):
 a=activate(read_ply(registry()[s]['model']));line=activate(read_ply(linepath(s)/'gaussians.ply'))
 for v in RESERVED[s]:
  c=cam(s,v);raw=npz(rawpath(s,v));ink=render(line,c)['rgb'];w,h=c['width'],c['height']
  for ca in cases(s):
   if not ca['selection_valid']:continue
   d=ROOT/'round3/evidence'/s/v/ca['case']/'line';val=ROOT/'round3/validation'/s/v/ca['case']/'line';out=ROOT/'round3/figures'/s/v/ca['case'];out.mkdir(parents=True,exist_ok=True)
   if (out/'SEAL.json').exists():checkseal(out);continue
   e=npz(d/'EVIDENCE.npz');z=npz(val/'ORDERING_COUNTERFACTUAL.npz');r=json.loads((val/'RESULT.json').read_text());oldcolor=responsibility_render(a,c,s,e);newcolor=responsibility_render(a,c,s,reordered_evidence(e,z));panel(out/'CASE.jpg',[('Original source RGB + frozen queries',marked(raw['rgb'],e)),('Original C8 ink / X-RAY',marked(ink,e)),('Mean-order source responsibility',oldcolor),('ROI reordered responsibility DISPLAY',newcolor),('Actual alpha*T and depth change',order_plot(e,z,r,w,h)),('Frozen patches and same-budget nulls',verdict_plot(s,v,ca['case'],w,h))],f'{s} {v} {ca["case"]} | Round 3 reserved falsification',f'Fixed case. Parent {ca["parent_id"]}. Role coloring uses original source renderer; ROI reorder is a diagnostic, not new model.',3)
   xy=np.median(e['proposed_line_uv'],axis=0);x=int(np.clip(xy[0]-50,0,w-100));y=int(np.clip(xy[1]-50,0,h-100));items=[]
   for label,im in [('Original RGB',marked(raw['rgb'],e)),('Original ink X-RAY',marked(ink,e)),('Mean-order responsibility',oldcolor),('ROI conditional-order responsibility',newcolor)]:
    q=Image.fromarray((np.clip(im[y:y+100,x:x+100],0,1)*255).astype('uint8')).resize((500,500),Image.Resampling.NEAREST);items.append((label,np.asarray(q)/255))
   panel(out/'ZOOM.jpg',items,f'{s} {v} {ca["case"]} | local evidence','Explanatory crop only; full scene in CASE.jpg; source geometry / alpha unchanged.',2);js(out/'DISPLAY.json',dict(crop=[x,y,x+100,y+100],runtime_color_only=True,original_sort_fullframe=True,conditional_order_only_at_query_pixels=True));seal(out)
if __name__=='__main__':
 failures=[]
 for s in SCENES:
  try:state('ROUND3_PLOTS',round=3,scene=s,status='RUNNING',children=[os.getpid()]);run(s)
  except Exception as ex:
   import traceback;traceback.print_exc();js(ROOT/'round3'/f'PLOT_INVALID_{s}.json',dict(error=repr(ex)));failures.append(s)
 state('ROUND3_READY_FOR_REVIEW',round=3,status='INVALID' if failures else 'READY_FOR_REVIEW',children=[])
 if failures:raise SystemExit(1)
