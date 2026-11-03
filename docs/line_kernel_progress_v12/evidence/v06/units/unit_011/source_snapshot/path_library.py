"""Complete finite path library. Invalid fitted subpaths never cut supersets."""
from runtime_io import *
from geometry_base import *
from port_paths import PathOracle,parallel
from pair_model import fit_engine,model_group_guard,map_support,select_greedy,select_joint
from scene_adapter import local_validator

class PathOverflow(Exception):pass

def enumerate_paths(edges,cap,guard=lambda:None):
    adj={};found={}
    for e in edges:
        adj.setdefault(e.a,[]).append((e.pa,e.b,e.pb,e))
        adj.setdefault(e.b,[]).append((e.pb,e.a,e.pa,e))
    def walk(chain,ee):
        guard()
        if len(chain)>=2:
            rev=tuple((cid,not flip) for cid,flip in chain[::-1]);key=min(tuple(chain),rev)
            found[key]=sorted(ee,key=lambda e:e.eid)
            if len(found)>cap:raise PathOverflow('COMPLETE_PATH_CAP')
        cid,flip=chain[-1];exit_port=0 if flip else 1;seen={i for i,_ in chain}
        for p,b,bp,e in sorted(adj.get(cid,[]),key=lambda z:(z[1],z[0],z[2],z[3].eid)):
            if p==exit_port and b not in seen:walk(chain+[(b,bp==1)],ee+[e])
    for cid in sorted(adj):
        for flip in (False,True):walk([(cid,flip)],[])
    out=[]
    for chain,ee in sorted(found.items()):
        benefit=sum(e.benefit for e in ee)
        if benefit<=EPS:continue
        out.append(dict(hid=len(out),model_key=[z for cid,rev in chain for z in (cid,int(rev))],chain=[list(z) for z in chain],leaves=[cid for cid,_ in chain],anchor=min(cid for cid,_ in chain),edge_ids=[e.eid for e in ee],benefit=float(benefit)))
    return out

def branch_at(d,reps,centers,guard):
    if len(reps)<9:return False
    xx=d['representatives']['x'][reps]/d['p'];tt=d['representatives']['t'][reps]
    for center in centers:
        guard();dx=xx-center;rr=np.linalg.norm(dx,axis=1);sel=np.flatnonzero((rr>EPS)&(rr<=4.));clusters=[]
        if len(sel)<9:continue
        dirs=tt[sel]*np.where(np.sum(tt[sel]*dx[sel],axis=1)>=0,1.,-1.)[:,None]
        for z,v in zip(sel,dirs):
            for axis,members in clusters:
                if np.dot(axis,v)>=np.cos(20*RAD):members.append(z);break
            else:clusters.append((v,[z]))
        if sum(len(z)>=3 and np.ptp(rr[z])>=2.-EPS for _,z in clusters)>=3:return True
    return False

def common_model(d,chain,engine,guard=lambda:None):
    guard();local=local_validator(d,d['p']);qs=[];previous=None
    for cid,reverse in chain:
        leaf=d['leaves'][cid]
        if not leaf.valid:return False,'invalid_leaf',{},None
        ok,why=local(leaf)
        if not ok:return False,why,{},None
        q=leaf.q[::-1] if reverse else leaf.q
        if previous is not None:
            v=q[0]-previous[-1];gap=np.linalg.norm(v)
            if gap>1.5+EPS:return False,'endpoint_gap',{},None
            ta=previous[-1]-previous[-2];ta/=max(np.linalg.norm(ta),1e-30)
            tb=q[1]-q[0];tb/=max(np.linalg.norm(tb),1e-30)
            if ta@tb<np.cos(30*RAD)-EPS:return False,'endpoint_tangent',{},None
            if gap>EPS and min(v@ta/gap,v@tb/gap)<np.cos(35*RAD)-EPS:return False,'connector',{},None
        previous=q;qs.append(q)
    ids=sorted(cid for cid,_ in chain);cs=[d['leaves'][i] for i in ids]
    for i,a in enumerate(cs):
        for b in cs[i+1:]:
            if parallel(a,b):return False,'parallel',{},None
    rows=np.concatenate([x.rows for x in cs]);reps=np.concatenate([x.reps for x in cs]);template=clean(np.vstack(qs))
    fit,why,met=engine.fit(rows,reps,template);guard()
    if fit is None:return False,'fit_'+why,dict(fit_metrics=met),None
    q,kind=fit
    same=np.linalg.norm(q[0]-template[0])+np.linalg.norm(q[-1]-template[-1]);reverse=np.linalg.norm(q[-1]-template[0])+np.linalg.norm(q[0]-template[-1])
    if reverse<same:q=q[::-1].copy()
    checks=[];mids=[];length=arc(q)[-1]
    for (cid,flip),oldq in zip(chain,qs):
        leaf=d['leaves'][cid];x=d['asset']['means'][leaf.rows]/d['p'];ext=extended_s(x,q)[0]
        entry=dict(carrier_id=cid,left_excess_p=float(max(0.,-ext.min())),right_excess_p=float(max(0.,ext.max()-length)),outside_kernel_count=int(np.sum((ext<-EPS)|(ext>length+EPS))))
        checks.append(entry)
        if entry['outside_kernel_count']:return False,'finite_domain',dict(member_checks=checks,fit_metrics=met),dict(q=q.tolist(),kind=kind)
        ss=project(sample(oldq),q)[0]
        if np.any(np.diff(ss)<-EPS):return False,'nonmonotone',dict(member_checks=checks),dict(q=q.tolist(),kind=kind)
        mids.append(float(project(np.array([np.array([np.interp(arc(oldq)[-1]/2,arc(oldq),oldq[:,k]) for k in range(3)])]),q)[0][0]))
        old_s=arc(leaf.q);points=np.stack([np.interp(leaf.intervals.reshape(-1),old_s,leaf.q[:,k]) for k in range(3)],1)
        se=extended_s(points,q)[0];entry['support_endpoint_clamped_count']=int(np.sum((se<0)|(se>length)))
        entry['support_endpoint_max_excess_p']=float(max(0.,-se.min(initial=0),se.max(initial=length)-length))
    if np.any(np.diff(mids)<-EPS):return False,'leaf_midpoint_order',dict(member_checks=checks),dict(q=q.tolist(),kind=kind)
    if branch_at(d,reps,np.vstack([template,q]),guard):return False,'branch',dict(member_checks=checks),dict(q=q.tolist(),kind=kind)
    ok,why,metrics=model_group_guard(d,q,[cid for cid,_ in chain],guard)
    metrics.update(member_checks=checks,fit_metrics=met,pooling_not_extension=False,support_is_projected_proxy=True)
    return ok,why,metrics,dict(q=q.tolist(),kind=kind)

def build_banks(d,hs,engine,guard=lambda:None):
    oracle=PathOracle(d['leaves'],d['representatives']['x']/d['p'],d['representatives']['t'],local_validator(d,d['p']),guard)
    banks={'concat':[],'common':[]};records=[]
    for h in hs:
        chain=[tuple(z) for z in h['chain']];ok,why,met=oracle(chain)
        records.append(dict(hid=h['hid'],representation='concat',accepted=ok,reason=why,metrics=met))
        if ok:banks['concat'].append(dict(h,metrics=met))
        before=engine.fit_count;ok,why,met,model=common_model(d,chain,engine,guard)
        records.append(dict(hid=h['hid'],representation='common',accepted=ok,reason=why,metrics=met,model=model,fit_attempts=engine.fit_count-before))
        if ok:banks['common'].append(dict(h,metrics=met,model_q=model['q'],model_kind=model['kind']))
    return banks,records
