"""Frozen-geometry sparse cross-fragment grouping. No parent identity gates."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[key]='2'
import numpy as np
from scipy.spatial import cKDTree
from collections import defaultdict
import itertools,time

RAD=np.pi/180

def representatives(a,s):
    p=float(np.median(s['pixel'][np.isfinite(s['pixel']) & (s['pixel']>0)]))
    d=(s['control'][s['control_index']]*s['derivative_basis'][:,:,None]).sum(1)
    norm=np.linalg.norm(d,axis=1); valid=np.isfinite(d).all(1)&(norm>1e-15)
    t=d/np.maximum(norm[:,None],1e-15); n=len(d); kr=np.full(n,-1,np.int32)
    order=np.lexsort((np.arange(n),a['arc_t'],a['internal_piece_id']))
    piece=a['internal_piece_id'][order]; bounds=np.r_[0,1+np.flatnonzero(piece[1:]!=piece[:-1]),n]
    mids=[]; starts=[]; ends=[]; counts=[]; rows=[]
    for lo,hi in zip(bounds[:-1],bounds[1:]):
        ids=order[lo:hi]; ids=ids[valid[ids]]; j=0
        while j<len(ids):
            k=j+1
            while k<min(j+6,len(ids)) and np.linalg.norm(a['means'][ids[k]]-a['means'][ids[j]])<=2*p: k+=1
            ii=ids[j:k]; rid=len(mids); kr[ii]=rid; mids.append(ii[len(ii)//2]); starts.append(ii[0]); ends.append(ii[-1]); counts.append(len(ii)); rows.extend(ii); j=k
    mid=np.asarray(mids,np.int64); first=np.asarray(starts,np.int64); last=np.asarray(ends,np.int64)
    r=dict(x=a['means'][mid].copy(),t=t[mid].copy(),endpoints=np.stack([a['means'][first],a['means'][last]],1),kernel_rep=kr,mid=mid,first=first,last=last,count=np.asarray(counts,np.int32),member_rows=np.asarray(rows,np.int64),member_offsets=np.r_[0,np.cumsum(counts)],valid_kernel=valid)
    r['length']=np.linalg.norm(r['endpoints'][:,1]-r['endpoints'][:,0],axis=1)
    return r,p

def unique_pairs(pairs):
    if len(pairs)==0:return np.empty((0,2),np.int32)
    pairs=np.sort(np.asarray(pairs,dtype=np.int32).reshape(-1,2),axis=1)
    return np.unique(pairs[pairs[:,0]!=pairs[:,1]],axis=0)

def spatial_pairs(r,p):
    x=r['x']; tree=cKDTree(x); out=[]
    for lo in range(0,len(x),4096):
        dd,jj=tree.query(x[lo:lo+4096],k=min(32,len(x)),distance_upper_bound=4*p,workers=1)
        if dd.ndim==1:dd=dd[:,None];jj=jj[:,None]
        ii=np.broadcast_to(np.arange(lo,lo+len(dd))[:,None],jj.shape); ok=np.isfinite(dd)&(jj<len(x))&(jj!=ii)
        out.append(np.c_[ii[ok],jj[ok]])
    return unique_pairs(np.concatenate(out) if out else [])

def hough_proposals(r,p,progress=lambda *a:None):
    x=r['x'];t=r['t']; n=len(x)
    if not n:return np.empty((0,2),np.int32),[set() for _ in range(n)],dict(families=0,peaks=0,reconciliations=0),{}
    z=(np.arange(256)+.5)/256; phi=np.arange(256)*np.pi*(3-np.sqrt(5)); dirs=np.c_[np.sqrt(1-z*z)*np.cos(phi),np.sqrt(1-z*z)*np.sin(phi),z]
    axis=np.eye(3)[np.argmin(abs(dirs),axis=1)]; u=np.cross(dirs,axis);u/=np.linalg.norm(u,axis=1)[:,None];v=np.cross(dirs,u)
    near=np.empty((n,2),np.int32)
    for lo in range(0,n,4096):
        dot=abs(t[lo:lo+4096]@dirs.T); near[lo:lo+len(dot)]=np.argsort(-dot,axis=1,kind='stable')[:,:2]
    base=np.floor(x/(32*p)).astype(np.int32);frac=x/(32*p)-base; ids=[];blocks=[]
    for shift in itertools.product((-1,0,1),repeat=3):
        mask=np.ones(n,bool)
        for k,q in enumerate(shift):
            if q==-1:mask&=frac[:,k]<.125
            if q==1:mask&=frac[:,k]>=.875
        ii=np.flatnonzero(mask)
        if len(ii):ids.append(ii);blocks.append(base[ii]+shift)
    rid=np.repeat(np.concatenate(ids),2);b=np.repeat(np.concatenate(blocks),2,axis=0);direction=near[np.concatenate(ids)].ravel()
    local=x[rid]-(b+.5)*(32*p); q1=np.floor(np.einsum('ij,ij->i',local,u[direction])/(2*p)).astype(np.int32);q2=np.floor(np.einsum('ij,ij->i',local,v[direction])/(2*p)).astype(np.int32)
    keys=np.c_[b,direction,q1,q2]; order=np.lexsort(tuple(keys[:,j] for j in range(5,-1,-1))); sk=keys[order]
    starts=np.r_[0,1+np.flatnonzero(np.any(sk[1:]!=sk[:-1],axis=1)),len(sk)]; peak=[]
    for lo,hi in zip(starts[:-1],starts[1:]):
        if hi-lo>=6:peak.append((-(hi-lo),tuple(sk[lo,:3]),lo,hi))
    peak.sort(); perblock=defaultdict(int); families=[]; centers=[];axes=[]; fblocks=[]
    for neg,block,lo,hi in peak:
        if perblock[block]>=8:continue
        # Eight candidate peaks per block, not a result-dependent replenishment sweep.
        perblock[block]+=1; members=np.unique(rid[order[lo:hi]]); xx=x[members]; center=xx.mean(0)
        _,vec=np.linalg.eigh((xx-center).T@(xx-center)); d=vec[:,-1]
        projection=(xx-center)@d; residual=np.linalg.norm(xx-center-projection[:,None]*d,axis=1);keep=residual<=p
        members=members[keep];projection=projection[keep]
        if len(members)<6 or np.ptp(projection)<6*p:continue
        families.append(members);centers.append(center);axes.append(d);fblocks.append(block)
    progress('hough_peaks',len(families)); parent=np.arange(len(families)); inv=defaultdict(list)
    for f,mm in enumerate(families):
        for i in mm:inv[int(i)].append(f)
    shared=defaultdict(int)
    for ff in inv.values():
        for a,b in itertools.combinations(ff,2):
            if fblocks[a]!=fblocks[b] and max(abs(fblocks[a][k]-fblocks[b][k]) for k in range(3))<=1:shared[(a,b)]+=1
    def root(a):
        while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
        return a
    reconciled=0
    for (a,b),count in shared.items():
        if count<2 or abs(np.dot(axes[a],axes[b]))<np.cos(10*RAD):continue
        delta=centers[b]-centers[a]
        if max(np.linalg.norm(delta-np.dot(delta,axes[a])*axes[a]),np.linalg.norm(delta-np.dot(delta,axes[b])*axes[b]))>p:continue
        aa,bb=root(a),root(b)
        if aa!=bb:parent[max(aa,bb)]=min(aa,bb);reconciled+=1
    famsets=[set() for _ in range(n)]; pairs=[]; fused=defaultdict(list)
    for f,mm in enumerate(families):
        ff=root(f);fused[ff].extend(mm.tolist())
        for i in mm:famsets[int(i)].add(int(ff))
        # Proposals use each fitted local line; reconciled identity spans blocks.
        mm=mm[np.argsort((x[mm]-centers[f])@axes[f],kind='stable')]
        for step in (1,2):
            aa,bb=mm[:-step],mm[step:];ok=np.linalg.norm(x[aa]-x[bb],axis=1)<=4*p
            pairs.extend(zip(aa[ok],bb[ok]))
    offsets=[0];members=[];ids=[]
    for f,mm in sorted(fused.items()):ids.append(f);members.extend(sorted(set(mm)));offsets.append(len(members))
    trace=dict(family_id=np.asarray(ids,np.int32),member_offsets=np.asarray(offsets,np.int64),members=np.asarray(members,np.int32),peak_center=np.asarray(centers),peak_axis=np.asarray(axes),peak_block=np.asarray(fblocks,np.int32),peak_family=np.asarray([root(f) for f in range(len(families))],np.int32),directions=dirs)
    return unique_pairs(pairs),famsets,dict(families=len(fused),peaks=len(families),reconciliations=reconciled,votes=len(rid),blocks=len(perblock)),trace

def cap_pairs(pairs,r):
    if not len(pairs):return pairs,0
    distances=np.linalg.norm(r['x'][pairs[:,0]]-r['x'][pairs[:,1]],axis=1); order=np.lexsort((pairs[:,1],pairs[:,0],distances));degree=np.zeros(len(r['x']),np.int32);keep=np.zeros(len(pairs),bool)
    for k in order:
        i,j=pairs[k]
        if degree[i]<64 and degree[j]<64:keep[k]=True;degree[i]+=1;degree[j]+=1
    return pairs[keep],int((~keep).sum())

def evaluate(r,p,pairs,famsets=None):
    pairs,capdrop=cap_pairs(pairs,r);m=len(pairs); best=np.full(m,np.inf); ports=np.zeros((m,2),np.int8);gaps=np.full(m,np.inf);angles=np.zeros(m);conn=np.full(m,180.);mind=np.full(m,np.inf)
    for lo in range(0,m,65536):
        sl=slice(lo,lo+65536);i,j=pairs[sl].T;t1,t2=r['t'][i],r['t'][j];theta=np.arccos(np.clip(abs(np.einsum('ij,ij->i',t1,t2)),0,1))/RAD; angles[sl]=theta
        for a,b in itertools.product((0,1),repeat=2):
            delta=r['endpoints'][j,b]-r['endpoints'][i,a]; gap=np.linalg.norm(delta,axis=1);direction=delta/np.maximum(gap[:,None],1e-15)
            out1=t1*(2*a-1);out2=t2*(2*b-1)
            c1=np.einsum('ij,ij->i',direction,out1);c2=np.einsum('ij,ij->i',-direction,out2)
            zero=gap<1e-12*p;opposed=np.einsum('ij,ij->i',out1,-out2)>np.cos(30*RAD);c1=np.where(zero&opposed,1,c1);c2=np.where(zero&opposed,1,c2)
            ca=np.arccos(np.clip(np.minimum(c1,c2),-1,1))/RAD;cost=gap/(1.5*p)+theta/30+ca/35
            legal=(gap<=1.5*p)&(theta<=30+1e-10)&(ca<=35+1e-10);update=legal&(cost<best[sl]); idx=lo+np.flatnonzero(update)
            best[idx]=cost[update];ports[idx]=[a,b];gaps[idx]=gap[update];conn[idx]=ca[update];mind[sl]=np.minimum(mind[sl],gap)
    shared=np.zeros(m,bool)
    if famsets is not None:
        for k in np.flatnonzero(np.isfinite(best)):
            i,j=pairs[k];shared[k]=bool(famsets[i]&famsets[j])
    basecost=best.copy();best[shared]*=.85
    return dict(pair=pairs,port=ports,cost=best,base_cost=basecost,gap=gaps,min_endpoint_gap=mind,tangent_angle=angles,connector_angle=conn,shared_hough_family=shared,cap_dropped=np.asarray(capdrop))

def walks(n,pair,accepted):
    adj=[[] for _ in range(n)]
    for e in np.flatnonzero(accepted):
        i,j=pair[e];adj[i].append((j,e));adj[j].append((i,e))
    seen=np.zeros(n,bool);out=[]
    order=[i for i,a in enumerate(adj) if len(a)==1]+[i for i,a in enumerate(adj) if len(a)==2]
    for start in order:
        if seen[start]:continue
        nodes=[];edges=[];prev=-1;cur=start;cycle=False
        while not seen[cur]:
            seen[cur]=True;nodes.append(cur);nexts=[v for v in adj[cur] if v[0]!=prev]
            if not nexts:break
            nxt,e=nexts[0];edges.append(e)
            if nxt==start:cycle=True;break
            prev,cur=cur,nxt
        out.append((np.asarray(nodes,np.int32),np.asarray(edges,np.int64),cycle))
    return out,adj

def solve(r,p,links):
    n=len(r['x']);m=len(links['pair']);legal=np.isfinite(links['cost']);status=np.where(legal,1,0).astype(np.uint8);ee=np.flatnonzero(legal)
    port=(links['pair'][ee]*2+links['port'][ee]).ravel();edge=np.repeat(ee,2);cost=np.repeat(links['cost'][ee],2)
    order=np.lexsort((edge,cost,port));po=port[order];groups=np.r_[0,1+np.flatnonzero(po[1:]!=po[:-1]),len(po)] if len(po) else np.array([0])
    best=np.full(2*n,-1,np.int64);amb=np.zeros(2*n,bool)
    for lo,hi in zip(groups[:-1],groups[1:]):
        k=po[lo];best[k]=edge[order[lo]]
        if hi-lo>1:
            c1,c2=cost[order[lo]],cost[order[lo+1]];amb[k]=(c2-c1)<=.15*max(c2,1e-15)
    pp=links['pair']*2+links['port'];hasamb=amb[pp].any(1);status[legal&hasamb]=2
    node_ambiguous=amb.reshape(n,2).any(1)
    blocked=node_ambiguous[links['pair']].any(1)
    status[legal&blocked]=2
    accepted=legal&(~blocked)&(best[pp[:,0]]==np.arange(m))&(best[pp[:,1]]==np.arange(m));status[accepted]=3
    components,_=walks(n,links['pair'],accepted)
    for nodes,edges,cycle in components:
        if cycle and len(nodes)<6:status[edges[np.argmax(links['cost'][edges])]]=6;continue
        if len(nodes)>20000:status[edges[19999::20000]]=5
        if len(nodes)<3:continue
        xx=r['x'][nodes]
        if cycle:
            chord=np.roll(xx,-1,axis=0)-xx;dist=np.linalg.norm(chord,axis=1);unit=chord/np.maximum(dist[:,None],1e-15);turn=np.arccos(np.clip(np.sum(np.roll(unit,1,axis=0)*unit,axis=1),-1,1))/RAD
            positions=np.r_[0,np.cumsum(dist[:-1])];length=dist.sum(); tt=np.tile(turn,2);ss=np.r_[positions,positions+length];prefix=np.r_[0,np.cumsum(tt)];left=np.searchsorted(ss,ss-8*p,side='left');sums=prefix[1:]-prefix[left]
            for j in np.flatnonzero(sums[len(nodes):]>90+1e-8):status[edges[(j-1)%len(edges)]]=4
        else:
            chord=np.diff(xx,axis=0);dist=np.linalg.norm(chord,axis=1);unit=chord/np.maximum(dist[:,None],1e-15);turn=np.arccos(np.clip(np.sum(unit[:-1]*unit[1:],axis=1),-1,1))/RAD
            ss=np.cumsum(dist)[:-1];prefix=np.r_[0,np.cumsum(turn)];left=np.searchsorted(ss,ss-8*p,side='left');sums=prefix[1:]-prefix[left]
            for j in np.flatnonzero(sums>90+1e-8):status[edges[j+1]]=4
    accepted=status==3;components,adj=walks(n,links['pair'],accepted);repedge=np.full(n,-1,np.int64);score=np.zeros(n);rep_reason=np.full(n,1,np.uint8);group_rows=[];ordered=[];offsets=[0]
    rep_reason[amb.reshape(n,2).any(1)]=2
    for nodes,edges,cycle in components:
        length=float(r['length'][nodes].sum())
        if len(nodes)<3 or length<4*p:continue
        minimum=int(min(r['member_rows'][r['member_offsets'][i]:r['member_offsets'][i+1]].min() for i in nodes));repedge[nodes]=minimum;conf=1/(1+float(links['cost'][edges].max(initial=0)));score[nodes]=conf;rep_reason[nodes]=0
        group_rows.append(dict(edge_id=minimum,representatives=len(nodes),kernels=int(r['count'][nodes].sum()),supported_length=length,chain_length=float(np.linalg.norm(np.diff(r['x'][nodes],axis=0),axis=1).sum()),extent=np.ptp(r['endpoints'][nodes].reshape(-1,3),axis=0).tolist(),cycle=bool(cycle),score=conf,provisional=True))
        ordered.extend(nodes.tolist());offsets.append(len(ordered))
    kr=r['kernel_rep'];valid=kr>=0;eid=np.full(len(kr),-1,np.int64);scores=np.zeros(len(kr));reason=np.full(len(kr),3,np.uint8);junction=np.zeros(len(kr),bool)
    eid[valid]=repedge[kr[valid]];scores[valid]=score[kr[valid]];reason[valid]=rep_reason[kr[valid]];junction[valid]=amb.reshape(n,2).any(1)[kr[valid]]
    # A seedlet with an ambiguous port is retained only in the auxiliary graph.
    eid[junction]=-1;scores[junction]=0;reason[junction]=2
    links=dict(links,status=status,ambiguous_port=amb.reshape(n,2),best_edge_per_port=best.reshape(n,2))
    return dict(edge_id=eid,score=scores,reason=reason,junction=junction,provisional=np.ones(len(eid),bool),rep_edge_id=repedge,groups=group_rows,links=links,chain_nodes=np.asarray(ordered,np.int32),chain_offsets=np.asarray(offsets,np.int64),max_degree=max((len(a) for a in adj),default=0),max_gap_over_p=float(links['gap'][accepted].max(initial=0)/p))

def run_arrays(a,s,progress=lambda *args:None):
    r,p=representatives(a,s);progress('representatives',len(r['x']),p); pairs=spatial_pairs(r,p);progress('spatial_pairs',len(pairs));baseline=solve(r,p,evaluate(r,p,pairs));progress('baseline_groups',len(baseline['groups']))
    hp,fsets,stats,trace=hough_proposals(r,p,progress);progress('hough_pairs',len(hp));hough=solve(r,p,evaluate(r,p,unique_pairs(np.concatenate([pairs,hp])),fsets));progress('hough_groups',len(hough['groups']))
    return dict(r=r,p=p,baseline=baseline,hough=hough,hough_stats=stats,hough_trace=trace,hough_family_count=stats['families'])
