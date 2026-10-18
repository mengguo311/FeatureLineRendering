from env import *
G=json.loads((R/'CONFIG.json').read_text())['gate']
def visible_state(uv,z,depth,alpha,c):
 fin=np.isfinite(uv).all(1)&np.isfinite(z)&(z>.2);q=np.rint(np.nan_to_num(uv)).astype(np.int64);inside=fin&(q[:,0]>=0)&(q[:,0]<c['width'])&(q[:,1]>=0)&(q[:,1]<c['height']);s=np.zeros(len(z),np.uint8);s[~inside]=3;ids=np.flatnonzero(inside);d=depth[q[ids,1],q[ids,0]];a=alpha[q[ids,1],q[ids,0]];good=np.isfinite(d)&(d>.2)&(a>=.5);tol=np.maximum(.01*d,6*d/np.sqrt(c['fx']*c['fy']));delta=z[ids]-d;s[ids[good&(abs(delta)<=tol)]]=1;s[ids[good&(delta>tol)]]=2;s[ids[good&(delta< -tol)]]=4;return s
def mutual(ab,ba):return [(i,j) for i,(j,p) in sorted(ab.items()) if p>=.75 and j in ba and ba[j][0]==i and ba[j][1]>=.75]
def downstream(count,visual):return 'GO_PROXY' if count>=2 and visual else 'NO_GO'
def match(v,tv,arm):
 s='ficus';lab=npz(R/'B'/s/v/(arm+'.npz'))['labels'];tlab=npz(R/'B'/s/tv/(arm+'.npz'))['labels'];_,z,a=raw(s,v);_,tz,ta=raw(s,tv);c=cam(s,v);tc=cam(s,tv);yy,xx=np.mgrid[:z.shape[0]:4,:z.shape[1]:4];rows=[];ar=[];pred={};mask=npz(R/'A'/s/v/'SUBJECT.npz')['candidate'];minarea=.01*mask.sum()
 for gid in [1,2,3]:
  n=int((lab==gid).sum())
  if n<minarea:continue
  valid=(lab[yy,xx]==gid)&np.isfinite(z[yy,xx])&(z[yy,xx]>.2)&(a[yy,xx]>=.5);uv=np.c_[xx[valid],yy[valid]];X=unproject(uv,z[uv[:,1],uv[:,0]],c);q,d=project(X,tc);state=visible_state(q,d,tz,ta,tc);ix=np.flatnonzero(state==1);qi=np.rint(q[ix]).astype(int);t=tlab[qi[:,1],qi[:,0]];known=t>0;ct=np.bincount(t[known],minlength=4);target=int(ct.argmax()) if known.any() else 0;fraction=float(ct[target]/max(known.sum(),1));unk=float((~known).sum()/max(len(ix),1));eligible=bool(len(ix)/max(len(state),1)>=.2 and known.sum()>=30 and unk<=.35)
  if eligible:pred[gid]=(target,fraction)
  rows.append(dict(region=gid,target=target,samples=len(state),visible=len(ix),target_unknown=int((~known).sum()),known=int(known.sum()),dominant=fraction,eligible=eligible,occluded=int((state==2).sum()),front=int((state==4).sum()),unknown_depth=int((state==0).sum()),outside=int((state==3).sum())))
  row=dict(region=np.full(len(state),gid,np.int16),source_uv=uv,target_uv=q,target_z=d,state=state,target_label=np.full(len(state),-1,np.int16));row['target_label'][ix]=t;ar.append(row)
 return pred,rows,{k:np.concatenate([x[k] for x in ar]) for k in ar[0]} if ar else {}
def main():
 rows=[]
 for arm in ['profile','equal_thirds']:
  for tv in [AUX['ficus'],*RES['ficus']]:
   p=R/'B/ficus/matches'/(arm+'_'+tv)
   if (p/'SEAL.json').exists():checkseal(p);rows.append(json.loads((p/'COUNTS.json').read_text()));continue
   p.mkdir(parents=True);ab,ra,aa=match(DEV['ficus'],tv,arm);ba,rb,bb=match(tv,DEV['ficus'],arm);row=dict(arm=arm,target=tv,mutual=mutual(ab,ba),forward=ra,reverse=rb,not_semantic_GT=True);np.savez_compressed(p/'FORWARD.npz',**aa);np.savez_compressed(p/'REVERSE.npz',**bb);js(p/'COUNTS.json',row);seal(p);rows.append(row);print(arm,tv,row['mutual'],flush=True)
 js(R/'MATCH_COUNTS.json',rows)
if __name__=='__main__':main()
