"""Unit010: local tangent equivalence only; old competition uses shared fits."""
from common import *
import common,copy
from core import *
from transfer import TransferEngine,StageJournal,save_state
from pipeline import state_of,restore,load_state,verify_checkpoint


def equivalence_values(cc,ref):
    x=sample(cc.q);_,dist,tan,_,_=project(x,ref.q)
    chord=cc.q[-1]-cc.q[0];chord/=max(np.linalg.norm(chord),1e-30)
    old_min=float(np.min(abs(tan@chord),initial=1))
    donor=project(x,cc.q)[2]
    local_min=float(np.min(abs(np.sum(tan*donor,axis=1)),initial=1))
    distance=float(dist.max(initial=0));close=distance<=.5+EPS
    return bool(close and old_min>=np.cos(15*RAD)),bool(close and local_min>=np.cos(15*RAD)),distance,old_min,local_min

class LocalTangentEngine(TransferEngine):
    def values(self,cc,ref):
        key=(cc.cid,cc.version,ref.cid,ref.version)
        if key not in self.equivalence_cache:self.equivalence_cache[key]=equivalence_values(cc,ref)
        return self.equivalence_cache[key]
    def local_equivalent(self,cc,ref):return self.values(cc,ref)[1]
    def pass_once(self,pooling=False):
        self.equivalence_cache={};self.initial_aux=copy.deepcopy(self.aux)
        candidates=self.candidates();valid=[]
        if hasattr(self,"observer"):self.observer("candidates",self,candidates)
        for n,(score,i,j) in enumerate(candidates):
            if n%256==0:guard(60)
            a,b=self.carriers[i],self.carriers[j]
            if hasattr(self,"observer"):self.observer("evaluation_begin",self,(i,j))
            q,op,host,donor=self.proposal(a,b,pooling)
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
                cc=self.carriers[oid]
                if not self.local_equivalent(cc,ref):equivalent=False;break
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

def shadow_competition(e,data):
    valid=data['valid'];old_ambiguous=set();new_ambiguous=set();old_aux=copy.deepcopy(e.initial_aux);choices=[];pairs=[]
    for (cid,port),ks in data['choices'].items():
        if len(ks)<2:continue
        best=valid[ks[0]][0];near=[k for k in ks if valid[k][0]-best<=.15*max(valid[k][0],1e-15)]
        if len(near)<2:continue
        others=[valid[k][2] if valid[k][1]==cid else valid[k][1] for k in near]
        ref=e.carriers[others[0]];old_ok=new_ok=True;old_visits=new_visits=0;choice_id=len(choices)
        for oid in others[1:]:
            cc=e.carriers[oid];old,local,d,om,lm=e.values(cc,ref)
            pairs.append((choice_id,cid,port,ref.cid,ref.version,cc.cid,cc.version,d,om,lm,int(old),int(local),int(old_ok),int(new_ok)))
            if old_ok:old_visits+=1;old_ok=old
            if new_ok:new_visits+=1;new_ok=local
            if not old_ok and not new_ok:break
        choices.append(dict(cid=cid,port=port,ref=ref.cid,others=others,old_equivalent=old_ok,local_equivalent=new_ok,old_visits=old_visits,local_visits=new_visits))
        if not old_ok:old_ambiguous.update(ks);old_aux[cid]=others[:2]
        if not new_ok:new_ambiguous.update(ks)
    assert new_ambiguous==data['ambiguous_edges'],'LOCAL_COMPETITION_RECONSTRUCTION_MISMATCH'
    shadow=TransferEngine(e.a,e.r,e.t,e.p);shadow.carriers=dict(e.carriers);shadow.aux=old_aux;shadow.next_version=e.next_version;shadow.level=e.level;shadow.fit_count=e.fit_count
    used=set()
    for vi,(cost,i,j,fit,hid,op,met) in enumerate(valid):
        if vi in old_ambiguous or i in used or j in used:continue
        a,b=shadow.carriers[i],shadow.carriers[j];cid=min(i,j);rows=np.r_[a.rows,b.rows];reps=np.r_[a.reps,b.reps];q,kind=fit
        new=Carrier(cid,reps,rows,q,kind,True,a.baseline or b.baseline,tuple(sorted(set(a.origins+b.origins))),shadow.next_version);shadow.next_version+=1
        shadow.events.append(dict(level=e.level,operation=op,inputs=[[i,a.version],[j,b.version]],output=[cid,new.version],host=hid,kernels=len(rows),reps=len(reps)))
        del shadow.carriers[i];del shadow.carriers[j];shadow.carriers[cid]=new;used.update([i,j])
    return shadow,choices,pairs

def compare_carriers(a,b):
    assert a.keys()==b.keys(),'SHADOW_CARRIER_IDS_MISMATCH'
    for cid in a:
        for k,v in vars(a[cid]).items():
            if isinstance(v,np.ndarray):np.testing.assert_array_equal(v,getattr(b[cid],k))
            else:assert v==getattr(b[cid],k),(cid,k)

def verify_shadow(shadow,c):
    if not c or 'control_state' not in c:return dict(status='SMALL_FIXTURE_NO_EXTERNAL_CONTROL',accepted=len(shadow.events),fit_count=shadow.fit_count)
    expected=load_state(c['control_state']);assert shadow.events==expected['events'],'SHADOW_ACCEPTED_EVENTS_MISMATCH'
    assert shadow.fit_count==expected['fit_count'] and shadow.next_version==expected['next_version']
    compare_carriers(shadow.carriers,expected['carriers']);assert dict(shadow.aux)==dict(expected['aux'])
    base=np.load(c['baseline_membership'])['edge_id'];old=dict(np.load(c['control_membership']))
    for field,actual in zip(('edge_id','reason_code','auxiliary_carrier_id','carrier_id'),shadow.primary(base)):
        np.testing.assert_array_equal(actual,old[field])
    return dict(status='VERIFIED',accepted=len(shadow.events),fit_count=shadow.fit_count,exact_events=True,exact_carriers=True,exact_aux=True,exact_primary_reason_aux_owner=True,control_state=c['control_state'],control_state_sha256=c['input_files'][c['control_state']])

EXTRA=('ORDERED_CANDIDATES.npz','COMPETITION_COMPLETE.json','COMPETITION_AUX.pkl','DIAGNOSTIC_MARGINS.pkl','EQUIVALENCE_CHOICES.npz','EQUIVALENCE_PAIRS.npz','SHADOW_CONTROL.json')
class LocalJournal(StageJournal):
    def __call__(self,what,e,data):
        if what=='candidates' and common.CFG and 'control_candidates' in common.CFG:
            z=dict(np.load(common.CFG['control_candidates']));candidate=np.asarray(data,float).reshape(-1,3)
            np.testing.assert_array_equal(candidate[:,0],z['cost']);np.testing.assert_array_equal(candidate[:,1],z['a']);np.testing.assert_array_equal(candidate[:,2],z['b'])
        if what=='competition_complete':
            shadow,choices,pairs=shadow_competition(e,data)
            keys=('cid','port','ref','old_equivalent','local_equivalent','old_visits','local_visits')
            nz(self.out/'EQUIVALENCE_CHOICES.npz',**{k:np.array([z[k] for z in choices],np.int64) for k in keys},other_offsets=np.r_[0,np.cumsum([len(z['others']) for z in choices])],others=np.array([v for z in choices for v in z['others']],np.int64))
            names=['choice','owner','port','reference','reference_version','other','other_version','distance','old_min_dot','local_min_dot','old_equivalent','local_equivalent','old_visited','local_visited']
            arr=np.asarray(pairs,float).reshape(-1,len(names));nz(self.out/'EQUIVALENCE_PAIRS.npz',names=np.asarray(names),values=arr)
            try:receipt=verify_shadow(shadow,common.CFG)
            except BaseException as exc:
                pk(self.out/'UNPROMOTED_STATE.pkl',state_of(e));pk(self.out/'UNPROMOTED_VALID_FITS.pkl',data['valid']);js(self.out/'SHADOW_CONTROL_REJECTED.json',dict(error=repr(exc),promoted=False));raise
            receipt.update(changed_choices=sum(z['old_equivalent']!=z['local_equivalent'] for z in choices),choices=len(choices),refit_calls=0)
            js(self.out/'SHADOW_CONTROL.json',receipt)
        if what=='pass_complete':
            self.flush(e,data['valid_count']);save_state(e,self.out,self.stage,extra=EXTRA)
        else:super().__call__(what,e,data)

def complete_local_pass(e,path,stage,pooling):
    assert not pooling,'No pooling in the frozen unit010 slice'
    path.mkdir(parents=True,exist_ok=True)
    if (path/'CHECKPOINT.json').exists():
        verify_checkpoint(path,stage);restore(e,load_state(path/'STATE.pkl'));return
    if any(path.iterdir()):raise RuntimeError('INCOMPLETE_PASS_PRESERVED '+str(path))
    js(path/'START.json',dict(utc=now(),pid=os.getpid(),stage=stage,pooling=False,fit_count_before=e.fit_count,next_version=e.next_version,variant='local_tangent_equivalence'))
    e.observer=LocalJournal(path,stage,False);e.pass_once(False)
    verify_checkpoint(path,stage);restore(e,load_state(path/'STATE.pkl'))
    print('PASS_DURABLE',stage,'fits',e.fit_count,'events',len(e.events),'variant local tangent',flush=True)
