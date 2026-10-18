from env import *
from plots import responsibility_render,marked,plot_image,plt

def patch_paint(a,c,s,roles):
 co=colors(a,c).copy();ids=roles['source_index'];mass=roles['total_visible_mass'];soft=roles['soft_patch'];u=roles['unknown'];paint=np.tile([.55,.35,.65],(len(ids),1))*u[:,None]
 for j in range(soft.shape[1]):paint+=soft[:,j,None]*np.array([.95,.2,.1] if j==0 else [.1,.3,.95])
 strength=.85*np.sqrt(mass/max(mass.max(initial=0),1e-20));co[ids]=co[ids]*(1-strength[:,None])+paint*strength[:,None];b={k:v for k,v in a.items() if k!='SH'};b['colors']=co;return render(b,c,[1]*3 if s=='ficus' else [0]*3,.3 if s=='ficus' else .0144)['rgb']

def local_graph_plot(g,r,e,w,h):
 fig=plt.figure();ax=fig.add_subplot(111,projection='3d');X=g['X'];side=g['side'];p=r['pixel_world_proxy'];origin=np.mean(e['world_line'],axis=0);ii=np.linspace(0,len(X)-1,min(1800,len(X))).astype(int) if len(X) else []
 if len(ii):q=(X[ii]-origin)/p;ax.scatter(*q.T,c=np.where(side[ii]<0,'red','blue'),s=4,alpha=.2,label='Conditional source/pixel hypotheses')
 q=(e['world_line']-origin)/p;ax.plot(*q.T,c='black',lw=2,label='Original C8 interval')
 for j,patch in enumerate(r['patches']):
  ctr=(np.asarray(patch['center'])-origin)/p;n=np.asarray(patch['normal']);ax.plot(*np.stack([ctr,ctr+5*n]).T,c='green',lw=2,label='Fitted normal PROXY' if j==0 else None)
 ax.set_xlabel('World dX / p');ax.set_ylabel('World dY / p');ax.set_zlabel('World dZ / p');ax.set_title('Local ray hypotheses, NOT source-center surface\n'+r['model']+'; <=1800 plotted, full graph retained',fontsize=9);ax.legend(fontsize=7);fig.tight_layout();return plot_image(fig,w,h)

def counter_table(s,v,ca,w,h):
 fig,ax=plt.subplots();ax.axis('off');rows=[]
 for arm in ['line','shifted_12px','source_geometry_axis','shuffled_sides']:
  r=json.loads((ROOT/'round2/models'/s/v/ca/arm/'RESULT.json').read_text());rows.append([arm,r['model'],str(r['counts']['qualified_pixels']),str(r['counts']['qualified_source_ids']),str(round(r.get('single',{}).get('rms_p',999),2)),str(round(r.get('source_overlap',0) or 0,3))])
 t=ax.table(cellText=rows,colLabels=['Arm','Proxy','Pixels','Src IDs','1-sheet RMS/p','ID overlap'],loc='center',cellLoc='center');t.auto_set_font_size(False);t.set_fontsize(8);t.scale(1,2);ax.set_title('Same-budget local model comparison\nNo physically certified plane from a small residual',fontsize=10);return plot_image(fig,w,h)

def run(s):
 v=DEV[s];c=cam(s,v);raw=npz(rawpath(s,v));a=activate(read_ply(registry()[s]['model']));ink=render(activate(read_ply(linepath(s)/'gaussians.ply')),c)['rgb']
 for ca in cases(s):
  if not ca['selection_valid']:continue
  inp=ROOT/'round1/scenes'/s/v/ca['case']/'line';d=ROOT/'round2/models'/s/v/ca['case']/'line';out=ROOT/'round2/figures'/s/ca['case'];out.mkdir(parents=True,exist_ok=True)
  if (out/'SEAL.json').exists():checkseal(out);continue
  e=npz(inp/'EVIDENCE.npz');r=json.loads((d/'RESULT.json').read_text());g=npz(d/'CONDITIONAL_GRAPH.npz');roles=npz(d/'SOURCE_ROLES.npz');rr=responsibility_render(a,c,s,e);paint=patch_paint(a,c,s,roles);w,h=c['width'],c['height']
  panel(out/'CASE.jpg',[('Original source RGB + fixed query',marked(raw['rgb'],e)),('Original C8 line / X-RAY',marked(ink,e)),('Source-only responsibility / red-blue',rr),('Local SOURCE roles / UNKNOWN purple',paint),('Conditional hypotheses + fitted proxy',local_graph_plot(g,r,e,w,h)),('Local selection and nulls',counter_table(s,v,ca['case'],w,h))],f'{s} {v} {ca["case"]} | Round 2 finite responsibility graph',f'Parent {ca["parent_id"]} | {r["model"]} | Source geometry / alpha / SH unchanged; diagnostic color only.',3)
  xy=np.median(e['proposed_line_uv'],axis=0);x=int(np.clip(xy[0]-50,0,w-100));y=int(np.clip(xy[1]-50,0,h-100));items=[]
  for name,im in [('Original RGB',marked(raw['rgb'],e)),('Original ink X-RAY',marked(ink,e)),('Source responsibility',rr),('Proxy or UNKNOWN display',paint)]:
   q=Image.fromarray((np.clip(im[y:y+100,x:x+100],0,1)*255).astype('uint8')).resize((500,500),Image.Resampling.NEAREST);items.append((name,np.asarray(q)/255))
  panel(out/'ZOOM.jpg',items,f'{s} {ca["case"]} | fixed 100px explanatory crop','Full frame in CASE.jpg. No crop used for candidate selection or fitting.',2);js(out/'DISPLAY.json',dict(crop=[x,y,x+100,y+100],mode='runtime source-ID color diagnostic; original geometry/SH files untouched'));seal(out)
if __name__=='__main__':
 failed=[]
 for s in SCENES:
  try:state('ROUND2_PLOTS',round=2,scene=s,status='RUNNING',children=[os.getpid()]);run(s)
  except Exception as ex:
   import traceback;traceback.print_exc();js(ROOT/'round2'/f'PLOT_INVALID_{s}.json',dict(error=repr(ex)));failed.append(s)
 state('ROUND2_READY_FOR_REVIEW',round=2,status='INVALID' if failed else 'READY_FOR_REVIEW',children=[])
 if failed:raise SystemExit(1)
