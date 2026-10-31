"""Unit011 fixed ordered-candidate fit-budget experiment; no local-tangent change."""
from common import *
import common,copy
from core import *
from transfer import TransferEngine,StageJournal,save_state
from pipeline import state_of,restore,load_state,verify_checkpoint
from local_tangent import compare_carriers,verify_shadow
from runner import record_arrays

class BudgetEngine(TransferEngine):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        cfg=common.CFG or {}
        self.fit_limit=int(cfg.get('numeric',{}).get('fit_cap_per_level',40000))
        self.control_fit_limit=int(cfg.get('control_fit_limit',30000))
    def record(self,*args,**kwargs):
        super().record(*args,**kwargs)
        if getattr(self,'_collect_control',False) and not self._control_fit_capped:self.control_records.append(copy.deepcopy(self.records[-1]))
    def fit(self,rows,reps,template,count=True):
        self.guard_calls=getattr(self,"guard_calls",0)+1
        if self.guard_calls%64==0:guard(20)
        if count:
            if self.fit_count>=self.fit_limit:return None,'fit_cap',{}
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
    def pass_once(self,pooling=False):
        assert not pooling,"Frozen unit011 has no pooling"
        assert self.fit_limit>=self.control_fit_limit>=0
        self.initial_aux=copy.deepcopy(self.aux);self.control_valid=[];self.control_records=[];self._collect_control=True;self._control_fit_capped=False
        candidates=self.candidates();valid=[];self.control_initial_stats=Counter(self.stats)
        if hasattr(self,"observer"):self.observer("candidates",self,candidates)
        for n,(score,i,j) in enumerate(candidates):
            if n%256==0:guard(60)
            self._control_fit_capped=False
            a,b=self.carriers[i],self.carriers[j]
            if hasattr(self,"observer"):self.observer("evaluation_begin",self,(i,j))
            q,op,host,donor=self.proposal(a,b,pooling)
            if q is None:self.record(i,j,'pool' if pooling else 'merge',op,score);continue
            rows=np.r_[a.rows,b.rows];reps=np.r_[a.reps,b.reps]
            self._control_fit_capped=self.fit_count>=self.control_fit_limit
            if self._control_fit_capped:self.control_records.append(dict(level=self.level,a=int(i),b=int(j),operation=op,reason="fit_cap",cost=float(score),metrics={}))
            if self.fit_count>=self.fit_limit:self.record(i,j,op,'fit_cap',score);continue
            if pooling:
                self.fit_count+=1;ok,why,met=self.validate(rows,reps,q);fit=(q,host.kind) if ok else None
            else:fit,why,met=self.fit(rows,reps,q)
            if fit is None:self.record(i,j,op,why,score,met);continue
            cost=met['residual_max']+met['tangent_max']/30
            valid.append((cost,i,j,fit,host.cid,op,met))
            if not self._control_fit_capped:self.control_valid.append(valid[-1])
        self._collect_control=False
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
                if hasattr(self,"observer"):self.observer("ambiguity_detected",self,dict(ks=ks,near=near,valid=valid,best=best))
                ambiguous_edges.update(ks);self.aux[cid]=others[:2]
        if hasattr(self,"observer"):self.observer("competition_complete",self,dict(valid_count=len(valid),ambiguous_count=len(ambiguous_edges),valid=valid,choices=choices,ambiguous_edges=ambiguous_edges))
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
                    if self.fit_count>=self.fit_limit:self.record(i,j,op,'fit_cap',cost);continue
                    self.fit_count+=1;ok,why,met=self.validate(np.r_[a.rows,b.rows],np.r_[a.reps,b.reps],q)
                    if not ok:self.record(i,j,op,why,cost,met);continue
                    fit=(q,host.kind);hid=host.cid
            elif i in used or j in used:self.record(i,j,op,'round_conflict',cost,met);continue
            a,b=self.carriers[i],self.carriers[j];cid=min(i,j);reps=np.r_[a.reps,b.reps];rows=np.r_[a.rows,b.rows];q,kind=fit
            new=Carrier(cid,reps,rows,q,kind,True,a.baseline or b.baseline,tuple(sorted(set(a.origins+b.origins))),self.next_version);self.next_version+=1
            self.events.append(dict(level=self.level,operation=op,inputs=[[i,a.version],[j,b.version]],output=[cid,new.version],host=hid,kernels=len(rows),reps=len(reps)))
            del self.carriers[i];del self.carriers[j];self.carriers[cid]=new;alias[i]=cid;alias[j]=cid;used.update([i,j]);accepted+=1;self.record(i,j,op,'accepted',cost,met)
            if hasattr(self,"observer"):self.observer("commit",self,dict(cursor=vi,carrier=new,event=self.events[-1]))
        self.stats['accepted_pool' if pooling else 'accepted_merge']+=accepted
        if hasattr(self,"observer"):self.observer("pass_complete",self,dict(accepted=accepted,valid_count=len(valid)))
        return accepted
    def _commit_precomputed(self,valid,pooling=False):
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
                if hasattr(self,"observer"):self.observer("ambiguity_detected",self,dict(ks=ks,near=near,valid=valid,best=best))
                ambiguous_edges.update(ks);self.aux[cid]=others[:2]
        if hasattr(self,"observer"):self.observer("competition_complete",self,dict(valid_count=len(valid),ambiguous_count=len(ambiguous_edges),valid=valid,choices=choices,ambiguous_edges=ambiguous_edges))
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
            if hasattr(self,"observer"):self.observer("commit",self,dict(cursor=vi,carrier=new,event=self.events[-1]))
        self.stats['accepted_pool' if pooling else 'accepted_merge']+=accepted
        if hasattr(self,"observer"):self.observer("pass_complete",self,dict(accepted=accepted,valid_count=len(valid)))
        return accepted

def replay_control(e):
    shadow=TransferEngine(e.a,e.r,e.t,e.p)
    shadow.carriers=dict(e.carriers);shadow.aux=copy.deepcopy(e.initial_aux);shadow.next_version=e.next_version;shadow.level=e.level
    shadow.fit_count=min(e.fit_count,e.control_fit_limit);shadow.records=copy.deepcopy(e.control_records)
    shadow.stats=Counter(e.control_initial_stats);shadow.stats.update(r['reason'] for r in shadow.records)
    BudgetEngine._commit_precomputed(shadow,list(e.control_valid),False)
    return shadow

EXTRA=('ORDERED_CANDIDATES.npz','COMPETITION_COMPLETE.json','COMPETITION_AUX.pkl','DIAGNOSTIC_MARGINS.pkl','CONTROL_CANDIDATE_STATUS.npz','BUDGET_SPLIT.npz','SHADOW_CONTROL.json')
class BudgetJournal(StageJournal):
    def __call__(self,what,e,data):
        if what=='candidates' and common.CFG and 'control_candidates' in common.CFG:
            z=dict(np.load(common.CFG['control_candidates']));candidate=np.asarray(data,float).reshape(-1,3)
            for actual,key in zip(candidate.T,('cost','a','b')):np.testing.assert_array_equal(actual,z[key])
        if what=='competition_complete':
            shadow=replay_control(e)
            record_arrays(self.out/'CONTROL_CANDIDATE_STATUS.npz',shadow)
            deferred=[r for r in e.control_records if r['reason']=='fit_cap']
            nz(self.out/'BUDGET_SPLIT.npz',a=np.array([r['a'] for r in deferred],np.int64),b=np.array([r['b'] for r in deferred],np.int64),score=np.array([r['cost'] for r in deferred],float))
            try:
                receipt=verify_shadow(shadow,common.CFG)
                if common.CFG and 'control_state' in common.CFG:
                    expected=load_state(common.CFG['control_state'])
                    assert shadow.records==expected['records'],'SHADOW_RECORDS_MISMATCH'
                    assert shadow.stats==expected['stats'],'SHADOW_STATS_MISMATCH'
            except BaseException as exc:
                pk(self.out/'UNPROMOTED_STATE.pkl',state_of(e));pk(self.out/'UNPROMOTED_VALID_FITS.pkl',data['valid']);js(self.out/'SHADOW_CONTROL_REJECTED.json',dict(error=repr(exc),promoted=False));raise
            receipt.update(exact_records=True,exact_stats=True,refit_calls=0,control_fit_limit=e.control_fit_limit,variant_fit_limit=e.fit_limit,variant_fit_count=e.fit_count,additional_fit_attempts=e.fit_count-shadow.fit_count,control_fit_cap_rejections=len(deferred),control_valid=len(e.control_valid),variant_valid=len(data['valid']))
            js(self.out/'SHADOW_CONTROL.json',receipt)
        if what=='pass_complete':
            self.flush(e,data['valid_count']);save_state(e,self.out,self.stage,extra=EXTRA)
        else:super().__call__(what,e,data)

def complete_budget_pass(e,path,stage,pooling):
    assert not pooling,'No pooling in frozen unit011'
    path.mkdir(parents=True,exist_ok=True)
    if (path/'CHECKPOINT.json').exists():
        verify_checkpoint(path,stage);restore(e,load_state(path/'STATE.pkl'));return
    if any(path.iterdir()):raise RuntimeError('INCOMPLETE_PASS_PRESERVED '+str(path))
    js(path/'START.json',dict(utc=now(),pid=os.getpid(),stage=stage,pooling=False,fit_count_before=e.fit_count,next_version=e.next_version,variant='fit_budget_40000',fit_limit=e.fit_limit,control_fit_limit=e.control_fit_limit))
    e.observer=BudgetJournal(path,stage,False);e.pass_once(False)
    verify_checkpoint(path,stage);restore(e,load_state(path/'STATE.pkl'))
    print('PASS_DURABLE',stage,'fits',e.fit_count,'events',len(e.events),'budget',e.fit_limit,flush=True)
