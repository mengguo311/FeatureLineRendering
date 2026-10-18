from env import *
from geometry_roles import ROLES,PALETTE
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def plot_image(fig,w,h):
 fig.set_size_inches(w/100,h/100);fig.canvas.draw();a=np.asarray(fig.canvas.buffer_rgba())[...,:3].copy()/255;plt.close(fig);return a
def responsibility_render(a,c,s,e,role=None):
 co=colors(a,c).copy();ids=e['participant_ids'];left=e['left_mass'];right=e['right_mass'];total=left+right;ratio=np.divide(left,total,out=np.full(len(ids),.5),where=total>0);paint=np.c_[ratio,np.full(len(ids),.1),1-ratio] if role is None else np.tile(PALETTE[role],(len(ids),1));strength=.85*np.sqrt(total/max(total.max(initial=0),1e-15));co[ids]=co[ids]*(1-strength[:,None])+paint*strength[:,None]
 x={k:v for k,v in a.items() if k!='SH'};x['colors']=co;return render(x,c,[1]*3 if s=='ficus' else [0]*3,.3 if s=='ficus' else .0144)['rgb']
def marked(im,e):
 out=Image.fromarray((np.clip(im,0,1)*255).astype('uint8'));d=ImageDraw.Draw(out)
 for xy,side in zip(e['query_uv'],e['side_offset']):
  x,y=xy;col=(240,40,30) if side<0 else (30,80,240) if side>0 else (0,200,80);d.ellipse((x-1,y-1,x+1,y+1),fill=col)
 return np.asarray(out)/255
def profiles(e,r,w,h):
 fig,ax=plt.subplots(2,1,constrained_layout=True);z=e['native_z'].copy();p=r['info']['pixel_world_proxy'];finite=np.isfinite(z)&(z>.2);base=float(np.median(z[finite])) if finite.any() else 0
 for side,color in [(-1,'red'),(0,'green'),(1,'blue')]:
  k=np.sign(e['side_offset'])==side;ax[0].scatter(e['along_index'][k],(z[k]-base)/p,color=color,s=10,label=['Left native','Center native','Right native'][side+1]);ax[0].scatter(e['along_index'][k],(e['query_median_center_z'][k]-base)/p,color=color,s=15,marker='x')
 ax[0].set_ylabel('Depth offset / world-pixel proxy');ax[0].set_xlabel('Along fixed interval');ax[0].legend(fontsize=8);ax[0].set_title('Dots: frozen native/proxy depth; x: EWA center median')
 ids=e['participant_ids'];order=np.argsort(e['left_mass']+e['right_mass'])[-12:];xx=np.arange(len(order));ax[1].bar(xx-.18,e['left_mass'][order],width=.35,color='red',label='Left alpha*T');ax[1].bar(xx+.18,e['right_mass'][order],width=.35,color='blue',label='Right alpha*T');ax[1].set_xticks(xx,[str(i) for i in ids[order]],rotation=60,fontsize=7);ax[1].legend(fontsize=8);ax[1].set_title('Top 12 shown; ALL source contributors stored / source IDs');return plot_image(fig,w,h)
def patch_plot(e,r,a,w,h):
 fig=plt.figure();ax=fig.add_subplot(111,projection='3d');ids=e['participant_ids'];weight=e['left_mass']+e['right_mass'];order=np.argsort(weight)[-600:];q=a['means'][ids[order]];ax.scatter(*q.T,c='gray',s=4,alpha=.25,label='Source centers (not surface)')
 for side,color in [('left','red'),('right','blue')]:
  P=e[side+'_points'];p=r[side+'_patch']
  if len(P):ax.scatter(*P.T,c=color,s=10,label=side+' depth samples')
  if p.get('valid'):
   c=np.asarray(p['center']);n=np.asarray(p['normal'])*r['info']['pixel_world_proxy']*8;ax.plot(*np.stack([c,c+n]).T,c=color,lw=2)
 ax.plot(*e['world_line'].T,c='black',lw=2,label='Fixed original ink interval');ax.set_xlabel('World X');ax.set_ylabel('World Y');ax.set_zlabel('World Z');ax.legend(fontsize=7);ax.set_title('Data-derived 3D diagnostic; fitted normals are proxies\nSource centers shown top 600 by responsibility, NOT query truncation',fontsize=9);fig.tight_layout();return plot_image(fig,w,h)
def run(s,views):
 source=activate(read_ply(registry()[s]['model']));line=activate(read_ply(linepath(s)/'gaussians.ply'));cases=[x for x in json.loads((ROOT/'CASE_FREEZE.json').read_text())['cases'] if x['scene']==s]
 for v in views:
  c=cam(s,v);raw=npz(rawpath(s,v));ink=render(line,c)['rgb'];ref=ROOT/'scenes'/s/'stage1'/v
  for case in cases:
   d=ref/case['case']
   if not (d/'line/RESULT.json').exists():continue
   r=json.loads((d/'line/RESULT.json').read_text());e=npz(d/'line/EVIDENCE.npz');w,h=c['width'],c['height'];actual=responsibility_render(source,c,s,e);role=responsibility_render(source,c,s,e,r['role']['role_index']);prof=profiles(e,r,w,h);patch=patch_plot(e,r,source,w,h)
   out=d/'figures';out.mkdir(exist_ok=True);panel(out/'CASE.jpg',[('Original RGB + actual query pixels',marked(raw['rgb'],e)),('Original C8 ink / X-RAY + query pixels',marked(ink,e)),('Actual source-ID responsibility: L red / R blue',actual),('Source role display ONLY / '+r['role']['role'],role),('Measured depth and source responsibility',prof),('Local depth samples + source allocation',patch)],f'{s} {v} {case["case"]} | original parent {case["parent_id"]}',f'L1={r["info"]["L1"]:.3f}, center qualified={r["info"]["center_supported_fraction"]:.2f}. Labels are proxies, not physical geometry / GT.',3)
   items=[];record={}
   for arm in ['line','shifted_12px','source_geometry_axis']:
    rr=json.loads((d/arm/'RESULT.json').read_text());ee=npz(d/arm/'EVIDENCE.npz');im=responsibility_render(source,c,s,ee);items.append((arm+' | '+rr['role']['role'],marked(im,ee)));record[arm]=rr['role']
   panel(out/'CONTROLS.jpg',items,f'{s} {v} {case["case"]} | SAME query budget, frozen controls','No-line control: region-centered source covariance axis; not a global geometry method. Blue/red are source contribution display only.',3)
   # Full-frame always retained; a secondary fixed 100px crop makes tiny source-ID marks readable.
   xy=np.median(e['proposed_line_uv'],axis=0);x=int(np.clip(xy[0]-50,0,w-100));y=int(np.clip(xy[1]-50,0,h-100));ims=[marked(raw['rgb'],e),marked(ink,e),actual,role];zooms=[np.asarray(Image.fromarray((np.clip(im[y:y+100,x:x+100],0,1)*255).astype('uint8')).resize((500,500),Image.Resampling.NEAREST))/255 for im in ims];panel(out/'ZOOM.jpg',list(zip(['RGB / exact query','Original C8 / X-RAY','Source responsibility','Role proxy display'],zooms)),f'{s} {v} {case["case"]} | explanatory crop','Nearest-pixel enlargement, no algorithm changes. Full frame in CASE.jpg.',2)
   js(out/'DISPLAY.json',dict(crop=[x,y,x+100,y+100],coloring='runtime diagnostic source-color marking only; original SH/alpha/covariance not written or changed',roles=record));seal(out)
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--secondary',action='store_true');a=p.parse_args();failed=[]
 for s in SCENES:
  try:state('PLOTS',scene=s,status='RUNNING',children=[os.getpid()]);run(s,VIEWS[s][1:] if a.secondary else [DEV[s]]);state('PLOTS_READY',status='READY_FOR_REVIEW',children=[])
  except Exception as e:js(ROOT/f'PLOTS_FAILURE_{s}.json',dict(error=repr(e)));failed.append(s)
 if failed:state('PLOTS_FAILED',status='ENGINEERING_NOT_READY',children=[],failed=failed);raise SystemExit(1)
