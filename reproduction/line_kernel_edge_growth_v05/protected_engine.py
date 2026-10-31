"""Unit015 shared fits; protected prefix commits and full joint ambiguity."""
from common import *
import common,copy
from collections import Counter
from core import Carrier
from endpoint_engine import EndpointEngine,EndpointJournal,EXTRA as ENDPOINT_EXTRA,replay_prefix
from budget_engine import BudgetEngine
from transfer import TransferEngine,save_state
from pipeline import state_of,restore,load_state,verify_checkpoint
from local_tangent import verify_shadow,compare_carriers

def verify_exact(shadow,c,joint=False):
    if joint:
        if not c or 'joint_state' not in c:return dict(status='SMALL_FIXTURE_NO_EXTERNAL_CONTROL',refit_calls=0)
        c=dict(c)
        for key in ('state','membership','groups','candidates'):c['control_'+key]=c['joint_'+key]
    receipt=verify_shadow(shadow,c)
    if c and 'control_state' in c:
        expected=load_state(c['control_state'])
        assert shadow.records==expected['records'],'SHADOW_RECORDS_MISMATCH'
        assert shadow.stats==expected['stats'],'SHADOW_STATS_MISMATCH'
    receipt.update(exact_records=True,exact_stats=True,refit_calls=0);return receipt

def verify_preservation(e,prefix,base):
    ids=e.primary(base)[0];old=prefix.primary(base)[0]
    assert not np.any((old>=0)&(ids<0)),'PREFIX_ASSIGNED_LOST'
    for cid,cc in prefix.carriers.items():
        if np.any(old[cc.rows]>=0):
            labels=np.unique(ids[cc.rows]);assert len(labels)==1 and labels[0]>=0,'PREFIX_GROUP_SPLIT'
    for cid in e.protected_output_ids:compare_carriers({cid:e.carriers[cid]},{cid:prefix.carriers[cid]})
    for cid in e.protected_input_ids:assert e.aux.get(cid)==prefix.aux.get(cid),'LOCKED_AUX_CHANGED'
    return ids

class ProtectedEngine(EndpointEngine):
    def pass_once(self,pooling=False):
        assert not pooling
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
        prefix=replay_prefix(self);prefix_receipt=verify_exact(prefix,common.CFG)
        evaluate(self.supplement_candidates,True)
        versions={k:v.version for k,v in self.carriers.items()};fit_count=self.fit_count
        suffix_failures=copy.deepcopy(self.records[len(self.prefix_records):])
        joint=TransferEngine(self.a,self.r,self.t,self.p);restore(joint,copy.deepcopy(state_of(self)));captured={}
        def capture(what,engine,data):
            if what=='competition_complete':captured.update(data)
            elif what=='ambiguity_detected' and hasattr(self,'observer'):self.observer(what,self,data)
        joint.observer=capture;BudgetEngine._commit_precomputed(joint,list(valid),False)
        joint_receipt=verify_exact(joint,common.CFG,True)
        self.prefix_shadow=prefix;self.joint_shadow=joint;self.shared_valid=valid
        ordered=captured['valid'];ambiguous=captured['ambiguous_edges'];self.joint_ambiguous_pairs={(ordered[k][1],ordered[k][2]) for k in ambiguous}
        locked={cid for ev in prefix.events for cid,_ in ev['inputs']};outputs={ev['output'][0] for ev in prefix.events}
        self.protected_input_ids=locked;self.protected_output_ids=outputs
        self.protection_conflicts=[];self.disputed_output_ids=set();by_input={cid:ev['output'][0] for ev in prefix.events for cid,_ in ev['inputs']}
        suffix_pairs={(i,j) for _,i,j in self.supplement_candidates}
        for vi,(cost,i,j,fit,hid,op,met) in enumerate(ordered):
            if (i,j) in suffix_pairs and (i in locked or j in locked):
                affected=sorted({by_input[k] for k in (i,j) if k in locked});self.disputed_output_ids.update(affected)
                self.protection_conflicts.append(dict(a=i,b=j,versions=[versions[i],versions[j]],outputs=affected,joint_ambiguous=vi in ambiguous,cost=cost))
        restore(self,copy.deepcopy(state_of(prefix)));self.fit_count=fit_count
        for rec in suffix_failures:self.record(rec['a'],rec['b'],rec['operation'],rec['reason'],rec['cost'],rec['metrics'])
        for cid in set(self.aux)|set(joint.aux):
            if cid in locked:continue
            if cid in joint.aux:self.aux[cid]=copy.deepcopy(joint.aux[cid][:2])
            else:self.aux.pop(cid,None)
        if hasattr(self,'observer'):
            self.observer('controls_verified',self,dict(prefix=prefix_receipt,joint=joint_receipt))
            self.observer('competition_complete',self,captured)
            for cursor,event in enumerate(prefix.events):self.observer('commit',self,dict(phase='prefix',cursor=cursor,carrier=self.carriers[event['output'][0]],event=event))
        used=set(locked);accepted=0
        for vi,(cost,i,j,fit,hid,op,met) in enumerate(ordered):
            if (i,j) not in suffix_pairs:continue
            if i in locked or j in locked:self.record(i,j,op,'prefix_protected',cost,met);continue
            if vi in ambiguous:self.record(i,j,op,'ambiguous',cost,met);continue
            if i in used or j in used:self.record(i,j,op,'round_conflict',cost,met);continue
            a,b=self.carriers[i],self.carriers[j]
            assert (a.version,b.version)==(versions[i],versions[j]),'SUPPLEMENT_INPUT_VERSION_CHANGED'
            cid=min(i,j);rows=np.r_[a.rows,b.rows];reps=np.r_[a.reps,b.reps];q,kind=fit
            new=Carrier(cid,reps,rows,q,kind,True,a.baseline or b.baseline,tuple(sorted(set(a.origins+b.origins))),self.next_version);self.next_version+=1
            ev=dict(level=self.level,operation=op,inputs=[[i,a.version],[j,b.version]],output=[cid,new.version],host=hid,kernels=len(rows),reps=len(reps))
            self.events.append(ev);del self.carriers[i];del self.carriers[j];self.carriers[cid]=new;used.update((i,j));accepted+=1;self.record(i,j,op,'accepted',cost,met)
            if hasattr(self,'observer'):self.observer('commit',self,dict(phase='supplement',cursor=vi,carrier=new,event=ev))
        self.stats['accepted_merge']+=accepted
        base=np.load(common.CFG['baseline_membership'])['edge_id'] if common.CFG and 'baseline_membership' in common.CFG else np.full(len(self.x),-1,np.int64)
        verify_preservation(self,prefix,base)
        if hasattr(self,'observer'):self.observer('pass_complete',self,dict(accepted=len(self.events),valid_count=len(valid)))
        return len(self.events)

EXTRA=ENDPOINT_EXTRA+('SHADOW_JOINT.json','PROTECTION.json','PROTECTED_INPUTS.npz','JOINT_AMBIGUITY.npz','PROTECTION_CONFLICTS.json')
class ProtectedJournal(EndpointJournal):
    def flush(self,e,cursor):
        if not self.batch:return
        self.batch_index+=1;name=f'DELTA_{self.batch_index:04d}.pkl';last=self.batch[-1]
        next_version=last['event']['output'][1]+1
        pk(self.out/'journal'/name,dict(competition_complete=True,phase=last['phase'],cursor=last['cursor'],commits=self.batch,next_version=next_version))
        js(self.out/'journal'/f'{name}.seal.json',dict(complete=True,file=name,sha256=sha(self.out/'journal'/name),commit_count=len(self.batch),phase=last['phase'],cursor=last['cursor'],next_version=next_version));self.batch=[]
    def __call__(self,what,e,data):
        if what=='candidates':
            if common.CFG and 'joint_candidates' in common.CFG:
                z=dict(np.load(common.CFG['joint_candidates']));a=np.asarray(data,float).reshape(-1,3)
                for actual,key in zip(a.T,('cost','a','b')):np.testing.assert_array_equal(actual,z[key])
            return super().__call__(what,e,data)
        if what=='controls_verified':
            from runner import record_arrays
            record_arrays(self.out/'CONTROL_CANDIDATE_STATUS.npz',e.prefix_shadow)
            js(self.out/'SHADOW_CONTROL.json',data['prefix']);js(self.out/'SHADOW_JOINT.json',data['joint'])
            locked=sorted(e.protected_input_ids);prefix=e.prefix_shadow;versions={cid:version for ev in prefix.events for cid,version in ev['inputs']}
            nz(self.out/'PROTECTED_INPUTS.npz',carrier_id=np.asarray(locked,np.int64),version=np.asarray([versions[k] for k in locked],np.int64),output_id=np.asarray(sorted(e.protected_output_ids),np.int64))
            pairs=sorted(e.joint_ambiguous_pairs);nz(self.out/'JOINT_AMBIGUITY.npz',pairs=np.asarray(pairs,np.int64).reshape(-1,2))
            js(self.out/'PROTECTION_CONFLICTS.json',e.protection_conflicts)
            js(self.out/'PROTECTION.json',dict(prefix_acceptances=len(prefix.events),locked_inputs=len(locked),locked_outputs=sorted(e.protected_output_ids),disputed_outputs=sorted(e.disputed_output_ids),joint_ambiguity_pairs=len(pairs),full_joint_mask_retained=True,refit_calls=0,identity_provisional=True));return
        if what=='pass_complete':self.flush(e,data['valid_count']);save_state(e,self.out,self.stage,extra=EXTRA);return
        super().__call__(what,e,data)

def complete_protected_pass(e,path,stage,pooling=False):
    assert not pooling;path.mkdir(parents=True,exist_ok=True)
    if (path/'CHECKPOINT.json').exists():verify_checkpoint(path,stage);restore(e,load_state(path/'STATE.pkl'));return
    if any(path.iterdir()):raise RuntimeError('INCOMPLETE_PASS_PRESERVED '+str(path))
    js(path/'START.json',dict(utc=now(),pid=os.getpid(),stage=stage,variant='prefix_protected_endpoint',fit_limit=e.fit_limit))
    e.observer=ProtectedJournal(path,stage,False)
    try:e.pass_once(False)
    except BaseException as exc:
        pk(path/'UNPROMOTED_STATE.pkl',state_of(e));js(path/'REJECTED.json',dict(error=repr(exc),promoted=False));raise
    verify_checkpoint(path,stage);restore(e,load_state(path/'STATE.pkl'))
