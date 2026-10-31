"""Durable internal shared-fit controls; numerical protected engine unchanged."""
from common import *
import common
from protected_engine import ProtectedEngine,ProtectedJournal,EXTRA,verify_preservation
from pipeline import state_of,restore,load_state,checkpoint,verify_checkpoint
from transfer import save_state
from local_tangent import compare_carriers

def control_dir(c,kind):return Path(c['unit'])/'scenes'/c['scene']/'states'/f"M{c['level']}"/'controls'/kind

def save_control(e,path,kind):
    path.mkdir(parents=True,exist_ok=True)
    stage=f'M{e.level}_{kind.upper()}_SHARED_CONTROL'
    assert not any(path.iterdir()),'INCOMPLETE_INTERNAL_CONTROL_PRESERVED'
    cfg=common.CFG;base=np.load(cfg['baseline_membership'])['edge_id'];prev=dict(np.load(cfg['previous_membership']))
    ids,reason,aux,owner=e.primary(base)
    pk(path/'STATE.pkl',state_of(e))
    nz(path/'MEMBERSHIP.npz',line_kernel_id=np.arange(len(ids)),edge_id=ids,primitive_id=e.a['primitive_id'],previous_edge_id=prev['edge_id'],baseline_edge_id=base,carrier_id=owner,representative_id=e.r['kernel_rep'],reason_code=reason,auxiliary_carrier_id=aux,provisional=np.ones(len(ids),bool))
    cold=load_state(path/'STATE.pkl');compare_carriers(e.carriers,cold['carriers'])
    assert cold['events']==e.events and cold['records']==e.records and cold['aux']==e.aux and cold['stats']==e.stats
    with np.load(path/'MEMBERSHIP.npz') as z:
        for k,v in zip(('edge_id','reason_code','auxiliary_carrier_id','carrier_id'),(ids,reason,aux,owner)):np.testing.assert_array_equal(z[k],v)
    receipt=dict(status='INTERNAL_SHARED_FIT_CONTROL',kind=kind,accepted=len(e.events),fit_count=e.fit_count,refit_calls=0,cold_state_and_membership_equal=True,historical_replay=False)
    js(path/'CONTROL_PROVENANCE.json',receipt);checkpoint(path,['STATE.pkl','MEMBERSHIP.npz','CONTROL_PROVENANCE.json'],stage)
    return dict(receipt,checkpoint=str(path/'CHECKPOINT.json'),checkpoint_sha256=sha(path/'CHECKPOINT.json'))

def load_control(c,e,kind):
    path=control_dir(c,kind);verify_checkpoint(path,f"M{c['level']}_{kind.upper()}_SHARED_CONTROL")
    fresh=ProtectedEngine(e.a,e.r,e.t,e.p);restore(fresh,load_state(path/'STATE.pkl'));return fresh

class ProgressiveJournal(ProtectedJournal):
    def __call__(self,what,e,data):
        if what=='candidates':
            source=common.CFG.get('previous_protection')
            old=json.loads(Path(source).read_text()) if source else {}
            disputed=set(old.get('disputed_outputs',[]))|set(old.get('inherited_disputed_outputs',[]))
            self.inherited={cid:(e.carriers[cid].version,e.carriers[cid].rows.copy()) for cid in disputed if cid in e.carriers}
        if what=='controls_verified':
            receipts={kind:save_control(getattr(e,kind+'_shadow'),control_dir(common.CFG,kind),kind) for kind in ('prefix','joint')}
            return super().__call__(what,e,receipts)
        if what=='pass_complete':
            self.flush(e,data['valid_count'])
            # A main state can only be complete while both exact shared-fit controls are durable.
            for kind in ('prefix','joint'):load_control(common.CFG,e,kind)
            owner=np.full(len(e.x),-1,np.int64)
            for cid,cc in e.carriers.items():owner[cc.rows]=cid
            lineage=[]
            for cid,(version,rows) in sorted(self.inherited.items()):
                outputs=np.unique(owner[rows]);assert len(outputs)==1 and outputs[0]>=0,'INHERITED_CARRIER_SPLIT'
                outid=int(outputs[0]);lineage.append(dict(input=[cid,version],output=[outid,e.carriers[outid].version],kernels=len(rows)))
            js(self.out/'DISPUTE_LINEAGE.json',dict(previous_protection=common.CFG.get('previous_protection'),inherited=lineage,inherited_disputed_outputs=sorted({z['output'][0] for z in lineage}),new_disputed_outputs=sorted(e.disputed_output_ids),identity_provisional=True))
            extra=EXTRA+('DISPUTE_LINEAGE.json','controls/prefix/CHECKPOINT.json','controls/joint/CHECKPOINT.json')
            save_state(e,self.out,self.stage,extra=extra);return
        return super().__call__(what,e,data)

def complete_pass(e,path,stage,pooling=False):
    assert not pooling;path.mkdir(parents=True,exist_ok=True)
    if (path/'CHECKPOINT.json').exists():
        verify_checkpoint(path,stage);restore(e,load_state(path/'STATE.pkl'))
        for kind in ('prefix','joint'):load_control(common.CFG,e,kind)
        return
    if any(path.iterdir()):raise RuntimeError('INCOMPLETE_PASS_PRESERVED '+str(path))
    js(path/'START.json',dict(utc=now(),pid=os.getpid(),stage=stage,variant='prefix_protected_endpoint_continuation',fit_limit=e.fit_limit))
    e.observer=ProgressiveJournal(path,stage,False)
    try:e.pass_once(False)
    except BaseException as exc:
        pk(path/'UNPROMOTED_STATE.pkl',state_of(e));js(path/'REJECTED.json',dict(error=repr(exc),promoted=False));raise
    verify_checkpoint(path,stage);restore(e,load_state(path/'STATE.pkl'))
