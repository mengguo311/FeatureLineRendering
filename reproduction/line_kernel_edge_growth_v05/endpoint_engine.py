"""Frozen unit012: bounded endpoint proposals, unchanged original fit/competition."""
from common import *
import common,copy
from core import *
from budget_engine import BudgetEngine
from transfer import TransferEngine,StageJournal,save_state
from pipeline import state_of,restore,load_state,verify_checkpoint
from local_tangent import verify_shadow
from runner import record_arrays

def canonical_scores(e,pairs):
    """Same canonical-pair score and batched arithmetic as core.candidates."""
    if not len(pairs):return []
    ranked=[];bounds=np.r_[0,1+np.flatnonzero(pairs[1:,0]!=pairs[:-1,0]),len(pairs)]
    for lo,hi in zip(bounds[:-1],bounds[1:]):
        i=int(pairs[lo,0]);a=e.carriers[i];bb=[e.carriers[int(j)] for j in pairs[lo:hi,1]]
        mid=np.asarray([b.q[len(b.q)//2] for b in bb]);_,d,t,_,_=project(mid,a.q)
        ends=np.asarray([b.q[[0,-1]] for b in bb]);bt=ends[:,1]-ends[:,0];bt/=np.maximum(np.linalg.norm(bt,axis=1)[:,None],1e-30)
        angle=np.degrees(np.arccos(np.clip(abs(np.sum(t*bt,1)),0,1)));endpoint=np.linalg.norm(a.q[[0,-1]][None,:,None,:]-ends[:,None,:,:],axis=3).min((1,2));scores=np.minimum(d,endpoint)+angle/30
        ranked.extend((float(score),i,int(j)) for score,j in zip(scores,pairs[lo:hi,1]))
    ranked.sort();return ranked

def endpoint_screen(e,pairs):
    """Vectorized exact existing endpoint branch checks; original host/argmin ties."""
    survivors=[];ports={};counts=Counter()
    ids=sorted({int(k) for pair in pairs for k in pair});index={cid:k for k,cid in enumerate(ids)}
    if not ids:return np.empty((0,2),np.int64),ports,counts
    ends=np.asarray([e.carriers[c].q[[0,-1]] for c in ids]);length=np.asarray([arc(e.carriers[c].q)[-1] for c in ids])
    dirs=np.asarray([[e.carriers[c].q[1]-e.carriers[c].q[0],e.carriers[c].q[-1]-e.carriers[c].q[-2]] for c in ids])
    dirs/=np.maximum(np.linalg.norm(dirs,axis=2)[:,:,None],1e-30)
    for start in range(0,len(pairs),4096):
        guard(60);z=pairs[start:start+4096];left=np.array([index[int(k)] for k in z[:,0]]);right=np.array([index[int(k)] for k in z[:,1]])
        swap=length[right]>length[left];aa=np.where(swap,right,left);bb=np.where(swap,left,right);nr=len(z);row=np.arange(nr)
        distance=np.linalg.norm(ends[aa,:,None,:]-ends[bb,None,:,:],axis=3);flat=distance.reshape(nr,4).argmin(1);ia=flat//2;ib=flat%2
        gap=distance[row,ia,ib];v=ends[bb,ib]-ends[aa,ia];v/=np.maximum(gap[:,None],1e-30)
        ta=dirs[aa,ia]*np.where(ia==1,1.,-1.)[:,None];tb=dirs[bb,ib]*np.where(ib==0,1.,-1.)[:,None]
        badgap=gap>1.5+EPS;badconnector=(gap>EPS)&(np.minimum(np.sum(v*ta,1),np.sum(v*tb,1))<np.cos(35*RAD)-EPS)
        badtangent=np.sum(ta*tb,1)<np.cos(30*RAD)-EPS
        counts['endpoint_gap']+=int(badgap.sum());counts['connector']+=int((~badgap&badconnector).sum());counts['endpoint_tangent']+=int((~badgap&~badconnector&badtangent).sum())
        for k in np.flatnonzero(~badgap&~badconnector&~badtangent):
            i,j=map(int,z[k]);pi,pj=(int(ib[k]),int(ia[k])) if swap[k] else (int(ia[k]),int(ib[k]));ports[i,j]=(pi,pj);survivors.append((i,j))
    return np.asarray(survivors,np.int64).reshape(-1,2),ports,counts

def endpoint_supplement(e,prefix,screen_cap=30000,append_cap=10000):
    ids=sorted(cid for cid,c in e.carriers.items() if c.valid);stats=Counter();records=[]
    if not ids:return [],{},dict(stats),records
    xyz=np.concatenate([e.carriers[c].q[[0,-1]] for c in ids]);owner=np.repeat(np.asarray(ids,np.int64),2);side=np.tile([0,1],len(ids));tree=cKDTree(xyz)
    existing={(i,j) for _,i,j in prefix};found=set()
    for lo in range(0,len(xyz),4096):
        guard(60);dd,jj=tree.query(xyz[lo:lo+4096],k=min(32,len(xyz)),distance_upper_bound=1.5+EPS,workers=1)
        if dd.ndim==1:dd=dd[:,None];jj=jj[:,None]
        stats['query_saturated']+=int(np.isfinite(dd[:,-1]).sum())
        for rr in range(len(jj)):
            neighbors=[(float(d),int(owner[k]),int(side[k])) for d,k in zip(dd[rr],jj[rr]) if k<len(xyz)]
            neighbors.sort();cid=int(owner[lo+rr])
            for _,other,_ in neighbors:
                if other==cid:continue
                pair=(min(cid,other),max(cid,other))
                if pair not in existing:found.add(pair)
    pairs=np.asarray(sorted(found),np.int64).reshape(-1,2);stats['unseen_endpoint_pairs']=len(pairs)
    survivors,ports,screen=endpoint_screen(e,pairs);stats.update(screen);ranked=canonical_scores(e,survivors)
    stats['cheap_screen_survivors']=len(ranked);stats['screen_cap']=max(0,len(ranked)-screen_cap)
    used=set();selected=[];selected_ports={}
    for score,i,j in ranked[:screen_cap]:
        if len(records)%256==0:guard(60)
        q,op,_,_=e.proposal(e.carriers[i],e.carriers[j],False);pi,pj=ports[i,j]
        if q is None:why=op
        elif op!='endpoint':why='not_endpoint_'+op
        elif (i,pi) in used or (j,pj) in used:why='endpoint_slot_cap'
        elif len(selected)>=append_cap:why='append_cap'
        else:
            why='selected';used.update(((i,pi),(j,pj)));selected.append((score,i,j));selected_ports[i,j]=(pi,pj)
        stats[why]+=1;records.append((score,i,j,pi,pj,why))
    stats['proposal_checks']=len(records);stats['appended']=len(selected)
    return selected,selected_ports,dict(stats),records

class EndpointEngine(BudgetEngine):
    def candidates(self):
        prefix=super().candidates();self.prefix_candidates=prefix
        suffix,self.supplement_ports,self.supplement_stats,self.supplement_records=endpoint_supplement(self,prefix)
        self.supplement_candidates=suffix
        return prefix+suffix
    def pass_once(self,pooling=False):
        assert not pooling,'Frozen endpoint experiment has no pooling'
        self.initial_aux=copy.deepcopy(self.aux);candidates=self.candidates();valid=[]
        self.prefix_initial_stats=Counter(self.stats)
        if hasattr(self,'observer'):self.observer('candidates',self,candidates)
        def evaluate(batch,supplement):
            for n,(score,i,j) in enumerate(batch):
                if n%256==0:guard(60)
                a,b=self.carriers[i],self.carriers[j]
                if hasattr(self,'observer'):self.observer('evaluation_begin',self,(i,j))
                q,op,host,donor=self.proposal(a,b,False)
                if q is None:self.record(i,j,'merge',op,score);continue
                if supplement:assert op=='endpoint','SUPPLEMENT_OPERATION_CHANGED'
                if self.fit_count>=self.fit_limit:self.record(i,j,op,'fit_cap',score);continue
                fit,why,met=self.fit(np.r_[a.rows,b.rows],np.r_[a.reps,b.reps],q)
                if fit is None:self.record(i,j,op,why,score,met);continue
                valid.append((met['residual_max']+met['tangent_max']/30,i,j,fit,host.cid,op,met))
        evaluate(self.prefix_candidates,False)
        self.prefix_valid=list(valid);self.prefix_records=copy.deepcopy(self.records);self.prefix_stats=Counter(self.stats);self.prefix_fit_count=self.fit_count
        if hasattr(self,'observer'):self.observer('prefix_complete',self,dict(valid=valid))
        evaluate(self.supplement_candidates,True)
        return BudgetEngine._commit_precomputed(self,valid,False)

def replay_prefix(e):
    shadow=TransferEngine(e.a,e.r,e.t,e.p);shadow.carriers=dict(e.carriers);shadow.aux=copy.deepcopy(e.initial_aux)
    shadow.next_version=e.next_version;shadow.level=e.level;shadow.fit_count=e.prefix_fit_count;shadow.records=copy.deepcopy(e.prefix_records);shadow.stats=Counter(e.prefix_stats)
    BudgetEngine._commit_precomputed(shadow,list(e.prefix_valid),False);return shadow

EXTRA=('ORDERED_CANDIDATES.npz','PREFIX_CANDIDATES.npz','SUPPLEMENT_CANDIDATES.npz','SUPPLEMENT_SCREEN.npz','SUPPLEMENT_STATS.json','COMPETITION_COMPLETE.json','COMPETITION_AUX.pkl','DIAGNOSTIC_MARGINS.pkl','CONTROL_CANDIDATE_STATUS.npz','SHADOW_CONTROL.json')
class EndpointJournal(StageJournal):
    def __call__(self,what,e,data):
        if what=='candidates':
            prefix=np.asarray(e.prefix_candidates,float).reshape(-1,3)
            if common.CFG and 'control_candidates' in common.CFG:
                z=dict(np.load(common.CFG['control_candidates']))
                for actual,key in zip(prefix.T,('cost','a','b')):np.testing.assert_array_equal(actual,z[key])
            nz(self.out/'PREFIX_CANDIDATES.npz',cost=prefix[:,0],a=prefix[:,1].astype(np.int64),b=prefix[:,2].astype(np.int64))
            suffix=np.asarray(e.supplement_candidates,float).reshape(-1,3);pp=[e.supplement_ports[i,j] for _,i,j in e.supplement_candidates]
            nz(self.out/'SUPPLEMENT_CANDIDATES.npz',cost=suffix[:,0],a=suffix[:,1].astype(np.int64),b=suffix[:,2].astype(np.int64),ports=np.asarray(pp,np.int8).reshape(-1,2),versions=np.asarray([[e.carriers[i].version,e.carriers[j].version] for _,i,j in e.supplement_candidates],np.int64).reshape(-1,2))
            rr=e.supplement_records
            nz(self.out/'SUPPLEMENT_SCREEN.npz',cost=np.array([z[0] for z in rr]),a=np.array([z[1] for z in rr],np.int64),b=np.array([z[2] for z in rr],np.int64),ports=np.asarray([z[3:5] for z in rr],np.int8).reshape(-1,2),reason=np.asarray([z[5] for z in rr],dtype='U40'))
            js(self.out/'SUPPLEMENT_STATS.json',e.supplement_stats)
            # Candidate generation must finish within the frozen first120s.
            if common.CFG and common.START is not None and time.time()-common.START>common.CFG['stage_elapsed_limits']['input']:raise TimeoutError('proposal generation exceeds input120s')
        if what=='prefix_complete':
            shadow=replay_prefix(e);record_arrays(self.out/'CONTROL_CANDIDATE_STATUS.npz',shadow)
            try:
                receipt=verify_shadow(shadow,common.CFG)
                if common.CFG and 'control_state' in common.CFG:
                    expected=load_state(common.CFG['control_state'])
                    assert shadow.records==expected['records'],'SHADOW_RECORDS_MISMATCH'
                    assert shadow.stats==expected['stats'],'SHADOW_STATS_MISMATCH'
            except BaseException as exc:
                pk(self.out/'UNPROMOTED_STATE.pkl',state_of(e));pk(self.out/'UNPROMOTED_VALID_FITS.pkl',data['valid']);js(self.out/'SHADOW_CONTROL_REJECTED.json',dict(error=repr(exc),promoted=False));raise
            receipt.update(exact_records=True,exact_stats=True,refit_calls=0,prefix_candidates=len(e.prefix_candidates),supplement_candidates=len(e.supplement_candidates),control_fit_limit=e.fit_limit)
            js(self.out/'SHADOW_CONTROL.json',receipt);return
        if what=='pass_complete':self.flush(e,data['valid_count']);save_state(e,self.out,self.stage,extra=EXTRA)
        else:super().__call__(what,e,data)

def complete_endpoint_pass(e,path,stage,pooling):
    assert not pooling;path.mkdir(parents=True,exist_ok=True)
    if (path/'CHECKPOINT.json').exists():verify_checkpoint(path,stage);restore(e,load_state(path/'STATE.pkl'));return
    if any(path.iterdir()):raise RuntimeError('INCOMPLETE_PASS_PRESERVED '+str(path))
    js(path/'START.json',dict(utc=now(),pid=os.getpid(),stage=stage,pooling=False,fit_count_before=e.fit_count,next_version=e.next_version,variant='endpoint_supplement',fit_limit=e.fit_limit))
    e.observer=EndpointJournal(path,stage,False);e.pass_once(False)
    verify_checkpoint(path,stage);restore(e,load_state(path/'STATE.pkl'))
    print('PASS_DURABLE',stage,'fits',e.fit_count,'events',len(e.events),flush=True)
