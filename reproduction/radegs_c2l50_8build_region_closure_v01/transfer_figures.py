from env import *
from graph import lookup,visible_state
from run import annotate

def main():
 out=ROOT/'crossview_figures';out.mkdir(exist_ok=True);rows=json.loads((ROOT/'evaluation/TRANSFERS.json').read_text())
 for s in SCENES:
  chosen=[]
  for arm in ['original','no_line']:
   pool=[r for r in rows if r['scene']==s and r['arm']==arm and r['target_view']==RESERVED[s][0]]
   if pool:chosen.append(pool[0]) # first frozen case/region, NEVER best IoU
  for r in chosen:
   s0=npz(rawpath(s,r['source_view']));s1=npz(rawpath(s,r['target_view']));c0=cam(s,r['source_view']);c1=cam(s,r['target_view']);p=ROOT/'dev'/s/r['source_view']/r['case']/r['arm'];q=ROOT/'reserved'/s/r['target_view']/r['case']/r['arm'];m=npz(p/'REGION_MASKS.npz')['masks'][r['dev_region']];yy,xx=np.nonzero(m);z=s0['median_camera_z'].squeeze()[yy,xx];aa=s0['alpha'].squeeze()[yy,xx];valid=np.isfinite(z)&(z>.2)&(aa>=.5);uv,zz=projection(unproject(np.c_[xx,yy][valid],z[valid],c0),c1);sd,al,_,inside=lookup(s1,uv);ok=inside&(visible_state(zz,sd,al,np.sqrt(c1['fx']*c1['fy']))=='visible');dest=np.zeros_like(s1['alpha'].squeeze(),bool);xy=np.rint(uv[ok]).astype(int);dest[xy[:,1],xy[:,0]]=True
   a=s0['rgb'].copy();a[m]=.5*a[m]+.5*np.array([1,.7,0]);b=s1['rgb'].copy();b[dest]=.5*b[dest]+.5*np.array([0,.7,1]);d=s1['rgb'].copy();best=r['target_original_region']
   if best>=0:
    bm=npz(q/'REGION_MASKS.npz')['masks'][best];d[bm]=.5*d[bm]+.5*np.array([1,0,.7])
   panel(out/f'{s}_{r["arm"]}.jpg',[('DEV region (orange); hypothesis only',a),('Reserved frozen source RGB',s1['rgb']),('Raw-depth projected pixels (cyan); NOT a new render',b),('Best independent target proposal (magenta)',d)],f'{s} {r["case"]} | {r["arm"]}',f'{r["source_view"]} -> {r["target_view"]} | comparable={r["comparable_fraction"]:.3f} IoU={r["iou"]:.3f} pass={r["passed"]}',cols=2)
   ims=[a,s1['rgb'],b,d];labels=['DEV hypothesis (orange)','Reserved raw source','Visible transferred pixels (cyan)','Target independent proposal (magenta)'];zooms=[]
   cp0=json.loads((p/'PROVENANCE.json').read_text())['center_uv'];cp1=json.loads((q/'PROVENANCE.json').read_text())['center_uv']
   for index,arr in enumerate(ims):
    x,y=np.rint(cp0 if index==0 else cp1).astype(int);H,W=arr.shape[:2];box=(max(0,x-48),max(0,y-48),min(W,x+49),min(H,y+49))
    if box[2]<=box[0] or box[3]<=box[1]:break
    im=Image.fromarray(np.uint8(np.clip(arr,0,1)*255)).crop(box).resize((388,388),Image.Resampling.NEAREST);zooms.append((labels[index],np.asarray(im)/255))
   if len(zooms)==4:panel(out/f'{s}_{r["arm"]}_DETAIL.jpg',zooms,f'{s} {r["case"]} | {r["arm"]}',f'Fixed case ROI / IoU={r["iou"]:.3f} / no target = UNKNOWN',cols=2)
if __name__=='__main__':main()
