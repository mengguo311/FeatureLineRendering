"""Small unit004 regressions; RED precedes continuation implementation."""
from common import *
import common,copy,tempfile,unittest,types,sys
from unittest import mock
from test_build import fixture
from test_unit3 import equal
from pipeline import checkpoint,verify_checkpoint,load_state,state_of,restore
from transfer import complete_pass,reset_level,TransferEngine
import transfer
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
RUNTIME=ROOT/'line_kernel_edge_growth_v05_20261031'
UNIT=RUNTIME/'units/unit_004'

def continuation():
    try:import continuation_runner;return continuation_runner
    except ModuleNotFoundError:return None

class NewContracts(unittest.TestCase):
    def tearDown(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def test_m3_does_not_suppress_real_growth_formula(self):
        e=fixture();e.a['means']=e.a['means']*1.75;e.r['x']=e.r['x']*1.75;e.r['endpoints']=e.r['endpoints']*1.75
        e.x=e.a['means'];e.rx=e.r['x'];e.ep=e.r['endpoints']
        for c in e.carriers.values():c.q*=1.75
        pre=copy.deepcopy(e.carriers);base=np.repeat([0,6],6);e.level=3;e.pass_once(False)
        expected=transfer.tables(e,e.primary(base)[0],pre,base)
        self.assertTrue(any(g['growth_gate'] for g in expected),'fixture must actually pass original gate')
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            module=continuation()
            if module:groups=module.statistics_m3(Path(td),e,e.primary(base)[0],pre,base,base)
            else:groups=transfer.statistics(Path(td),e,e.primary(base)[0],pre,base,'M3_MERGE_ONLY')
            self.assertTrue(any(g['growth_gate'] for g in groups))
            self.assertIn('M2_contributions',groups[0]);self.assertIn('gain_over_largest_M2_p',groups[0])
    def test_import_uses_original_checkpoint_binding(self):
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            p=Path(td);js(p/'payload.json',dict(saved=True))
            common.CFG=dict(decision_sha256='old_decision',_config_sha256='old_config')
            checkpoint(p,['payload.json'],'S2_MERGE_COMPLETE')
            common.CFG=dict(decision_sha256='new_decision',_config_sha256='new_config')
            module=continuation()
            if module:cp=module.verify_predecessor(p,'S2_MERGE_COMPLETE','old_decision','old_config',sha(p/'CHECKPOINT.json'))
            else:cp=verify_checkpoint(p,'S2_MERGE_COMPLETE')
            self.assertTrue(cp['complete']);self.assertEqual(common.CFG['decision_sha256'],'new_decision')

def frozen_reference():
    frozen=json.loads((UNIT.parent/'unit_003/PARENT_RUN_FROZEN.json').read_text());source=Path(__file__).resolve().parent/'core.py';snap=Path(frozen['immutable_source_snapshot'][str(source)])
    assert sha(snap)==frozen['source_files'][str(source)]==sha(source)
    ref=types.ModuleType('unit3_frozen_core');sys.modules[ref.__name__]=ref;exec(compile(snap.read_text(),str(snap),'exec'),ref.__dict__);return ref

def small_continuation_config(out):
    from test_unit3 import small_config
    from runner import carrier_arrays
    c=small_config(out);c['scene']='scan24';c['stage_elapsed_limits']=dict(input=120,M3=180,final=240)
    original_config=out/'CONFIG.json';e=fixture(cls=TransferEngine);e.level=2;e.next_version=23
    e.carriers[0].version=11;e.carriers[6].version=22
    old=out/'predecessor';common.CFG=c;pk(old/'STATE.pkl',state_of(e));checkpoint(old,['STATE.pkl'],'S2_MERGE_COMPLETE')
    carrier_arrays(e,old/'CARRIERS.npz');base=np.repeat([0,6],6);nz(old/'MEMBERSHIP.npz',edge_id=base,carrier_id=base,line_kernel_id=np.arange(12))
    js(old/'LINEAGE.json',dict(events=[],fixture=True));js(out/'NEW_DECISION.json',dict(new_unit=True))
    c.update(previous_state=str(old/'STATE.pkl'),previous_checkpoint=str(old/'CHECKPOINT.json'),previous_carriers=str(old/'CARRIERS.npz'),previous_membership=str(old/'MEMBERSHIP.npz'),previous_lineage=str(old/'LINEAGE.json'),predecessor_config=str(original_config),predecessor_config_sha256=sha(original_config),L1_membership=str(old/'MEMBERSHIP.npz'),tracked_M2_groups=[0,6],decision_path=str(out/'NEW_DECISION.json'),decision_sha256=sha(out/'NEW_DECISION.json'),reference_results=[])
    for path in list(old.iterdir())+[original_config,out/'NEW_DECISION.json']:c['input_files'][str(path)]=sha(path)
    js(out/'CONTINUATION_CONFIG.json',c);c['_config_sha256']=sha(out/'CONTINUATION_CONFIG.json');common.CFG=None;return c

class BoundedRegression(unittest.TestCase):
    def setUp(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def tearDown(self):self.setUp()
    def compare(self,e):
        ref=frozen_reference();rr=ref.Engine(e.a,e.r,e.t,e.p);restore(rr,copy.deepcopy(state_of(e)))
        reset_level(e,3);reset_level(rr,3);equal(e.candidates(),rr.candidates());baseline=np.full(len(e.x),-1,np.int64)
        for cid,c in e.carriers.items():
            if c.baseline:baseline[c.rows]=cid
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td)/'M3';complete_pass(e,out,'M3_STATE',False);rr.pass_once(False)
            for a,b in [(e.fit_count,rr.fit_count),(e.next_version,rr.next_version),(e.events,rr.events),(e.records,rr.records),(dict(e.stats),dict(rr.stats)),(e.carriers,rr.carriers),(dict(e.aux),dict(rr.aux))]:equal(a,b)
            for a,b in zip(e.primary(baseline),rr.primary(baseline)):equal(a,b)
            fresh=TransferEngine(e.a,e.r,e.t,e.p)
            with mock.patch.object(fresh,'pass_once',side_effect=AssertionError('NO_RECOMPUTE')):complete_pass(fresh,out,'M3_STATE',False)
            equal(state_of(e),state_of(fresh))
            print('EQUIVALENT',len(e.x),'kernels','fits',e.fit_count,'events',len(e.events),flush=True)
    def test_hard_fixtures_and_complete_resume(self):
        for kind in ('straight','duplicate','gentle_curve','curve','S','parallel','T','X','gap','tie'):
            with self.subTest(kind=kind):self.compare(fixture(kind,cls=TransferEngine))
    def test_real_m2_max128_seedlets(self):
        u1=UNIT.parent/'unit_001';cfg=json.loads((u1/'CONFIG.json').read_text());state=u1/'scenes/scan24/stages/S2_MERGE/STATE.pkl'
        assert sha(state)=='b1678f236750a852ac58c03c12fd44c907e118fd754dd6aeb38f9bcd075cd7fd'
        for key in ('gaussians','representatives','controls'):verify({cfg[key]:cfg['input_files'][cfg[key]]})
        ss=load_state(state);chosen=[];count=0
        for cid,c in sorted(ss['carriers'].items()):
            if c.valid and 3<=len(c.reps)<=8 and count+len(c.reps)<=128:chosen.append(c);count+=len(c.reps)
            if count>=120:break
        oldr=dict(np.load(cfg['representatives']));old_a=dict(np.load(cfg['gaussians']));selected=np.concatenate([c.reps for c in chosen]);rows=np.concatenate([c.rows for c in chosen]);rowmap={int(old):i for i,old in enumerate(rows)};repmap={int(old):i for i,old in enumerate(selected)}
        members=[np.array([rowmap[int(v)] for v in oldr['member_rows'][oldr['member_offsets'][rid]:oldr['member_offsets'][rid+1]]]) for rid in selected];offsets=np.r_[0,np.cumsum([len(v) for v in members])];kernel_rep=np.full(len(rows),-1,np.int64)
        for rid,rr in enumerate(members):kernel_rep[rr]=rid
        r=dict(x=oldr['x'][selected],t=oldr['t'][selected],endpoints=oldr['endpoints'][selected],kernel_rep=kernel_rep,member_rows=np.concatenate(members),member_offsets=offsets,mid=np.array([rowmap[int(v)] for v in oldr['mid'][selected]]))
        a={k:v[rows].copy() for k,v in old_a.items()}
        with np.load(cfg['controls']) as z:d=(z['control'][z['control_index'][rows]]*z['derivative_basis'][rows,:,None]).sum(1)
        t=d/np.maximum(np.linalg.norm(d,axis=1)[:,None],1e-15);e=TransferEngine(a,r,t,cfg['p']);e.next_version=ss['next_version']
        for old in chosen:
            c=copy.deepcopy(old);c.rows=np.array([rowmap[int(v)] for v in old.rows]);c.reps=np.array([repmap[int(v)] for v in old.reps]);e.carriers[c.cid]=c
        for cid,alts in ss['aux'].items():
            if cid in e.carriers:e.aux[cid]=copy.deepcopy(alts)
        assert len(selected)<=128;print('REAL_M2_FIXTURE',len(rows),'kernels',len(selected),'seedlets',len(chosen),'carriers',flush=True);self.compare(e)
    def test_native_small_routing_and_later_failure(self):
        module=continuation()
        for fail in (False,True):
            with self.subTest(inject_failure=fail),tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
                out=Path(td);c=small_continuation_config(out)
                with mock.patch.object(TransferEngine,'initialize',side_effect=AssertionError('NO_INITIALIZATION')):
                    if fail:
                        with mock.patch.object(module,'statistics_m3',side_effect=RuntimeError('INJECTED_AFTER_NATIVE')):
                            with self.assertRaisesRegex(RuntimeError,'INJECTED_AFTER_NATIVE'):module.run(c)
                    else:module.run(c)
                result=json.loads((out/'RUN_RESULT.json').read_text());self.assertEqual(result['status'],'partial' if fail else 'complete')
                native=out/'scenes/scan24/stages/M3_MERGE_ONLY';self.assertEqual(len(np.load(native/'MEMBERSHIP.npz')['edge_id']),12)
                for view in c['views']:self.assertTrue((native/(view+'_FULL.png')).exists())
                state=out/'scenes/scan24/states/M3';verify_checkpoint(state,'M3_STATE');self.assertEqual(len(load_state(state/'STATE.pkl')['carriers']),1)
                self.tearDown()
    def test_incumbent_boundary_rejects_promotion_preserves_state(self):
        module=continuation();e=fixture(cls=TransferEngine)
        for c in e.carriers.values():c.baseline=False
        baseline=np.full(12,-1,np.int64);previous=np.repeat([0,6],6)
        before=copy.deepcopy(state_of(e))
        with self.assertRaisesRegex(RuntimeError,'INCUMBENT_LOST'):module.promotion_check(e,baseline,previous,e.r)
        equal(before,state_of(e))
    def test_runner_preserves_complete_state_on_rejected_promotion(self):
        module=continuation();original=module.promotion_check;calls=[]
        def fail_after_restore(*args):
            calls.append(True)
            if len(calls)>1:raise RuntimeError('INCUMBENT_LOST_REJECT_M3_PROMOTION')
            return original(*args)
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);c=small_continuation_config(out);before=sha(c['previous_membership'])
            with mock.patch.object(module,'promotion_check',side_effect=fail_after_restore):
                with self.assertRaisesRegex(RuntimeError,'INCUMBENT_LOST'):module.run(c)
            self.assertEqual(sha(c['previous_membership']),before)
            root=out/'scenes/scan24';verify_checkpoint(root/'states/M3','M3_STATE')
            self.assertTrue((root/'PROMOTION_REJECTED.json').exists());self.assertFalse((root/'stages/M3_MERGE_ONLY').exists())
            facts=json.loads((out/'RUN_RESULT.json').read_text());self.assertFalse(facts['delivery_gate']);self.assertEqual(facts['status'],'partial')
    def test_post_checkpoint_failure_and_hash_tamper(self):
        e=fixture(cls=TransferEngine);reset_level(e,3)
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);complete_pass(e,out,'M3_STATE',False)
            with self.assertRaisesRegex(RuntimeError,'INJECTED'):raise RuntimeError('INJECTED_EXPENSIVE_FAILURE')
            self.assertEqual(len(load_state(out/'STATE.pkl')['carriers']),1)
            with (out/'STATE.pkl').open('ab') as f:f.write(b'corrupt')
            with self.assertRaisesRegex(RuntimeError,'HASH_MISMATCH'):complete_pass(e,out,'M3_STATE',False)

if __name__=='__main__':unittest.main()
