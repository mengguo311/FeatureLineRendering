"""Composite finite-carrier identity, shared oracle and port greedy/MILP."""
from dataclasses import dataclass
from collections import defaultdict
import time,warnings
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import csc_matrix
from geometry_base import *

@dataclass
class Leaf:
    cid:int
    version:int
    rows:np.ndarray
    reps:np.ndarray
    q:np.ndarray
    valid:bool
    baseline:bool
    intervals:np.ndarray
@dataclass(frozen=True)
class Edge:
    eid:int
    a:int
    pa:int
    b:int
    pb:int
    cost:float
    @property
    def benefit(self):return 2.-self.cost
    @property
    def key(self):return (self.a,self.pa,self.b,self.pb)

class Infeasible(Exception):
    def __init__(self,reason,edges):self.reason=reason;self.edges=list(edges)

def endpoint_ports(a,b):
    swapped=(arc(b.q)[-1],-b.cid)>(arc(a.q)[-1],-a.cid)
    aa,bb=(b,a) if swapped else (a,b)
    dd=np.linalg.norm(aa.q[[0,-1],None,:]-bb.q[None,[0,-1],:],axis=2)
    i,j=np.unravel_index(dd.argmin(),dd.shape)
    return (int(j),int(i)) if swapped else (int(i),int(j))

def paths(edges,selected):
    byid={e.eid:e for e in edges};adj=defaultdict(list);used=set()
    for k in selected:
        e=byid[k]
        for cid,p,other,op in [(e.a,e.pa,e.b,e.pb),(e.b,e.pb,e.a,e.pa)]:
            if (cid,p) in used:raise Infeasible('port_capacity',selected)
            used.add((cid,p));adj[cid].append((other,p,op,k))
    seen=set();out=[]
    for root in sorted(adj):
        if root in seen:continue
        stack=[root];comp=set();ce=set()
        while stack:
            n=stack.pop()
            if n in comp:continue
            comp.add(n)
            for other,_,_,eid in adj[n]:ce.add(eid);stack.append(other)
        ends=sorted(n for n in comp if len(adj[n])==1)
        if len(ends)!=2:raise Infeasible('cycle',sorted(ce))
        n=ends[0];prev=None;chain=[];entry=1-adj[n][0][1]
        while True:
            chain.append((n,entry==1));seen.add(n)
            nxt=[z for z in adj[n] if z[0]!=prev]
            if not nxt:break
            other,p,op,_=nxt[0]
            if p==entry:raise Infeasible('port_orientation',sorted(ce))
            prev,n=n,other;entry=op
        out.append(chain)
    return out

def chain_edges(chain,edges,selected):
    ids={i for i,_ in chain};return [e.eid for e in edges if e.eid in selected and e.a in ids and e.b in ids]

def check_selection(edges,selected,oracle):
    try:pp=paths(edges,selected)
    except Infeasible as exc:return False,exc.reason,exc.edges,[]
    for ch in pp:
        ok,reason,met=oracle(ch)
        if not ok:return False,reason,chain_edges(ch,edges,selected),pp
    return True,'ok',[],pp

def greedy(edges,oracle,guard=lambda:None):
    selected=[];records=[]
    for e in sorted(edges,key=lambda e:(-e.benefit,*e.key)):
        guard()
        if e.benefit<=0:records.append(dict(edge=e.eid,reason='nonpositive_benefit'));continue
        ok,why,_,_=check_selection(edges,selected+[e.eid],oracle)
        records.append(dict(edge=e.eid,reason='accepted' if ok else why))
        if ok:selected.append(e.eid)
    return sorted(selected),dict(status='greedy_complete',records=records,benefit=sum(e.benefit for e in edges if e.eid in selected))

def joint(edges,oracle,seconds=120,guard=lambda:None,max_rounds=32):
    edges=sorted(edges,key=lambda e:e.key);start=time.monotonic();cuts=[];receipts=[];incumbent=[];status='no_edges'
    if not edges:return [],dict(status=status,cuts=[],solves=[],seconds=0,benefit=0)
    ports=sorted({(e.a,e.pa) for e in edges}|{(e.b,e.pb) for e in edges});pi={p:i for i,p in enumerate(ports)}
    rr=[];cc=[]
    for j,e in enumerate(edges):rr.extend([pi[e.a,e.pa],pi[e.b,e.pb]]);cc.extend([j,j])
    for iteration in range(max_rounds):
        guard();remaining=seconds-(time.monotonic()-start)
        if remaining<=0:status='timeout';break
        r=list(rr);c=list(cc);upper=[1.]*len(ports);idx={e.eid:j for j,e in enumerate(edges)}
        for cut in cuts:
            row=len(upper);r.extend([row]*len(cut['edges']));c.extend(idx[k] for k in cut['edges']);upper.append(len(cut['edges'])-1.)
        mat=csc_matrix((np.ones(len(r)),(r,c)),shape=(len(upper),len(edges)))
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            result=milp(c=np.array([-e.benefit for e in edges]),integrality=np.ones(len(edges)),bounds=Bounds(0,1),constraints=LinearConstraint(mat,-np.inf,np.asarray(upper)),options={'time_limit':remaining,'mip_rel_gap':0.,'threads':2,'parallel':False})
        receipt={'status':int(result.status),'message':str(result.message),'warnings':[str(w.message) for w in warns]}
        for name in ('fun','mip_gap','mip_dual_bound','mip_node_count'):
            v=getattr(result,name,None);receipt[name]=float(v) if v is not None and np.isfinite(v) else None
        receipts.append(receipt)
        if result.x is None:status='solver_no_incumbent';break
        x=np.asarray(result.x)
        if np.max(abs(x-np.rint(x)))>1e-6:status='fractional_incumbent_rejected';break
        chosen=[e.eid for e,v in zip(edges,x) if v>.5]
        ok,why,bad,_=check_selection(edges,chosen,oracle)
        if ok:
            incumbent=sorted(chosen);status='optimal' if result.status==0 else 'feasible_partial';break
        assert bad,'Empty invalid cut'
        cuts.append(dict(reason=why,edges=sorted(bad)))
        status='cut_limit'
    return incumbent,dict(status=status,cuts=cuts,solves=receipts,seconds=time.monotonic()-start,benefit=sum(e.benefit for e in edges if e.eid in incumbent),checked_feasible=True)

class DSU:
    def __init__(self):self.p={}
    def find(self,x):
        self.p.setdefault(x,x)
        while self.p[x]!=x:self.p[x]=self.p[self.p[x]];x=self.p[x]
        return x
    def union(self,a,b):
        a,b=self.find(a),self.find(b)
        if a!=b:self.p[max(a,b)]=min(a,b)

def complete_contexts(seeds,records,cap=128):
    # Repeated incident-record halo closure is exactly undirected raw-record closure.
    d=DSU()
    for a,b in records:d.union(int(a),int(b))
    for _,ids in seeds:
        ids=list(ids)
        for x in ids:d.find(int(x))
        for x in ids[1:]:d.union(int(ids[0]),int(x))
    groups=defaultdict(list)
    for n in list(d.p):groups[d.find(n)].append(n)
    labels=defaultdict(list)
    for tag,ids in seeds:
        if ids:labels[d.find(int(ids[0]))].append(tag)
    return [dict(labels=sorted(labels[k]),carriers=sorted(groups[k]),status='READY' if len(groups[k])<=cap else 'NOT_RUN_OVERSIZE') for k in sorted(labels)]

def parallel(a,b):
    if (arc(b.q)[-1],-b.cid)>(arc(a.q)[-1],-a.cid):a,b=b,a
    sb,db,tb=extended_s(b.q,a.q);qb=b.q
    if sb[-1]<sb[0]:sb=sb[::-1];db=db[::-1];tb=tb[::-1];qb=qb[::-1]
    overlap=max(0.,min(arc(a.q)[-1],sb[-1])-max(0.,sb[0]));v=qb[-1]-qb[0];v/=max(np.linalg.norm(v),1e-30)
    angle=np.degrees(np.arccos(np.clip(abs(tb@v),0,1)))
    return overlap>=2-EPS and np.median(angle)<=15+EPS and np.median(db)>.5+EPS

class PathOracle:
    def __init__(self,leaves,rx=None,rt=None,local_check=None,guard=lambda:None):
        self.leaves=leaves;self.rx=rx;self.rt=rt;self.local_check=local_check;self.guard=guard;self.cache={}
    def __call__(self,chain):
        key=tuple(chain)
        if key not in self.cache:self.cache[key]=self.evaluate(chain)
        return self.cache[key]
    def evaluate(self,chain):
        self.guard();qs=[];ivs=[];offset=0.;prev=None;rows=[];reps=[];domains=[];connectors=[]
        for cid,reverse in chain:
            c=self.leaves[cid]
            if not c.valid:return False,'invalid_leaf',{}
            if self.local_check:
                ok,why=self.local_check(c)
                if not ok:return False,why,{}
            q=c.q[::-1] if reverse else c.q;length=arc(q)[-1]
            if prev is not None:
                v=q[0]-prev[-1];gap=np.linalg.norm(v)
                if gap>1.5+EPS:return False,'endpoint_gap',{}
                ta=prev[-1]-prev[-2];ta/=max(np.linalg.norm(ta),1e-30);tb=q[1]-q[0];tb/=max(np.linalg.norm(tb),1e-30)
                if ta@tb<np.cos(30*RAD)-EPS:return False,'endpoint_tangent',{}
                if gap>EPS and min(v@ta/gap,v@tb/gap)<np.cos(35*RAD)-EPS:return False,'connector',{}
                connectors.append([offset,offset+float(gap)]);offset+=gap
            domains.append(dict(carrier_id=cid,start=float(offset),end=float(offset+length),reverse=bool(reverse)))
            iv=c.intervals.copy()
            if reverse:iv=length-iv[:,::-1]
            ivs.extend((iv+offset).tolist());offset+=length;qs.append(q);prev=q;rows.extend(c.rows.tolist());reps.extend(c.reps.tolist())
        q=clean(np.vstack(qs));v=np.diff(q,axis=0);ln=np.linalg.norm(v,axis=1);v/=np.maximum(ln[:,None],1e-30)
        turns=np.degrees(np.arccos(np.clip(np.sum(v[:-1]*v[1:],axis=1),-1,1)));pos=np.cumsum(ln)[:-1]
        if turns.max(initial=0)>30+EPS:return False,'vertex_turn',{}
        if max((turns[(pos>=s-8-EPS)&(pos<=s+EPS)].sum() for s in pos),default=0)>60+EPS:return False,'window_turn',{}
        # Remove exactly redundant collinear knots for contact testing only.
        # Otherwise a short virtual connector makes adjacent straight support
        # segments appear nonadjacent by array index. Leaf geometry is unchanged.
        cq=[q[0]]
        for k in range(1,len(q)-1):
            a=q[k]-cq[-1];b=q[k+1]-q[k]
            if np.linalg.norm(np.cross(a,b))<=EPS*max(np.linalg.norm(a)*np.linalg.norm(b),1e-30) and a@b>0:continue
            cq.append(q[k])
        cq.append(q[-1])
        if contact_bounded(np.asarray(cq),self.guard):return False,'self_contact',{}
        for i,(a,_) in enumerate(chain):
            for b,_ in chain[i+1:]:
                if parallel(self.leaves[a],self.leaves[b]):return False,'parallel',{}
        if self.rx is not None and len(reps)>=9:
            xx=self.rx[reps];tt=self.rt[reps]
            for center in q:
                self.guard()
                dx=xx-center;rr=np.linalg.norm(dx,axis=1);sel=np.flatnonzero((rr>EPS)&(rr<=4.))
                if len(sel)<9:continue
                dirs=tt[sel]*np.where(np.sum(tt[sel]*dx[sel],axis=1)>=0,1.,-1.)[:,None];clusters=[]
                for z,d in zip(sel,dirs):
                    for axis,members in clusters:
                        if np.dot(axis,d)>=np.cos(20*RAD):members.append(z);break
                    else:clusters.append((d,[z]))
                if sum(len(zz)>=3 and np.ptp(rr[zz])>=2.-EPS for _,zz in clusters)>=3:return False,'branch',{}
        iv,length,run,gap,total=union_intervals(ivs)
        if gap>1.5+EPS:return False,'unsupported_gap',{}
        return True,'ok',dict(leaf_domains_p=domains,unsupported_connectors_p=connectors,coverage=length/max(offset,EPS),supported_intervals=iv.tolist(),supported_length_p=length,longest_continuous_run_p=run,max_gap_p=gap,total_gap_p=total,carrier_length_p=offset,kernels=len(rows),seedlets=len(set(reps)),extent_p=(q.max(axis=0)-q.min(axis=0)).tolist(),bbox_p=[q.min(axis=0).tolist(),q.max(axis=0).tolist()])
