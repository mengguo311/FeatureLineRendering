"""Same whole-path geometry checks; endpoint guards use observation ports consistently."""
from port_paths import PathOracle,parallel
from geometry_base import *

def port_join(leaves,ports,left,right):
 a,ra=left;b,rb=right;qa=leaves[a].q[::-1] if ra else leaves[a].q;qb=leaves[b].q[::-1] if rb else leaves[b].q
 v=qb[0]-qa[-1];gap=float(np.linalg.norm(v));meta=dict(gap=gap)
 if gap>1.5+EPS:return False,'endpoint_gap',meta
 aa=ports[(a,0 if ra else 1)];bb=ports[(b,1 if rb else 0)]
 if not aa['known'] or not bb['known']:return False,'observed_port_unknown',meta
 ta=np.asarray(aa['axis']);tb=-np.asarray(bb['axis']);dot=float(ta@tb);meta['observed_tangent_angle_deg']=float(np.degrees(np.arccos(np.clip(dot,-1,1))))
 if dot<np.cos(30*RAD)-EPS:return False,'observed_endpoint_tangent',meta
 if gap>EPS:
  dots=[float(v@ta/gap),float(v@tb/gap)];meta['observed_connector_angles_deg']=[float(np.degrees(np.arccos(np.clip(z,-1,1)))) for z in dots]
  if min(dots)<np.cos(35*RAD)-EPS:return False,'observed_connector',meta
 return True,'ok',meta

class ObservationOracle(PathOracle):
    def __init__(self,leaves,ports,rx=None,rt=None,local_check=None,guard=lambda:None):
        super().__init__(leaves,rx,rt,local_check,guard);self.ports=ports

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
                ok,why,_=port_join(self.leaves,self.ports,prev_info,(cid,reverse))
                if not ok:return False,why,{}
                connectors.append([offset,offset+float(gap)]);offset+=gap
            domains.append(dict(carrier_id=cid,start=float(offset),end=float(offset+length),reverse=bool(reverse)))
            iv=c.intervals.copy()
            if reverse:iv=length-iv[:,::-1]
            ivs.extend((iv+offset).tolist());offset+=length;qs.append(q);prev=q;prev_info=(cid,reverse);rows.extend(c.rows.tolist());reps.extend(c.reps.tolist())
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
