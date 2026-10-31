"""Bounded real/fixture checks for priority only; no full-scene science."""
from common import *
import common,copy,tempfile,unittest,types,sys
from unittest import mock
from test_build import fixture
from test_endpoint_contract import dense
from test_unit3 import equal
import test_unit8 as t8
import test_unit13 as t13
import test_unit12 as t12
from pipeline import state_of,restore,load_state,verify_checkpoint
from transfer import TransferEngine,reset_level
from endpoint_engine import EndpointEngine
from protected_engine import ProtectedEngine,complete_protected_pass
import endpoint_runner,protected_runner
UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_016')
SOURCE=Path(__file__).resolve().parent

def frozen_endpoint():
    f=json.loads((UNIT.parent/'unit_015/PARENT_RUN_FROZEN.json').read_text());p=Path(f['immutable_source_snapshot'][str(SOURCE/'endpoint_engine.py')]);assert sha(p)==f['source_files'][str(SOURCE/'endpoint_engine.py')]==sha(SOURCE/'endpoint_engine.py')
    m=types.ModuleType('unit15_frozen_endpoint');sys.modules[m.__name__]=m;exec(compile(p.read_text(),str(p),'exec'),m.__dict__);return m

def native_config(out):
    with mock.patch.object(t13,'UNIT',UNIT):c=t13.native_config(out)
    c['unit']=str(out/'joint');js(out/'JOINT_CONFIG.json',c);c['_config_sha256']=sha(out/'JOINT_CONFIG.json');endpoint_runner.run(c)
    common.CFG=None;common.END=None;common.START=None
    root=out/'joint/scenes/ficus';state=root/'states/M4';native=root/'stages/M4_MERGE_ONLY'
    c.update(unit=str(out/'protected'),joint_state=str(state/'STATE.pkl'),joint_candidates=str(state/'ORDERED_CANDIDATES.npz'),joint_membership=str(native/'MEMBERSHIP.npz'),joint_groups=str(native/'GROUPS.json'),material_case_ids=[0,6],damaged_case_ids=[0])
    for p in list(state.iterdir())+list(native.iterdir()):
        if p.is_file():c['input_files'][str(p)]=sha(p)
    js(out/'PROTECTED_CONFIG.json',c);c['_config_sha256']=sha(out/'PROTECTED_CONFIG.json');return c

class Contracts(unittest.TestCase):
    def setUp(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def tearDown(self):self.setUp()
    def compare(self,base):
        ref=frozen_endpoint();old=ref.EndpointEngine(base.a,base.r,base.t,base.p);new=ProtectedEngine(base.a,base.r,base.t,base.p)
        for e in (old,new):restore(e,copy.deepcopy(state_of(base)));reset_level(e,4);e.fit_limit=40000;e.control_fit_limit=40000
        f=json.loads((UNIT.parent/'unit_015/PARENT_RUN_FROZEN.json').read_text());original=str(SOURCE/'protected_engine.py');p=Path(f['immutable_source_snapshot'][original])
        assert sha(p)==f['source_files'][original]==sha(original)
        m=types.ModuleType('unit15_frozen_protected');sys.modules[m.__name__]=m;exec(compile(p.read_text(),str(p),'exec'),m.__dict__)
        pinned=m.ProtectedEngine(base.a,base.r,base.t,base.p);restore(pinned,copy.deepcopy(state_of(base)));reset_level(pinned,4);pinned.fit_limit=40000;pinned.control_fit_limit=40000
        equal(old.candidates(),new.candidates());equal(new.prefix_candidates,pinned.candidates()[:len(new.prefix_candidates)]);captured={}
        def capture(name,e,data):
            if name=='competition_complete':captured.update(valid=copy.deepcopy(data['valid']),ambiguous={(data['valid'][k][1],data['valid'][k][2]) for k in data['ambiguous_edges']})
        old.observer=capture;old.pass_once(False);new.pass_once(False);pinned.pass_once(False)
        equal(state_of(new),state_of(pinned))
        for attr in ('joint_ambiguous_pairs','protection_conflicts','disputed_output_ids','protected_input_ids','protected_output_ids'):equal(getattr(new,attr),getattr(pinned,attr))
        for attr in ('prefix_shadow','joint_shadow'):equal(state_of(getattr(new,attr)),state_of(getattr(pinned,attr)))
        for key in ('prefix_candidates','supplement_candidates','supplement_ports','supplement_stats','supplement_records','prefix_valid','prefix_records','prefix_fit_count'):
            equal(getattr(old,key),getattr(new,key))
        equal(captured['valid'],sorted(new.shared_valid,key=lambda z:(z[0],z[1],z[2])));equal(captured['ambiguous'],new.joint_ambiguous_pairs)
        for key in ('events','carriers','aux','fit_count','next_version','records','stats'):equal(getattr(old,key),getattr(new.joint_shadow,key))
        self.assertEqual(old.fit_count,new.fit_count)
        used=[cid for ev in new.events for cid,_ in ev['inputs']];self.assertEqual(len(used),len(set(used)))
        before=copy.deepcopy(state_of(new))
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            p=Path(td)/'STATE.pkl';pk(p,state_of(new));fresh=ProtectedEngine(base.a,base.r,base.t,base.p);restore(fresh,load_state(p));equal(before,state_of(fresh))
        print('SHARED_FITS_BOTH_REPLAYS_EXACT',len(base.x),'kernels',new.fit_count,'fits',flush=True)
    def test_hard_dense_and_curve_controls(self):
        for kind in ('straight','duplicate','gentle_curve','curve','S','parallel','T','X','gap','tie'):
            with self.subTest(kind=kind):self.compare(fixture(kind,cls=TransferEngine))
        self.compare(dense())
    def test_real_m3_max128_seedlets(self):
        with mock.patch.object(t8,'UNIT',UNIT):t8.BoundedRegression.test_real_m3_max128_seedlets(self)
    def test_proposal_caps_and_geometry_controls(self):t12.Contracts.test_endpoint_hard_controls_reversal_and_caps(self)
    def test_shared_fit_cap(self):
        for cap in (0,1,4):
            e=dense(ProtectedEngine);e.fit_limit=cap;e.pass_once(False);self.assertEqual(e.fit_count,cap)
    def test_actual_config_contract(self):
        from freeze_unit16 import make_config
        c,h=make_config();old=json.loads((UNIT.parent/'unit_013/CONFIG.json').read_text())
        for key in ('numeric','endpoint_supplement','p','gaussians','controls','representatives','previous_state','previous_checkpoint','previous_membership','control_state','control_membership','views'):equal(c[key],old[key])
        self.assertEqual(c['decision_sha256'],sha(UNIT/'DECISION.json'));self.assertEqual(len(h),4);self.assertEqual(c['kernel_count'],285956)
        self.assertEqual(c['scene'],'ficus');self.assertEqual(c['views'],['test_r_1','test_r_79'])
        self.assertEqual(c['control_fit_limit'],30000);self.assertEqual(c['control_actual_fit_count'],19949)
        self.assertEqual(c['material_case_ids'],[33824,29734]);self.assertEqual(c['damaged_case_ids'],[21870,28829,28837,78077,62169])
        self.assertEqual(c['joint_case_label'],'joint_reference_not_material')
        self.assertEqual(c['max_seconds'],1800);self.assertEqual(c['stage_elapsed_limits'],dict(input=120,M4=1380,final=1800))
        self.assertFalse((UNIT/'source_snapshot').exists());self.assertFalse((UNIT/'scenes').exists())
    def test_native_checkpoint_resume_and_later_failure(self):
        for fail in (False,True):
            with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
                out=Path(td);c=native_config(out)
                with mock.patch.object(ProtectedEngine,'initialize',side_effect=AssertionError('NO_REFIT')):
                    if fail:
                        with mock.patch.object(protected_runner,'statistics_level',side_effect=RuntimeError('INJECTED_AFTER_NATIVE')):
                            with self.assertRaisesRegex(RuntimeError,'INJECTED_AFTER_NATIVE'):protected_runner.run(c)
                    else:protected_runner.run(c)
                root=out/'protected/scenes/ficus';state=root/'states/M4';native=root/'stages/M4_MERGE_ONLY'
                verify_checkpoint(state,'M4_STATE');self.assertEqual(len(np.load(native/'MEMBERSHIP.npz')['edge_id']),120)
                for view in ('test_r_1','test_r_79'):self.assertTrue((native/(view+'_FULL.png')).exists())
                for file in ('SHADOW_CONTROL.json','SHADOW_JOINT.json'):self.assertEqual(json.loads((state/file).read_text())['status'],'VERIFIED')
                prefix=load_state(c['control_state']);saved=load_state(state/'STATE.pkl');self.assertEqual(saved['events'][:len(prefix['events'])],prefix['events'])
                for p in (state/'journal').glob('*.pkl'):
                    with p.open('rb') as f:d=pickle.load(f)
                    self.assertEqual(d['next_version'],d['commits'][-1]['event']['output'][1]+1);self.assertIn(d['phase'],('prefix','supplement'))
                result=json.loads((out/'protected/RUN_RESULT.json').read_text());self.assertEqual(result['status'],'partial' if fail else 'complete')
                fresh=dense(ProtectedEngine)
                with mock.patch.object(fresh,'pass_once',side_effect=AssertionError('NO_RECOMPUTE')):complete_protected_pass(fresh,state,'M4_STATE')
                equal(state_of(fresh),saved)
                with (state/'STATE.pkl').open('ab') as f:f.write(b'corrupt')
                with self.assertRaisesRegex(RuntimeError,'HASH_MISMATCH'):complete_protected_pass(fresh,state,'M4_STATE')
                self.tearDown()
    def test_joint_shadow_mismatch_blocks_promotion(self):
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);c=native_config(out);bad=load_state(c['joint_state']);bad['events']=[];p=out/'bad_joint.pkl';pk(p,bad);c['joint_state']=str(p);c['input_files'][str(p)]=sha(p)
            with self.assertRaisesRegex(AssertionError,'SHADOW_ACCEPTED_EVENTS_MISMATCH'):protected_runner.run(c)
            root=out/'protected/scenes/ficus';self.assertTrue((root/'states/M4/UNPROMOTED_STATE.pkl').exists());self.assertFalse((root/'stages/M4_MERGE_ONLY').exists())

if __name__=='__main__':unittest.main()
