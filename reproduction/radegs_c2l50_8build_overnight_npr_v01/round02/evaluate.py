from env import *
from experiment import view_result,ARMS
from geometry import correspond
def getlab(v,arm):
 if arm=='r01_profile':return npz(R1/'B/ficus'/v/'profile.npz')['labels']
 if arm=='v02_rgb':return npz(V2/'stageB/ficus'/v/'shared_rgb_only_k3.npz')['labels']
 return view_result(v,arm)['labels']
def match(v,tv,arm):
 lab=getlab(v,arm);target=getlab(tv,arm);_,z,a=raw('ficus',v);_,tz,ta=raw('ficus',tv);c=cam('ficus',v);tc=cam('ficus',tv);mask=npz(R1/'A/ficus'/v/'SUBJECT.npz')['candidate'];yy,xx=np.mgrid[:z.shape[0]:4,:z.shape[1]:4];rows=[];arrays=[];pred={}
 for k in [1,2,3]:
  if (lab==k).sum()<.01*mask.sum():continue
  good=(lab[yy,xx]==k)&np.isfinite(z[yy,xx])&(z[yy,xx]>.2)&(a[yy,xx]>=.5);uv=np.c_[xx[good],yy[good]];X=unproject(uv,z[uv[:,1],uv[:,0]],c);state,q=correspond(X,uv,c,tc,tz,ta);ids=np.flatnonzero(state==1);tl=target[q[ids,1],q[ids,0]];known=tl>0;ct=np.bincount(tl[known],minlength=4);best=int(ct.argmax());fraction=float(ct[best]/max(known.sum(),1));eligible=bool(len(ids)/max(len(state),1)>=.2 and known.sum()>=30 and (~known).sum()/max(len(ids),1)<=.35)
  if eligible:pred[k]=(best,fraction)
  rows.append(dict(region=k,matched_to=best,known=int(known.sum()),target_unknown=int((~known).sum()),state_counts=np.bincount(state,minlength=6).tolist(),dominant=fraction,eligible=eligible));targ=np.full(len(state),-1,np.int16);targ[ids]=tl;arrays.append(dict(region=np.full(len(state),k,np.uint8),uv=uv,target_uv=q,state=state,target_label=targ))
 return pred,rows,({k:np.concatenate([x[k] for x in arrays]) for k in arrays[0]} if arrays else {})
def main():
 status('EVALUATION',children=[os.getpid()]);records=[]
 for arm in [*ARMS,'r01_profile','v02_rgb']:
  for tv in [AUX['ficus'],*RES['ficus']]:
   p=R/'evaluation'/(arm+'_'+tv)
   if (p/'SEAL.json').exists():checkseal(p);records.append(json.loads((p/'COUNTS.json').read_text()));continue
   p.mkdir(parents=True);ab,aa,adata=match(DEV['ficus'],tv,arm);ba,bb,bdata=match(tv,DEV['ficus'],arm);pairs=[(i,j) for i,(j,f) in ab.items() if f>=.75 and j in ba and ba[j][0]==i and ba[j][1]>=.75];row=dict(arm=arm,target=tv,mutual=pairs,forward=aa,reverse=bb,common_strict_visibility='2worldpixel depth,1.5px cycle,3worldpixel distance',not_semantic_GT=True);js(p/'COUNTS.json',row);np.savez_compressed(p/'FORWARD.npz',**adata);np.savez_compressed(p/'REVERSE.npz',**bdata);seal(p);records.append(row);print(arm,tv,pairs,flush=True)
 js(R/'MATCH_COUNTS.json',records);status('EVALUATION_DONE',children=[])
if __name__=='__main__':main()
