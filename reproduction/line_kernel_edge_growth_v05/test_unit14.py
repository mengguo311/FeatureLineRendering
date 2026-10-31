"""Scan65 transfer regressions; numerical implementation is unchanged from unit013."""
from common import *
import common,copy,tempfile,unittest,types,sys
from unittest import mock
import test_unit12 as t12
import test_unit9 as t9
from test_build import fixture
from test_endpoint_contract import dense
from test_unit3 import equal
from pipeline import state_of,restore,load_state,verify_checkpoint
from transfer import TransferEngine,reset_level
from budget_engine import BudgetEngine
from endpoint_engine import EndpointEngine,complete_endpoint_pass
import endpoint_runner,continuation_level
UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_014')
SOURCE=Path(__file__).resolve().parent

def frozen_endpoint():
    f=json.loads((UNIT.parent/'unit_013/PARENT_RUN_FROZEN.json').read_text())
    original=str(SOURCE/'endpoint_engine.py');p=Path(f['immutable_source_snapshot'][original])
    assert sha(p)==f['source_files'][original]==sha(original)
    m=types.ModuleType('unit13_frozen_endpoint');sys.modules[m.__name__]=m
    exec(compile(p.read_text(),str(p),'exec'),m.__dict__);return m

def native_config(out):
    from runner import carrier_arrays
    c=t9.m4_config(out);e=dense();e.level=3;n=len(e.x);a=dict(e.a)
    a['covariance']=np.tile(np.eye(3)*1e-4,(n,1,1));a['opacity']=np.full(n,.7);base=np.repeat(np.arange(0,n,6),6)
    for key,data in [('gaussians',a),('representatives',e.r),('controls',dict(control=e.t[:,None,:],control_index=np.arange(n),derivative_basis=np.ones((n,1)))),('baseline_membership',dict(edge_id=base,reason_code=np.zeros(n,np.uint8)))]:
        with open(c[key],'wb') as f:np.savez_compressed(f,**data)
    with open(c['previous_state'],'wb') as f:pickle.dump(state_of(e),f,protocol=5)
    with open(c['previous_membership'],'wb') as f:np.savez_compressed(f,edge_id=base,carrier_id=base,line_kernel_id=np.arange(n))
    Path(c['previous_carriers']).unlink();carrier_arrays(e,Path(c['previous_carriers']))
    cp=Path(c['previous_checkpoint']);v=json.loads(cp.read_text());v['files']['STATE.pkl']=sha(c['previous_state']);cp.write_text(json.dumps(v))
    c.update(kernel_count=n,numeric=dict(fit_cap_per_level=30000),control_fit_limit=30000,unit=str(out/'control'),runtime=str(out),stage_elapsed_limits=dict(input=120,M4=180,final=240))
    for p in c['input_files']:c['input_files'][p]=sha(p)
    js(out/'CONTROL_CONFIG.json',c);c['_config_sha256']=sha(out/'CONTROL_CONFIG.json')
    with mock.patch.object(continuation_level,'TransferEngine',BudgetEngine):continuation_level.run(c)
    common.CFG=None;common.END=None;common.START=None
    state=out/'control/scenes/scan65/states/M4';native=out/'control/scenes/scan65/stages/M4_MERGE_ONLY'
    c.update(unit=str(out/'variant'),numeric=dict(fit_cap_per_level=40000),control_state=str(state/'STATE.pkl'),control_candidates=str(state/'ORDERED_CANDIDATES.npz'),control_membership=str(native/'MEMBERSHIP.npz'),control_groups=str(native/'GROUPS.json'),changed_tracked_groups=[])
    for p in list(state.iterdir())+list(native.iterdir()):
        if p.is_file():c['input_files'][str(p)]=sha(p)
    js(out/'VARIANT_CONFIG.json',c);c['_config_sha256']=sha(out/'VARIANT_CONFIG.json');return c

class Contracts(unittest.TestCase):
    def setUp(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def tearDown(self):self.setUp()
    def compare(self,base):
        t12.Contracts.compare(self,base)
        ref=frozen_endpoint();old=ref.EndpointEngine(base.a,base.r,base.t,base.p);new=EndpointEngine(base.a,base.r,base.t,base.p)
        for e in (old,new):restore(e,copy.deepcopy(state_of(base)));reset_level(e,4);e.fit_limit=40000;e.control_fit_limit=30000
        equal(old.candidates(),new.candidates())
        for e in (old,new):reset_level(e,4);e.pass_once(False)
        for key in ('prefix_candidates','supplement_candidates','supplement_ports','supplement_stats','supplement_records','prefix_valid','events','carriers','aux','fit_count','next_version','records','stats'):
            equal(getattr(old,key),getattr(new,key))
        equal(old.primary(np.full(len(base.x),-1)),new.primary(np.full(len(base.x),-1)))
        print('UNIT013_ENDPOINT_EXACT',len(base.x),'kernels',new.fit_count,'fits',flush=True)
    def test_hard_and_dense_prefix_equivalence(self):
        for kind in ('straight','duplicate','gentle_curve','curve','S','parallel','T','X','gap','tie'):
            with self.subTest(kind=kind):self.compare(fixture(kind,cls=TransferEngine))
        self.compare(dense())
    def test_real_scan65_m3_max128_seedlets(self):
        with mock.patch.object(t9,'UNIT',UNIT):t9.BoundedRegression.test_real_m3_max128_seedlets(self)
    def test_endpoint_hard_controls_reversal_and_caps(self):t12.Contracts.test_endpoint_hard_controls_reversal_and_caps(self)
    def test_shared_cap_and_single_merge_per_carrier(self):t12.Contracts.test_shared_cap_and_single_merge_per_carrier(self)
    def test_unchanged_fit_and_competition_implementation(self):t12.Contracts.test_unchanged_fit_and_competition_implementation(self)
    def test_actual_config_contract(self):
        from freeze_unit14 import make_config
        c,h=make_config();old=json.loads((UNIT.parent/'unit_009/CONFIG.json').read_text());ref=json.loads((UNIT.parent/'unit_013/CONFIG.json').read_text())
        for key in ('scene','p','gaussians','controls','representatives','views','previous_state','previous_checkpoint','previous_membership','baseline_membership','L1_membership','history_memberships','tracked_predecessor_groups'):equal(c[key],old[key])
        equal(c['numeric'],ref['numeric']);equal(c['endpoint_supplement'],ref['endpoint_supplement'])
        self.assertEqual(c['decision_sha256'],sha(UNIT/'DECISION.json'));self.assertEqual(c['control_fit_limit'],30000);self.assertEqual(c['shadow_replay_fit_ceiling'],40000)
        self.assertEqual(c['control_actual_fit_count'],18069);self.assertEqual(c['kernel_count'],279616);self.assertEqual(len(h),4)
        self.assertEqual(c['max_seconds'],1800);self.assertEqual(c['stage_elapsed_limits'],dict(input=120,M4=1380,final=1800))
        self.assertEqual(c['source_files'],{str(p):sha(p) for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
        self.assertFalse((UNIT/'source_snapshot').exists());self.assertFalse((UNIT/'scenes').exists())
        frozen=json.loads((UNIT.parent/'unit_013/PARENT_RUN_FROZEN.json').read_text());verify(frozen['source_files'])
        print('SCAN65_CONFIG_VALID',c['p'],len(c['source_files']),'source files',flush=True)
    def test_scan65_native_resume_and_later_failure(self):
        for fail in (False,True):
            with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
                out=Path(td);c=native_config(out)
                with mock.patch.object(EndpointEngine,'initialize',side_effect=AssertionError('NO_REFIT')):
                    if fail:
                        with mock.patch.object(endpoint_runner,'statistics_level',side_effect=RuntimeError('INJECTED_AFTER_NATIVE')):
                            with self.assertRaisesRegex(RuntimeError,'INJECTED_AFTER_NATIVE'):endpoint_runner.run(c)
                    else:endpoint_runner.run(c)
                root=out/'variant/scenes/scan65';state=root/'states/M4';native=root/'stages/M4_MERGE_ONLY'
                verify_checkpoint(state,'M4_STATE');self.assertEqual(len(np.load(native/'MEMBERSHIP.npz')['edge_id']),120)
                for cam in ('0012','0036'):self.assertTrue((native/(cam+'_FULL.png')).is_file())
                self.assertFalse((out/'variant/scenes/scan24').exists())
                shadow=json.loads((state/'SHADOW_CONTROL.json').read_text());self.assertEqual(shadow['status'],'VERIFIED');self.assertTrue(shadow['exact_stats']);self.assertEqual(shadow['refit_calls'],0)
                self.assertEqual(len(load_state(state/'STATE.pkl')['events']),9);self.assertEqual(len(load_state(c['control_state'])['events']),8)
                result=json.loads((out/'variant/RUN_RESULT.json').read_text());self.assertEqual(result['status'],'partial' if fail else 'complete');self.assertEqual(result['scene'],'scan65')
                if not fail:self.assertEqual(result['comparisons']['control_fit_limit'],30000)
                fresh=dense(EndpointEngine)
                with mock.patch.object(fresh,'pass_once',side_effect=AssertionError('NO_RECOMPUTE')):complete_endpoint_pass(fresh,state,'M4_STATE',False)
                equal(state_of(fresh),load_state(state/'STATE.pkl'))
                with (state/'STATE.pkl').open('ab') as f:f.write(b'corrupt')
                with self.assertRaisesRegex(RuntimeError,'HASH_MISMATCH'):complete_endpoint_pass(fresh,state,'M4_STATE',False)
                self.tearDown()
    def test_shadow_failure_and_incumbent_boundary(self):
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);c=native_config(out);bad=load_state(c['control_state']);bad['events']=[];p=out/'bad_control.pkl';pk(p,bad);c['control_state']=str(p);c['input_files'][str(p)]=sha(p)
            with self.assertRaisesRegex(AssertionError,'SHADOW_ACCEPTED_EVENTS_MISMATCH'):endpoint_runner.run(c)
            root=out/'variant/scenes/scan65';self.assertTrue((root/'states/M4/UNPROMOTED_STATE.pkl').exists());self.assertFalse((root/'stages/M4_MERGE_ONLY').exists())
        self.tearDown();e=fixture(cls=EndpointEngine)
        for cc in e.carriers.values():cc.baseline=False
        before=copy.deepcopy(state_of(e))
        with self.assertRaisesRegex(RuntimeError,'INCUMBENT_LOST'):endpoint_runner.promotion_check(e,np.full(12,-1),np.repeat([0,6],6),e.r)
        equal(before,state_of(e))

if __name__=='__main__':unittest.main()
