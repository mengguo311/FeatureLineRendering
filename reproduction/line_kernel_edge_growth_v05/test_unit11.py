"""Bounded original-core and shared-fit budget regressions; no complete asset science."""
from common import *
import common,copy,tempfile,unittest,types,sys,inspect
from unittest import mock
from core import Engine
from transfer import TransferEngine,reset_level
from pipeline import state_of,restore,load_state,verify_checkpoint
from test_build import fixture
from test_budget_cap import two_pairs
from test_unit3 import equal
import test_unit7 as t7
from budget_engine import BudgetEngine,replay_control,complete_budget_pass
import budget_runner,continuation_level

UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_011')
SOURCE=Path(__file__).resolve().parent

def reference(cap=30000):
    f=json.loads((UNIT.parent/'unit_007/PARENT_RUN_FROZEN.json').read_text());orig=str(SOURCE/'core.py');p=Path(f['immutable_source_snapshot'][orig]);assert sha(p)==f['source_files'][orig]
    text=p.read_text()
    if cap!=30000:text=text.replace('>=30000','>='+str(cap))
    m=types.ModuleType('unit11_reference_'+str(cap));sys.modules[m.__name__]=m;exec(compile(text,str(p),'exec'),m.__dict__);return m

def config24(out):
    from runner import carrier_arrays
    c=t7.m4_config(out);e=two_pairs();e.level=3
    a=dict(e.a);a['covariance']=np.tile(np.eye(3)*1e-4,(24,1,1));a['opacity']=np.full(24,.7);base=np.repeat([0,6,12,18],6)
    for key,data in [('gaussians',a),('representatives',e.r),('controls',dict(control=e.t[:,None,:],control_index=np.arange(24),derivative_basis=np.ones((24,1)))),('baseline_membership',dict(edge_id=base,reason_code=np.zeros(24,np.uint8)))]:
        with open(c[key],'wb') as f:np.savez_compressed(f,**data)
    with open(c['previous_state'],'wb') as f:pickle.dump(state_of(e),f,protocol=5)
    with open(c['previous_membership'],'wb') as f:np.savez_compressed(f,edge_id=base,carrier_id=base,line_kernel_id=np.arange(24))
    Path(c['previous_carriers']).unlink();carrier_arrays(e,Path(c['previous_carriers']))
    cp=Path(c['previous_checkpoint']);v=json.loads(cp.read_text());v['files']['STATE.pkl']=sha(c['previous_state']);cp.write_text(json.dumps(v))
    c.update(kernel_count=24,numeric=dict(fit_cap_per_level=1),control_fit_limit=1,unit=str(out/'control'),runtime=str(out))
    for p in c['input_files']:c['input_files'][p]=sha(p)
    js(out/'CONTROL_CONFIG.json',c);c['_config_sha256']=sha(out/'CONTROL_CONFIG.json')
    with mock.patch.object(continuation_level,'TransferEngine',BudgetEngine):continuation_level.run(c)
    common.CFG=None;common.END=None;common.START=None
    state=out/'control/scenes/scan24/states/M4';native=out/'control/scenes/scan24/stages/M4_MERGE_ONLY'
    c.update(unit=str(out/'variant'),numeric=dict(fit_cap_per_level=2),control_state=str(state/'STATE.pkl'),control_membership=str(native/'MEMBERSHIP.npz'),control_candidates=str(state/'ORDERED_CANDIDATES.npz'),control_groups=str(native/'GROUPS.json'),changed_tracked_groups=[])
    for p in list(state.iterdir())+list(native.iterdir()):
        if p.is_file():c['input_files'][str(p)]=sha(p)
    js(out/'VARIANT_CONFIG.json',c);c['_config_sha256']=sha(out/'VARIANT_CONFIG.json');return c

class Contracts(unittest.TestCase):
    def setUp(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def tearDown(self):self.setUp()
    def compare(self,base,cap=30000):
        old=reference(cap).Engine(base.a,base.r,base.t,base.p);new=BudgetEngine(base.a,base.r,base.t,base.p)
        for e in (old,new):restore(e,copy.deepcopy(state_of(base)));reset_level(e,4)
        new.control_fit_limit=cap;new.fit_limit=40000
        equal(old.candidates(),new.candidates());reset_level(old,4);reset_level(new,4);saved={}
        def capture(name,e,data):
            if name=='competition_complete':saved.update(valid=copy.deepcopy(data['valid']),records=copy.deepcopy(e.records),fits=e.fit_count)
        old.observer=capture;old.pass_once(False)
        def check(name,e,data):
            if name=='competition_complete':
                equal(sorted(e.control_valid,key=lambda z:(z[0],z[1],z[2])),saved['valid']);equal(e.control_records,saved['records'])
                shadow=replay_control(e)
                for key in ('events','carriers','aux','fit_count','next_version','records','stats'):equal(getattr(shadow,key),getattr(old,key))
                baseline=np.full(len(e.x),-1,np.int64)
                for cid,cc in base.carriers.items():
                    if cc.baseline:baseline[cc.rows]=cid
                equal(shadow.primary(baseline),old.primary(baseline))
                if cap==30000:equal(data['valid'],saved['valid'])
        new.observer=check;new.pass_once(False)
        if cap==30000:
            for key in ('events','carriers','aux','fit_count','next_version','records','stats'):equal(getattr(new,key),getattr(old,key))
        print('SHARED_FIT_CONTROL_EQUAL',len(base.x),'kernels',cap,'cap',old.fit_count,new.fit_count,'fits',len(old.events),len(new.events),'events',flush=True)
    def test_hard_fixtures_and_truncated_shared_fit_control(self):
        for kind in ('straight','duplicate','gentle_curve','curve','S','parallel','T','X','gap','tie'):
            for cap in (30000,1):
                with self.subTest(kind=kind,cap=cap):self.compare(fixture(kind,cls=TransferEngine),cap)
        self.compare(two_pairs(),1)
    def test_real_m3_max128_seedlets(self):
        with mock.patch.object(t7,'UNIT',UNIT):t7.BoundedRegression.test_real_m3_max128_seedlets(self)
    def test_exact_fit_and_competition_scope(self):
        src=(UNIT.parent/'unit_007/source_snapshot/core.py').read_text();fit=src[src.index('    def fit('):src.index('    def initialize(')]
        fit=fit.replace('>=30000','>=self.fit_limit').replace('        if count:\n','        self.guard_calls=getattr(self,"guard_calls",0)+1\n        if self.guard_calls%64==0:guard(20)\n        if count:\n',1)
        self.assertEqual(inspect.getsource(BudgetEngine.fit).strip(),fit.strip())
        tail=src[src.index('        valid.sort(key=lambda z:'):src.index('    def primary(')]
        self.assertEqual(inspect.getsource(BudgetEngine._commit_precomputed).split('\n',1)[1].strip(),tail.strip())
        self.assertNotIn('local_equivalent',inspect.getsource(BudgetEngine.pass_once))
        verify(json.loads((UNIT.parent/'unit_010/PARENT_RUN_FROZEN.json').read_text())['source_files'])
    def test_actual_config_contract(self):
        from freeze_unit11 import make_config
        c,h=make_config();ref=json.loads((UNIT.parent/'unit_007/CONFIG.json').read_text())
        expected=dict(ref['numeric'],fit_cap_per_level=40000);self.assertEqual(c['numeric'],expected);self.assertEqual(c['control_fit_limit'],30000)
        self.assertEqual(c['scene'],'scan24');self.assertEqual(c['kernel_count'],458490);self.assertEqual(c['level'],4)
        for k in ('p','previous_state','previous_checkpoint','previous_membership','baseline_membership','L1_membership','history_memberships'):self.assertEqual(c[k],ref[k])
        self.assertEqual(c['decision_sha256'],sha(UNIT/'DECISION.json'));self.assertEqual(len(h),4);self.assertEqual(c['max_seconds'],1800)
        self.assertEqual(c['source_files'],{str(p):sha(p) for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
        self.assertFalse((UNIT/'source_snapshot').exists());self.assertFalse((UNIT/'scenes').exists())
    def test_native_changed_budget_resume_and_failure_preservation(self):
        for fail in (False,True):
            with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
                out=Path(td);c=config24(out)
                with mock.patch.object(BudgetEngine,'initialize',side_effect=AssertionError('NO_REFIT')):
                    if fail:
                        with mock.patch.object(budget_runner,'statistics_level',side_effect=RuntimeError('INJECTED_AFTER_NATIVE')):
                            with self.assertRaisesRegex(RuntimeError,'INJECTED_AFTER_NATIVE'):budget_runner.run(c)
                    else:budget_runner.run(c)
                state=out/'variant/scenes/scan24/states/M4';native=out/'variant/scenes/scan24/stages/M4_MERGE_ONLY';verify_checkpoint(state,'M4_STATE')
                self.assertEqual(len(load_state(state/'STATE.pkl')['events']),2);self.assertEqual(len(np.load(native/'MEMBERSHIP.npz')['edge_id']),24)
                for cam in ('0012','0036'):self.assertTrue((native/(cam+'_FULL.png')).is_file())
                shadow=json.loads((state/'SHADOW_CONTROL.json').read_text());self.assertEqual(shadow['status'],'VERIFIED');self.assertTrue(shadow['exact_stats']);self.assertEqual(shadow['additional_fit_attempts'],1)
                result=json.loads((out/'variant/RUN_RESULT.json').read_text());self.assertEqual(result['status'],'partial' if fail else 'complete')
                if not fail:
                    compare=json.loads((native/'CONTROL_COMPARISON.json').read_text());self.assertTrue(compare['changed_groups'])
                    sel=json.loads((native/'diagnostics/ADDITIONAL_BUDGET_SELECTION.json').read_text());self.assertEqual(sel['accepted_from_deferred'],1)
                fresh=two_pairs(BudgetEngine)
                with mock.patch.object(fresh,'pass_once',side_effect=AssertionError('NO_RECOMPUTE')):complete_budget_pass(fresh,state,'M4_STATE',False)
                with (state/'STATE.pkl').open('ab') as f:f.write(b'corrupt')
                with self.assertRaisesRegex(RuntimeError,'HASH_MISMATCH'):complete_budget_pass(fresh,state,'M4_STATE',False)
                self.tearDown()
    def test_shadow_failure_blocks_promotion_and_keeps_candidate(self):
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);c=config24(out);bad=load_state(c['control_state']);bad['events']=[];p=out/'bad_control.pkl';pk(p,bad);c['control_state']=str(p);c['input_files'][str(p)]=sha(p)
            with self.assertRaisesRegex(AssertionError,'SHADOW_ACCEPTED_EVENTS_MISMATCH'):budget_runner.run(c)
            root=out/'variant/scenes/scan24';self.assertTrue((root/'states/M4/UNPROMOTED_STATE.pkl').exists());self.assertTrue((root/'states/M4/SHADOW_CONTROL_REJECTED.json').exists());self.assertFalse((root/'stages/M4_MERGE_ONLY').exists())
    def test_incumbent_boundary(self):
        e=two_pairs(BudgetEngine)
        for cc in e.carriers.values():cc.baseline=False
        before=copy.deepcopy(state_of(e))
        with self.assertRaisesRegex(RuntimeError,'INCUMBENT_LOST'):budget_runner.promotion_check(e,np.full(24,-1),np.repeat([0,6,12,18],6),e.r)
        equal(before,state_of(e))

if __name__=='__main__':unittest.main()
