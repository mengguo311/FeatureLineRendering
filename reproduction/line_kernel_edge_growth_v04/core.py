"""Finite support carriers; original Gaussian arrays are never modified."""
from common import np, guard
from scipy.spatial import cKDTree
from scipy.linalg import solve_banded
from dataclasses import dataclass
from collections import Counter, defaultdict
RAD=np.pi/180
EPS=1e-8
def clean(q):
    q=np.asarray(q,float)
    return q[np.r_[True,np.linalg.norm(np.diff(q,axis=0),axis=1)>EPS]]
def arc(q):return np.r_[0.,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))]
def sample(q,spacing=1.):
    ss=arc(q);tt=np.linspace(0,ss[-1],max(2,int(np.ceil(ss[-1]/spacing))+1))
    return np.stack([np.interp(tt,ss,q[:,k]) for k in range(3)],1)
def refine(q):
    out=[q[0]]
    for a,b in zip(q[:-1],q[1:]):
        n=max(1,int(np.ceil(np.linalg.norm(b-a)/4)))
        out.extend(a+(b-a)*u for u in np.arange(1,n+1)/n)
    return np.asarray(out)
def project(x,q):
    """Exact nearest finite segment, deterministic lowest segment on ties."""
    v=np.diff(q,axis=0);ll=np.einsum('ij,ij->i',v,v);ss=arc(q);out=[]
    for lo in range(0,len(x),1024):
        dx=x[lo:lo+1024,None,:]-q[None,:-1,:]
        u=np.clip(np.einsum('nkj,kj->nk',dx,v)/np.maximum(ll,1e-30),0,1)
        residual=dx-u[:,:,None]*v
        ds=np.einsum('nkj,nkj->nk',residual,residual);j=ds.argmin(1);ii=np.arange(len(j));uu=u[ii,j]
        tangent=v[j]/np.sqrt(np.maximum(ll[j,None],1e-30))
        out.append((ss[j]+uu*np.sqrt(ll[j]),np.sqrt(ds[ii,j]),tangent,j,q[j]+uu[:,None]*v[j]))
    return tuple(np.concatenate([z[k] for z in out]) for k in range(5))
def extended_s(x,q):
    s,d,t,j,near=project(x,q);ss=arc(q)
    z=(j==0)&(s<EPS);s[z]+=np.minimum(0,np.sum((x[z]-q[0])*t[z],1))
    z=(j==len(q)-2)&(s>ss[-1]-EPS);s[z]+=np.maximum(0,np.sum((x[z]-q[-1])*t[z],1))
    return s,d,t
def union_intervals(intervals):
    z=sorted((float(min(a,b)),float(max(a,b))) for a,b in intervals);out=[]
    for a,b in z:
        if out and a<=out[-1][1]+EPS:out[-1][1]=max(out[-1][1],b)
        else:out.append([a,b])
    ar=np.asarray(out,float).reshape(-1,2);length=float(np.diff(ar,axis=1).sum()) if len(ar) else 0.
    gaps=ar[1:,0]-ar[:-1,1] if len(ar)>1 else np.empty(0)
    return ar,length,float(np.diff(ar,axis=1).max(initial=0)),float(gaps.max(initial=0)),float(gaps.sum())
def segment_contact(q):
    n=len(q)-1
    if n<3:return False
    ii,jj=np.triu_indices(n,2);a=q[ii];b=q[jj];u=q[ii+1]-a;v=q[jj+1]-b;w=a-b
    aa=np.sum(u*u,1);bb=np.sum(u*v,1);cc=np.sum(v*v,1);dd=np.sum(u*w,1);ee=np.sum(v*w,1);den=aa*cc-bb*bb
    s=(bb*ee-cc*dd)/np.maximum(den,1e-30);t=(aa*ee-bb*dd)/np.maximum(den,1e-30)
    interior=(den>1e-20)&(s>=0)&(s<=1)&(t>=0)&(t<=1)
    dist=np.where(interior,np.linalg.norm(w+s[:,None]*u-t[:,None]*v,axis=1),np.inf)
    for f in (0.,1.):
        tt=np.clip((ee+f*bb)/np.maximum(cc,1e-30),0,1);dist=np.minimum(dist,np.linalg.norm(w+f*u-tt[:,None]*v,axis=1))
        st=np.clip((f*bb-dd)/np.maximum(aa,1e-30),0,1);dist=np.minimum(dist,np.linalg.norm(w+st[:,None]*u-f*v,axis=1))
    return bool(np.any(dist<.5-EPS))
@dataclass
class Carrier:
    cid:int
    reps:np.ndarray
    rows:np.ndarray
    q:np.ndarray
    kind:str
    valid:bool
    baseline:bool
    origins:tuple
    version:int=0

class Engine:
    def __init__(self,a,r,t,p):
        self.a=a;self.r=r;self.p=p;self.x=a['means'].astype(float)/p;self.t=t;self.rx=r['x']/p;self.rt=r['t'];self.ep=r['endpoints']/p
        self.carriers={};self.events=[];self.records=[];self.aux=defaultdict(list);self.stats=Counter();self.fit_count=0;self.level=0;self.next_version=1
    def rows_for(self,reps):return np.concatenate([self.r['member_rows'][self.r['member_offsets'][i]:self.r['member_offsets'][i+1]] for i in reps]).astype(np.int64)
    def support(self,reps,q):
        s=project(self.ep[reps].reshape(-1,3),q)[0].reshape(-1,2)
        return union_intervals(s)
    def branch(self,reps,q):
        if len(reps)<9:return False
        xx=self.rx[reps];tt=self.rt[reps]
        for center in q:
            dx=xx-center;rr=np.linalg.norm(dx,axis=1);sel=np.flatnonzero((rr>EPS)&(rr<=4.))
            if len(sel)<9:continue
            dirs=tt[sel]*np.where(np.sum(tt[sel]*dx[sel],1)>=0,1.,-1.)[:,None];clusters=[]
            for z,d in zip(sel,dirs):
                found=False
                for axis,members in clusters:
                    if np.dot(axis,d)>=np.cos(20*RAD):members.append(z);found=True;break
                if not found:clusters.append((d,[z]))
            arms=[axis for axis,zz in clusters if len(zz)>=3 and np.ptp(rr[zz])>=2.-EPS]
            if len(arms)>=3:return True
        return False
    def validate(self,rows,reps,q,branch=True):
        if len(rows)>8192:return False,'member_cap',{}
        if len(q)>128:return False,'knot_cap',{}
        if not np.isfinite(q).all() or len(q)<2:return False,'invalid_model',{}
        s,d,t,_,_=project(self.x[rows],q);ang=np.degrees(np.arccos(np.clip(abs(np.sum(self.t[rows]*t,1)),0,1)))
        met=dict(residual_max=float(d.max(initial=0)),residual_q95=float(np.quantile(d,.95)),tangent_max=float(ang.max(initial=0)))
        if met['residual_max']>1+EPS or met['residual_q95']>.5+EPS:return False,'residual',met
        if met['tangent_max']>30+EPS or not np.isfinite(ang).all():return False,'tangent',met
        v=np.diff(q,axis=0);ln=np.linalg.norm(v,axis=1);v=v/np.maximum(ln[:,None],1e-30)
        turns=np.degrees(np.arccos(np.clip(np.sum(v[:-1]*v[1:],1),-1,1)));pos=np.cumsum(ln)[:-1]
        window=max((turns[(pos>=ss-8-EPS)&(pos<=ss+EPS)].sum() for ss in pos),default=0.)
        met.update(vertex_turn=float(turns.max(initial=0)),window_turn=float(window))
        if met['vertex_turn']>30+EPS or window>60+EPS:return False,'turn',met
        if segment_contact(q):return False,'self_contact',met
        intervals,length,run,gap,total=self.support(reps,q);met.update(supported_length=length,longest_run=run,max_gap=gap,total_gap=total)
        if gap>1.5+EPS:return False,'unsupported_gap',met
        if branch and self.branch(reps,q):return False,'branch',met
        return True,'accepted',met
    def fit(self,rows,reps,template,count=True):
        if count:
            if self.fit_count>=30000:return None,'fit_cap',{}
            self.fit_count+=1
        x=self.x[rows];template=clean(template)
        if len(rows)>8192:return None,'member_cap',{}
        direction=self.t[rows[0]].copy();center=x.mean(0);w=np.ones(len(x))
        for _ in range(3):
            center=np.average(x,axis=0,weights=w);dx=x-center
            _,vv=np.linalg.eigh((dx*w[:,None]).T@dx);direction=vv[:,-1]
            if np.dot(direction,self.t[rows[0]])<0:direction=-direction
            s=dx@direction;res=np.linalg.norm(dx-s[:,None]*direction,axis=1);bins=np.floor(s-s.min()).astype(np.int64);_,inv,cnt=np.unique(bins,return_inverse=True,return_counts=True)
            w=np.minimum(1.,.5/np.maximum(res,1e-30))/cnt[inv]
        q=center+np.array([s.min(),s.max()])[:,None]*direction
        if np.linalg.norm(q[1]-q[0])<EPS:q=np.stack([center-EPS*direction,center+EPS*direction])
        q=refine(q);ok,why,met=self.validate(rows,reps,q)
        if ok:return (q,'line'),'accepted',met
        if len(template)<2:return None,why,met
        length=arc(template)[-1];knots=max(2,int(np.ceil(length/4))+1)
        if knots>128:return None,'knot_cap',met
        tt=np.linspace(0,length,knots);q=np.stack([np.interp(tt,arc(template),template[:,k]) for k in range(3)],1)
        ss=project(x,template)[0];j=np.clip(np.searchsorted(tt,ss,side='right')-1,0,knots-2);u=(ss-tt[j])/np.maximum(tt[j+1]-tt[j],1e-30);v=1-u
        bins=np.floor(ss).astype(np.int64);_,inv,cnt=np.unique(bins,return_inverse=True,return_counts=True)
        for _ in range(3):
            res=np.linalg.norm(x-v[:,None]*q[j]-u[:,None]*q[j+1],axis=1);w=np.minimum(1.,.5/np.maximum(res,1e-30))/cnt[inv]
            diag=np.bincount(j,w*v*v,minlength=knots)+np.bincount(j+1,w*u*u,minlength=knots);off=np.bincount(j,w*u*v,minlength=knots-1)
            rhs=np.stack([np.bincount(j,w*v*x[:,k],minlength=knots)+np.bincount(j+1,w*u*x[:,k],minlength=knots) for k in range(3)],1)
            anchor=np.where(diag<1e-12,1.,1e-12);rhs+=anchor[:,None]*q;diag+=anchor
            ab=np.zeros((3,knots));ab[1]=diag;ab[0,1:]=off;ab[2,:-1]=off;q=solve_banded((1,1),ab,rhs,check_finite=False)
        q=refine(q);ok,why,met=self.validate(rows,reps,q)
        return ((q,'polyline') if ok else None),why,met
    def initialize(self,base,chains):
        assigned=np.zeros(len(self.rx),bool)
        for lo,hi in zip(chains['offsets'][:-1],chains['offsets'][1:]):
            reps=chains['nodes'][lo:hi];cid=int(chains['representative_edge_id'][reps[0]]);assert cid>=0
            rows=self.rows_for(reps);assigned[reps]=True;template=self.rx[reps]
            if len(reps)>1:
                a=self.ep[reps[0]];b=self.ep[reps[-1]]
                first=a[np.argmax(np.linalg.norm(a-template[1],axis=1))];last=b[np.argmax(np.linalg.norm(b-template[-2],axis=1))];template=np.vstack([first,template,last])
            fit,why,_=self.fit(rows,reps,template,count=False)
            q,kind=fit if fit else (clean(template),'frozen_baseline')
            self.carriers[cid]=Carrier(cid,reps,rows,q,kind,fit is not None,True,(cid,));self.stats['baseline_'+why]+=1
        for rid in np.flatnonzero(~assigned):
            rows=self.rows_for(np.array([rid]));cid=int(rows.min());q=self.ep[rid].copy()
            if np.linalg.norm(q[1]-q[0])<EPS:q=np.stack([self.rx[rid]-EPS*self.rt[rid],self.rx[rid]+EPS*self.rt[rid]])
            self.carriers[cid]=Carrier(cid,np.array([rid],np.int32),rows,q,'seedlet',True,False,())
        assert sum(len(c.rows) for c in self.carriers.values())==int((self.r['kernel_rep']>=0).sum())
    def candidates(self):
        ids=sorted(k for k,c in self.carriers.items() if c.valid);samples=[];owners=[]
        for cid in ids:
            z=sample(self.carriers[cid].q);samples.append(z);owners.extend([cid]*len(z))
        if not samples:return []
        xyz=np.concatenate(samples);owners=np.asarray(owners,np.int64);tree=cKDTree(xyz);pair_batches=[];saturation=0
        for lo in range(0,len(xyz),4096):
            guard(60);dd,jj=tree.query(xyz[lo:lo+4096],k=min(32,len(xyz)),distance_upper_bound=4.,workers=1)
            if dd.ndim==1:dd=dd[:,None];jj=jj[:,None]
            saturation+=int(np.isfinite(dd[:,-1]).sum());nr,nk=jj.shape;row=np.broadcast_to(np.arange(nr)[:,None],jj.shape)
            target=owners[np.minimum(jj,len(xyz)-1)];source=owners[lo:lo+nr,None];ok=(jj<len(xyz))&(target!=source)
            flat=np.flatnonzero(ok);rr=row.ravel()[flat];dst=target.ravel()[flat]
            if len(flat):
                key=rr*len(self.x)+dst;_,first=np.unique(key,return_index=True);first=np.sort(first);rr=rr[first];dst=dst[first]
                starts=np.r_[0,1+np.flatnonzero(rr[1:]!=rr[:-1])];rank=np.arange(len(rr))-np.repeat(starts,np.diff(np.r_[starts,len(rr)]));keep=rank<8
                aa=owners[lo+rr[keep]];bb=dst[keep];pair_batches.append(np.stack([np.minimum(aa,bb),np.maximum(aa,bb)],1))
        # Final cap is per carrier, independent of how many samples it owns.
        if not pair_batches:return []
        pairs=np.unique(np.concatenate(pair_batches),axis=0);ranked=[];bounds=np.r_[0,1+np.flatnonzero(pairs[1:,0]!=pairs[:-1,0]),len(pairs)]
        for lo,hi in zip(bounds[:-1],bounds[1:]):
            i=int(pairs[lo,0]);a=self.carriers[i];bb=[self.carriers[int(j)] for j in pairs[lo:hi,1]]
            mid=np.asarray([b.q[len(b.q)//2] for b in bb]);_,d,t,_,_=project(mid,a.q)
            ends=np.asarray([b.q[[0,-1]] for b in bb]);bt=ends[:,1]-ends[:,0];bt/=np.maximum(np.linalg.norm(bt,axis=1)[:,None],1e-30)
            angle=np.degrees(np.arccos(np.clip(abs(np.sum(t*bt,1)),0,1)));endpoint=np.linalg.norm(a.q[[0,-1]][None,:,None,:]-ends[:,None,:,:],axis=3).min((1,2));scores=np.minimum(d,endpoint)+angle/30
            ranked.extend((float(score),i,int(j)) for score,j in zip(scores,pairs[lo:hi,1]))
        ranked.sort();degree=Counter();out=[]
        for score,i,j in ranked:
            if degree[i]>=8 or degree[j]>=8:self.stats['candidate_cap']+=1;continue
            degree[i]+=1;degree[j]+=1;out.append((score,i,j))
        self.stats['sample_query_saturated']+=saturation;self.stats['proposed']+=len(out)
        return out
    def proposal(self,a,b,pooling):
        # Longer host first; stable IDs resolve equal host lengths only.
        if (arc(b.q)[-1],-b.cid)>(arc(a.q)[-1],-a.cid):a,b=b,a
        sb,db,tb=extended_s(b.q,a.q);qb=b.q
        if sb[-1]<sb[0]:sb=sb[::-1];db=db[::-1];tb=tb[::-1];qb=qb[::-1]
        length=arc(a.q)[-1];overlap=max(0.,min(length,sb[-1])-max(0.,sb[0]));monotone=bool(np.all(np.diff(sb)>=-EPS))
        tang=qb[-1]-qb[0];tang/=max(np.linalg.norm(tang),1e-30);angle=np.degrees(np.arccos(np.clip(abs(tb@tang),0,1)))
        if overlap>=2-EPS and float(np.median(angle))<=15+EPS and float(np.median(db))>.5+EPS:return None,'parallel',a,b
        if pooling:
            sx,_,_=extended_s(self.x[b.rows],a.q)
            if not monotone or sx.min()<-EPS or sx.max()>length+EPS:return None,'not_contained',a,b
            return a.q.copy(),'containment',a,b
        if monotone and overlap>=min(2.,.5*min(length,arc(qb)[-1]))-EPS:
            q=np.vstack([qb[sb<-EPS],a.q,qb[sb>length+EPS]])
            return clean(q),'overlap',a,b
        dist=np.linalg.norm(a.q[[0,-1],None,:]-b.q[None,[0,-1],:],axis=2);ia,ib=np.unravel_index(dist.argmin(),dist.shape)
        if dist[ia,ib]>1.5+EPS:return None,'endpoint_gap',a,b
        qa=a.q if ia==1 else a.q[::-1];qb=b.q if ib==0 else b.q[::-1];v=qb[0]-qa[-1];gap=np.linalg.norm(v)
        ta=qa[-1]-qa[-2];ta/=max(np.linalg.norm(ta),1e-30);tb=qb[1]-qb[0];tb/=max(np.linalg.norm(tb),1e-30)
        if gap>EPS:
            v/=gap
            if min(v@ta,v@tb)<np.cos(35*RAD)-EPS:return None,'connector',a,b
        if ta@tb<np.cos(30*RAD)-EPS:return None,'endpoint_tangent',a,b
        return clean(np.vstack([qa,qb])),'endpoint',a,b
    def record(self,i,j,op,reason,score,met=None):
        self.records.append(dict(level=self.level,a=int(i),b=int(j),operation=op,reason=reason,cost=float(score),metrics=met or {}));self.stats[reason]+=1
    def pass_once(self,pooling=False):
        candidates=self.candidates();valid=[]
        for n,(score,i,j) in enumerate(candidates):
            if n%256==0:guard(60)
            a,b=self.carriers[i],self.carriers[j];q,op,host,donor=self.proposal(a,b,pooling)
            if q is None:self.record(i,j,'pool' if pooling else 'merge',op,score);continue
            rows=np.r_[a.rows,b.rows];reps=np.r_[a.reps,b.reps]
            if self.fit_count>=30000:self.record(i,j,op,'fit_cap',score);continue
            if pooling:
                self.fit_count+=1;ok,why,met=self.validate(rows,reps,q);fit=(q,host.kind) if ok else None
            else:fit,why,met=self.fit(rows,reps,q)
            if fit is None:self.record(i,j,op,why,score,met);continue
            cost=met['residual_max']+met['tangent_max']/30
            valid.append((cost,i,j,fit,host.cid,op,met))
        valid.sort(key=lambda z:(z[0],z[1],z[2]));choices=defaultdict(list)
        for k,z in enumerate(valid):
            if pooling:
                donor=z[2] if z[1]==z[4] else z[1]
                choices[(donor,2)].append(k)
            else:
                for cid,other in [(z[1],z[2]),(z[2],z[1])]:
                    c=self.carriers[cid];o=self.carriers[other]
                    ds=np.linalg.norm(c.q[[0,-1],None,:]-o.q[None,[0,-1],:],axis=2)
                    port=int(np.unravel_index(ds.argmin(),ds.shape)[0]);choices[(cid,port)].append(k)
        ambiguous_edges=set()
        for (cid,port),ks in choices.items():
            if len(ks)<2:continue
            best=valid[ks[0]][0];near=[k for k in ks if valid[k][0]-best<=.15*max(valid[k][0],1e-15)]
            if len(near)<2:continue
            others=[valid[k][2] if valid[k][1]==cid else valid[k][1] for k in near]
            # Equivalent duplicate alternatives may coexist as support; distinct paths may not.
            ref=self.carriers[others[0]];equivalent=True
            for oid in others[1:]:
                cc=self.carriers[oid];_,dist,tan,_,_=project(sample(cc.q),ref.q);direction=cc.q[-1]-cc.q[0];direction/=max(np.linalg.norm(direction),1e-30)
                if dist.max(initial=0)>.5+EPS or np.min(abs(tan@direction),initial=1)<np.cos(15*RAD):equivalent=False;break
            if not equivalent:
                ambiguous_edges.update(ks);self.aux[cid]=others[:2]
        used=set();accepted=0;alias={k:k for k in self.carriers}
        def root(k):
            while alias[k]!=k:k=alias[k]
            return k
        for vi,(cost,i,j,fit,hid,op,met) in enumerate(valid):
            if vi in ambiguous_edges:self.record(i,j,op,'ambiguous',cost,met);continue
            oi,oj=i,j
            if pooling:
                i,j=root(i),root(j)
                if i==j:continue
                if i!=oi or j!=oj or i in used or j in used:
                    a,b=self.carriers[i],self.carriers[j];q,op,host,donor=self.proposal(a,b,True)
                    if q is None:self.record(i,j,'pool',op,cost);continue
                    if self.fit_count>=30000:self.record(i,j,op,'fit_cap',cost);continue
                    self.fit_count+=1;ok,why,met=self.validate(np.r_[a.rows,b.rows],np.r_[a.reps,b.reps],q)
                    if not ok:self.record(i,j,op,why,cost,met);continue
                    fit=(q,host.kind);hid=host.cid
            elif i in used or j in used:self.record(i,j,op,'round_conflict',cost,met);continue
            a,b=self.carriers[i],self.carriers[j];cid=min(i,j);reps=np.r_[a.reps,b.reps];rows=np.r_[a.rows,b.rows];q,kind=fit
            new=Carrier(cid,reps,rows,q,kind,True,a.baseline or b.baseline,tuple(sorted(set(a.origins+b.origins))),self.next_version);self.next_version+=1
            self.events.append(dict(level=self.level,operation=op,inputs=[[i,a.version],[j,b.version]],output=[cid,new.version],host=hid,kernels=len(rows),reps=len(reps)))
            del self.carriers[i];del self.carriers[j];self.carriers[cid]=new;alias[i]=cid;alias[j]=cid;used.update([i,j]);accepted+=1;self.record(i,j,op,'accepted',cost,met)
        self.stats['accepted_pool' if pooling else 'accepted_merge']+=accepted
        return accepted
    def primary(self,baseline):
        ids=baseline.copy();reason=np.where(ids>=0,0,1).astype(np.uint8);owner=np.full(len(ids),-1,np.int64)
        for c in self.carriers.values():
            owner[c.rows]=c.cid
            active=c.baseline or (len(c.reps)>=3 and len(c.rows)>=6 and self.support(c.reps,c.q)[1]>=4-EPS)
            if active:ids[c.rows]=c.cid;reason[c.rows]=0
            elif c.cid in self.aux:reason[c.rows]=2
        reason[self.r['kernel_rep']<0]=3
        aux=np.full((len(ids),2),-1,np.int64)
        for cid,alts in self.aux.items():
            if cid in self.carriers:
                c=self.carriers[cid];resolved=[]
                for alt in alts:
                    new=int(owner[alt]) if 0<=alt<len(owner) else -1
                    if new>=0 and new!=cid and new not in resolved:
                        target=self.carriers[new]
                        ok,_,_=self.validate(c.rows,c.reps,target.q,branch=False)
                        if ok:resolved.append(new)
                aux[c.rows,:len(resolved[:2])]=resolved[:2]
        return ids,reason,aux,owner
