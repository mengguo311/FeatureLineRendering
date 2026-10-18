from env import *
from section import *
import signal
def timeout(*a):raise TimeoutError('unit900s')
signal.signal(signal.SIGALRM,timeout)
def collect():
 rows=[]
 for vi,v in enumerate([DEV['ficus'],AUX['ficus']]):
  _,z,a=raw('ficus',v);c=cam('ficus',v);m=npz(R/'A/ficus'/v/'SUBJECT.npz')['candidate'];yy,xx=np.mgrid[:z.shape[0]:4,:z.shape[1]:4];good=m[yy,xx]&np.isfinite(z[yy,xx])&(z[yy,xx]>.2)&(a[yy,xx]>=.5);uv=np.c_[xx[good],yy[good]];d=z[uv[:,1],uv[:,0]];rows.append(dict(world=unproject(uv,d,c),uv=uv,view_id=np.full(len(uv),vi,np.int16),pixel_scale=d/np.sqrt(c['fx']*c['fy'])))
 n=min(len(r['world']) for r in rows)
 for r in rows:
  ids=np.linspace(0,len(r['world'])-1,n,dtype=int)
  for k in r:r[k]=r[k][ids]
 return {k:np.concatenate([r[k] for r in rows]) for k in rows[0]}
def predict(v,m):
 _,z,a=raw('ficus',v);c=cam('ficus',v);subject=npz(R/'A/ficus'/v/'SUBJECT.npz');mask=subject['candidate'];y,x=np.nonzero(mask);uv=np.c_[x,y];X=unproject(uv,z[y,x],c);h=X@np.asarray(m['up']);labs={}
 for arm,cuts,valid in [('profile',m.get('cuts'),m['qualified']),('equal_thirds',[m['bins']/3,2*m['bins']/3],True)]:
  lab=np.zeros(z.shape,np.int16)
  if valid:lab[y,x]=profile_labels(h,m['height_lo'],m['height_hi'],cuts,m['bins'])
  labs[arm]=dict(labels=lab,unknown=(mask&(lab==0))|subject['unknown'],source_uv=uv,world_height=h)
 return labs
def fit():
 p=R/'B/ficus/model';p.mkdir(parents=True,exist_ok=True)
 if (p/'SEAL.json').exists():checkseal(p);return
 data=collect();up=json.loads((R/'A/ficus/model/MODEL.json').read_text())['axis'];assert up['qualified'];m,ar=fit_sections(data['world'],data['view_id'],up['up']);np.savez_compressed(p/'OBSERVATIONS.npz',**data);np.savez_compressed(p/'PROFILE.npz',**ar);js(p/'MODEL.json',m)
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(9,5));he=np.linspace(m['height_lo'],m['height_hi'],m['bins'],endpoint=False);he+=(m['height_hi']-m['height_lo'])/(2*m['bins'])
 for i,w in enumerate(ar['width_by_view']):ax.plot(he,w,label=['DEV','AUX'][i])
 ax.plot(he,ar['width_common'],'k-',lw=2,label='Common observed profile')
 if m['cuts']:
  for cut in m['cuts']:ax.axvline(m['height_lo']+cut/m['bins']*(m['height_hi']-m['height_lo']),ls='--',c='red')
 ax.set(xlabel='Shared upright coordinate (original world units)',ylabel='Visible cross-section span (not volume)',title='r01 Ficus | Frozen axial bottleneck test | qualified='+str(m['qualified']));ax.legend();fig.tight_layout();fig.savefig(p/'PROFILE.png',dpi=150);plt.close(fig);seal(p);print('PROFILE_MODEL',json.dumps(m),flush=True)
def runviews(vs):
 m=json.loads((R/'B/ficus/model/MODEL.json').read_text())
 for v in vs:
  guard();p=R/'B/ficus'/v
  if (p/'SEAL.json').exists():checkseal(p);continue
  p.mkdir(parents=True);signal.alarm(900);data=predict(v,m);rgb,z,a=raw('ficus',v);ref=npz(V1/'stageA/ficus'/v/'REFERENCE.npz');old=npz(V2/'stageB/ficus'/v/'shared_xyz_lab_width_k3.npz');oldrgb=npz(V2/'stageB/ficus'/v/'shared_rgb_only_k3.npz');items=[('Original source RGB',rgb),('Original C8 ink | XRAY',ref['line_rgb']),('TRUE joint | frozen CPU reference',ref['joint_rgb']),('v02 shared XYZ/Lab/width K3',colors(rgb,old['labels'],old['unknown'])),('r01 axial profile | candidates, not semantic GT',colors(rgb,data['profile']['labels'],data['profile']['unknown'])),('Equal-height thirds | same 3-region budget',colors(rgb,data['equal_thirds']['labels'],data['equal_thirds']['unknown']))]
  panel(p/'FULL.jpg',items,'Ficus / '+v+' | r01 real structural-hypothesis test','Blue lower broad / orange narrow middle / green upper spread; grey UNKNOWN. No RGB fit or line input in r01.',3)
  panel(p/'CONTROLS.jpg',[('Original source RGB',rgb),('v02 RGB-only K3 | same old sample budget',colors(rgb,oldrgb['labels'],oldrgb['unknown'])),('r01 profile hypotheses',colors(rgb,data['profile']['labels'],data['profile']['unknown'])),('Equal thirds null',colors(rgb,data['equal_thirds']['labels'],data['equal_thirds']['unknown']))],'Ficus / '+v+' | Strong and same-budget controls','No semantic identity follows from shared color. Native complete frame, unchanged source and C8.',2)
  rows=[]
  for arm,ar in data.items():np.savez_compressed(p/(arm+'.npz'),**ar);rows.append(dict(arm=arm,view=v,counts=np.bincount(ar['labels'].ravel(),minlength=4).tolist(),unknown_subject=int((npz(R/'A/ficus'/v/'SUBJECT.npz')['candidate']&(ar['labels']==0)).sum())))
  js(p/'COUNTS.json',rows);seal(p);signal.alarm(0);print('B_VIEW',v,rows,flush=True)
def main():
 import argparse;p=argparse.ArgumentParser();p.add_argument('--phase',choices=['fit','reserved'],required=True);a=p.parse_args();g=json.loads((R/'A_GATE.json').read_text());assert g['ficus']=='GO_PROXY';status('B_'+a.phase,children=[os.getpid()])
 if a.phase=='fit':fit();runviews([DEV['ficus'],AUX['ficus']])
 else:runviews(RES['ficus'])
 status('B_'+a.phase+'_DONE',children=[])
if __name__=='__main__':main()
