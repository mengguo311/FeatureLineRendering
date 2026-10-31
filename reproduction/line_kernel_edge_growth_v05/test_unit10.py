"""Unit010 bounded regressions: one scientific difference, no full-asset run."""
from common import *
import common,copy,tempfile,unittest,types,sys
from unittest import mock
import test_unit9 as t9
from test_local_tangent import curved_duplicates
from test_build import fixture
from test_unit3 import equal
from pipeline import state_of,restore,load_state,verify_checkpoint
from local_tangent import LocalTangentEngine,equivalence_values,shadow_competition,compare_carriers,complete_local_pass
from transfer import TransferEngine,reset_level
import local_runner,continuation_level
UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_010')
SOURCE=Path(__file__).resolve().parent

def small_config(out,c=None):
    c=t9.m4_config(out) if c is None else c;c['unit']=str(out/'control');c['runtime']=str(out)
    continuation_level.run(c);common.CFG=None;common.END=None;common.START=None
    state=out/'control/scenes/scan65/states/M4';native=out/'control/scenes/scan65/stages/M4_MERGE_ONLY'
    c.update(unit=str(out/'variant'),control_state=str(state/'STATE.pkl'),control_membership=str(native/'MEMBERSHIP.npz'),control_candidates=str(state/'ORDERED_CANDIDATES.npz'),control_groups=str(native/'GROUPS.json'),changed_tracked_groups=[0,6])
    for p in list(state.iterdir())+list(native.iterdir()):
        if p.is_file():c['input_files'][str(p)]=sha(p)
    js(out/'VARIANT_CONFIG.json',c);c['_config_sha256']=sha(out/'VARIANT_CONFIG.json');return c

class Contracts(unittest.TestCase):
    def setUp(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def tearDown(self):self.setUp()
    def compare(self,base):
        original=TransferEngine(base.a,base.r,base.t,base.p);variant=LocalTangentEngine(base.a,base.r,base.t,base.p)
        for e in (original,variant):restore(e,copy.deepcopy(state_of(base)));reset_level(e,4)
        equal(original.candidates(),variant.candidates())
        # Reset statistics changed by the explicit pre-comparison query.
        reset_level(original,4);reset_level(variant,4);captured={}
        def observer(name,e,data):
            if name=='competition_complete':captured['valid']=copy.deepcopy(data['valid']);captured['records']=copy.deepcopy(e.records);captured['fit_count']=e.fit_count
        original.observer=observer;original.pass_once(False)
        def new_observer(name,e,data):
            if name=='competition_complete':
                equal(captured['valid'],data['valid']);equal(captured['records'],e.records);self.assertEqual(captured['fit_count'],e.fit_count)
                shadow,choices,pairs=shadow_competition(e,data);equal(shadow.events,original.events);compare_carriers(shadow.carriers,original.carriers);equal(dict(shadow.aux),dict(original.aux));self.assertEqual(shadow.next_version,original.next_version)
                baseline=np.full(len(e.x),-1,np.int64)
                for cid,cc in base.carriers.items():
                    if cc.baseline:baseline[cc.rows]=cid
                equal(shadow.primary(baseline),original.primary(baseline))
        variant.observer=new_observer;variant.pass_once(False)
        print('PRECOMPETITION_AND_SHADOW_EQUAL',len(base.x),'kernels',original.fit_count,'fits',len(original.events),'old events',len(variant.events),'variant events',flush=True)
    def test_hard_cases_precompetition_and_shadow(self):
        for kind in ('straight','duplicate','gentle_curve','curve','S','parallel','T','X','gap','tie'):
            with self.subTest(kind=kind):self.compare(fixture(kind,cls=TransferEngine))
        self.compare(curved_duplicates(TransferEngine))
    def test_real_max128_seedlets(self):
        with mock.patch.object(t9,'UNIT',UNIT):t9.BoundedRegression.test_real_m3_max128_seedlets(self)
    def test_equivalence_orientation_knots_and_hard_negatives(self):
        e=curved_duplicates();a=copy.deepcopy(e.carriers[0]);b=copy.deepcopy(e.carriers[18])
        self.assertEqual(equivalence_values(b,a)[:2],(False,True))
        b.q=b.q[::-1].copy();self.assertTrue(equivalence_values(b,a)[1])
        b.q=a.q[np.r_[np.arange(0,len(a.q)-1,2),len(a.q)-1]].copy();self.assertTrue(equivalence_values(b,a)[1])
        b.q=a.q+[0,0,.8];self.assertFalse(equivalence_values(b,a)[1])
        # Distinct tangent even at coincident crossing must remain non-equivalent.
        a.q=np.array([[-2.,0,0],[2.,0,0]]);b.q=np.array([[0,-2.,0],[0,2.,0]]);self.assertFalse(equivalence_values(b,a)[1])
        b.q=a.q.copy();self.assertEqual(equivalence_values(b,a)[:2],(True,True))
        theta=.4;b.q=np.array([[0.,0,0],[np.cos(theta),np.sin(theta),0.]])*.2;a.q=np.array([[-1.,0,0],[1.,0,0]])
        self.assertFalse(equivalence_values(b,a)[1])
    def test_native_shadow_resume_and_later_failure(self):
        for fail in (False,True):
            with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
                out=Path(td);c=small_config(out)
                with mock.patch.object(LocalTangentEngine,'initialize',side_effect=AssertionError('NO_INIT')):
                    if fail:
                        with mock.patch.object(local_runner,'statistics_level',side_effect=RuntimeError('INJECTED_AFTER_NATIVE')):
                            with self.assertRaisesRegex(RuntimeError,'INJECTED_AFTER_NATIVE'):local_runner.run(c)
                    else:local_runner.run(c)
                root=out/'variant/scenes/scan65';state=root/'states/M4';verify_checkpoint(state,'M4_STATE');native=root/'stages/M4_MERGE_ONLY'
                self.assertEqual(len(np.load(native/'MEMBERSHIP.npz')['edge_id']),12)
                for cam in ('0012','0036'):self.assertTrue((native/(cam+'_FULL.png')).is_file())
                self.assertEqual(json.loads((state/'SHADOW_CONTROL.json').read_text())['status'],'VERIFIED')
                r=json.loads((out/'variant/RUN_RESULT.json').read_text());self.assertEqual(r['status'],'partial' if fail else 'complete')
                fresh=fixture(cls=LocalTangentEngine)
                with mock.patch.object(fresh,'pass_once',side_effect=AssertionError('NO_RECOMPUTE')):complete_local_pass(fresh,state,'M4_STATE',False)
                self.assertEqual(fresh.level,4);self.tearDown()
    def test_shadow_mismatch_preserves_failed_candidate(self):
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);c=small_config(out);bad=load_state(c['control_state']);bad['events']=[];path=out/'wrong_control.pkl';pk(path,bad);c['control_state']=str(path);c['input_files'][str(path)]=sha(path)
            with self.assertRaisesRegex(AssertionError,'SHADOW_ACCEPTED_EVENTS_MISMATCH'):local_runner.run(c)
            root=out/'variant/scenes/scan65';self.assertTrue((root/'states/M4/UNPROMOTED_STATE.pkl').exists());self.assertTrue((root/'states/M4/SHADOW_CONTROL_REJECTED.json').exists());self.assertFalse((root/'stages/M4_MERGE_ONLY').exists())
    def test_incumbent_loss_blocks_promotion(self):
        e=fixture(cls=LocalTangentEngine)
        for cc in e.carriers.values():cc.baseline=False
        before=copy.deepcopy(state_of(e))
        with self.assertRaisesRegex(RuntimeError,'INCUMBENT_LOST'):local_runner.promotion_check(e,np.full(12,-1,np.int64),np.repeat([0,6],6),e.r)
        equal(before,state_of(e))
    def test_old_sources_unchanged_and_variant_scope(self):
        frozen=json.loads((UNIT.parent/'unit_009/PARENT_RUN_FROZEN.json').read_text());verify(frozen['source_files'])
        src=(SOURCE/'core.py').read_text();expected=src[src.index('    def pass_once('):src.index('    def primary(')]
        old="""                cc=self.carriers[oid];_,dist,tan,_,_=project(sample(cc.q),ref.q);direction=cc.q[-1]-cc.q[0];direction/=max(np.linalg.norm(direction),1e-30)
                if dist.max(initial=0)>.5+EPS or np.min(abs(tan@direction),initial=1)<np.cos(15*RAD):equivalent=False;break"""
        expected=expected.replace(old,"""                cc=self.carriers[oid]
                if not self.local_equivalent(cc,ref):equivalent=False;break""").replace('        candidates=self.candidates();valid=[]','        self.equivalence_cache={};self.initial_aux=copy.deepcopy(self.aux)\n        candidates=self.candidates();valid=[]')
        import inspect
        self.assertEqual(inspect.getsource(LocalTangentEngine.pass_once).strip(),expected.strip())

if __name__=='__main__':unittest.main()

class ConfigContracts(unittest.TestCase):
    def tearDown(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def test_exact_config_source_control_contract(self):
        from freeze_unit10 import make_config
        c,external=make_config();self.assertEqual(c['scene'],'scan65');self.assertEqual(c['kernel_count'],279616)
        self.assertEqual(c['level'],4);self.assertEqual(c['variant'],'local_tangent_equivalence');self.assertEqual(c['views'],['0012','0036'])
        self.assertEqual(c['tracked_predecessor_groups'],[56133,64877,167509]);self.assertEqual(c['changed_tracked_groups'],[61267,238627,64111])
        ref=json.loads((UNIT.parent/'unit_009/CONFIG.json').read_text())
        for k in ('numeric','previous_state','previous_checkpoint','previous_membership','p','baseline_membership','L1_membership','history_memberships'):self.assertEqual(c[k],ref[k])
        self.assertEqual(c['decision_sha256'],sha(UNIT/'DECISION.json'));self.assertEqual(c['source_files'],{str(p):sha(p) for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
        self.assertEqual(len(external),4);self.assertEqual(c['max_seconds'],1800);self.assertEqual(c['stage_elapsed_limits'],dict(input=120,M4=1380,final=1800))
        self.assertTrue(c['all_unknown_eligible']);self.assertFalse((UNIT/'scenes').exists());self.assertFalse((UNIT/'source_snapshot').exists())
        for k in ('control_state','control_membership','control_candidates','control_groups'):self.assertIn(c[k],c['input_files'])
    def test_cold_state_tampering_blocks_resume(self):
        e=fixture(cls=LocalTangentEngine)
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);complete_local_pass(e,out,'M4_STATE',False)
            with (out/'STATE.pkl').open('ab') as f:f.write(b'corrupt')
            with self.assertRaisesRegex(RuntimeError,'HASH_MISMATCH'):complete_local_pass(e,out,'M4_STATE',False)
    def test_changed_curved_competition_reaches_native_diagnostics(self):
        from runner import carrier_arrays
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);c=t9.m4_config(out);e=curved_duplicates(TransferEngine);e.level=3
            a=dict(e.a);a['covariance']=np.tile(np.eye(3)*1e-4,(54,1,1));a['opacity']=np.full(54,.7)
            baseline=np.repeat([0,18,36],18)
            for key,data in [('gaussians',a),('representatives',e.r),('controls',dict(control=e.t[:,None,:],control_index=np.arange(54),derivative_basis=np.ones((54,1)))),('baseline_membership',dict(edge_id=baseline,reason_code=np.zeros(54,np.uint8)))]:
                with open(c[key],'wb') as f:np.savez_compressed(f,**data)
            with open(c['previous_state'],'wb') as f:pickle.dump(state_of(e),f,protocol=5)
            with open(c['previous_membership'],'wb') as f:np.savez_compressed(f,edge_id=baseline,carrier_id=baseline,line_kernel_id=np.arange(54))
            Path(c['previous_carriers']).unlink();carrier_arrays(e,Path(c['previous_carriers']))
            cp=Path(c['previous_checkpoint']);v=json.loads(cp.read_text());v['files']['STATE.pkl']=sha(c['previous_state']);cp.write_text(json.dumps(v))
            c['kernel_count']=54
            for path in c['input_files']:c['input_files'][path]=sha(path)
            js(out/'CURVED_CONFIG.json',c);c['_config_sha256']=sha(out/'CURVED_CONFIG.json');c=small_config(out,c)
            local_runner.run(c)
            root=out/'variant/scenes/scan65';native=root/'stages/M4_MERGE_ONLY';ss=load_state(root/'states/M4/STATE.pkl')
            self.assertEqual(len(ss['events']),1)
            comparison=json.loads((native/'CONTROL_COMPARISON.json').read_text());self.assertTrue(comparison['changed_groups'])
            cases=json.loads((native/'diagnostics/CHANGED_EQ_SELECTION.json').read_text());self.assertGreater(cases['total_changed_choices'],0);self.assertTrue(cases['cases'])
            self.assertEqual(len(np.load(native/'MEMBERSHIP.npz')['edge_id']),54)
            for cam in ('0012','0036'):self.assertTrue((native/(cam+'_FULL.png')).exists())
