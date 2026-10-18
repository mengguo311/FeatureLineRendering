from env import *
from protocol import transfer
from run_stage_a import overlay,grey

def run():
 rows=[]
 for s in SCENES:
  for v,tv in [(DEV[s],AUX[s]),(AUX[s],DEV[s]),(DEV[s],RESERVED[s][0]),(DEV[s],RESERVED[s][1])]:
   p=ROOT/'stageA'/s/v;q=ROOT/'stageA'/s/tv;checkseal(p);checkseal(q);a=npz(p/'SUBJECT.npz');b=npz(q/'SUBJECT.npz');ra=npz(rawpath(s,v));rb=npz(rawpath(s,tv));out=ROOT/'transfer'/s/(v+'__'+tv);out.mkdir(parents=True,exist_ok=True)
   controls=['candidate','rgb_alpha_control','depth_control','alpha_control'];imgs=[]
   for arm in controls:
    r,ar=transfer(a[arm],ra['median_camera_z'].squeeze(),ra['alpha'].squeeze(),cam(s,v),b[arm],rb['median_camera_z'].squeeze(),rb['alpha'].squeeze(),cam(s,tv));r.update(scene=s,from_view=v,to_view=tv,arm=arm);js(out/(arm+'.json'),r);np.savez_compressed(out/(arm+'.npz'),**ar);rows.append(r)
    im=rb['rgb'].copy();uv=np.rint(ar['target_uv']).astype(int);good=(uv[:,0]>=0)&(uv[:,0]<im.shape[1])&(uv[:,1]>=0)&(uv[:,1]<im.shape[0]);colors_by_state={0:[1,.6,0],1:[0,.9,.3],2:[.1,.4,1],4:[1,0,1]}
    for state,col in colors_by_state.items():
     idx=np.flatnonzero(good&(ar['state']==state));xy=uv[idx];im[xy[:,1],xy[:,0]]=col
    idx=np.flatnonzero(good&(ar['state']==1)&~ar['inside_candidate']);xy=uv[idx];im[xy[:,1],xy[:,0]]=[1,0,0]
    imgs.append((arm+' | projected source samples',im))
   panel(out/'TRANSFER.jpg',[('Source view subject proxy',overlay(ra['rgb'],a['candidate'])),('Target independent subject proxy',overlay(rb['rgb'],b['candidate'])),*imgs],s+' | '+v+' -> '+tv+' | Frozen transfer diagnostic','Green: comparable inside; red: comparable outside; blue: occluded; magenta: front inconsistent; orange: unknown',2);seal(out)
 js(ROOT/'TRANSFER_COUNTS.json',dict(rows=rows,not_independent_line_matches=True));print('TRANSFER_COMPLETE',len(rows))
if __name__=='__main__':run()
