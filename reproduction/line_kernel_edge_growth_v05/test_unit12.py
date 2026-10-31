"""Bounded prefix equivalence, endpoint controls, durable native delivery."""
from common import *
import common,copy,tempfile,unittest,types,sys,inspect
from unittest import mock
from test_build import fixture
from test_endpoint_contract import dense
from test_unit3 import equal
import test_unit7 as t7
from pipeline import state_of,restore,load_state,verify_checkpoint
from transfer import TransferEngine,reset_level
from budget_engine import BudgetEngine
from endpoint_engine import EndpointEngine,replay_prefix,endpoint_supplement,endpoint_screen,canonical_scores,complete_endpoint_pass
import endpoint_runner,continuation_level

UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_012')
SOURCE=Path(__file__).resolve().parent

def reference():
    f=json.loads((UNIT.parent/'unit_011/PARENT_RUN_FROZEN.json').read_text());original=str(SOURCE/'budget_engine.py');p=Path(f['immutable_source_snapshot'][original]);assert sha(p)==f['source_files'][original]
    m=types.ModuleType('unit11_frozen_budget');sys.modules[m.__name__]=m;exec(compile(p.read_text(),str(p),'exec'),m.__dict__);return m

def native_config(out):
    from runner import carrier_arrays
    c=t7.m4_config(out);e=dense();e.level=3;n=len(e.x);a=dict(e.a)
    a['covariance']=np.tile(np.eye(3)*1e-4,(n,1,1));a['opacity']=np.full(n,.7);base=np.repeat(np.arange(0,n,6),6)
    for key,data in [('gaussians',a),('representatives',e.r),('controls',dict(control=e.t[:,None,:],control_index=np.arange(n),derivative_basis=np.ones((n,1)))),('baseline_membership',dict(edge_id=base,reason_code=np.zeros(n,np.uint8)))]:
        with open(c[key],'wb') as f:np.savez_compressed(f,**data)
    with open(c['previous_state'],'wb') as f:pickle.dump(state_of(e),f,protocol=5)
    with open(c['previous_membership'],'wb') as f:np.savez_compressed(f,edge_id=base,carrier_id=base,line_kernel_id=np.arange(n))
    Path(c['previous_carriers']).unlink();carrier_arrays(e,Path(c['previous_carriers']))
    cp=Path(c['previous_checkpoint']);v=json.loads(cp.read_text());v['files']['STATE.pkl']=sha(c['previous_state']);cp.write_text(json.dumps(v))
    c.update(kernel_count=n,numeric=dict(fit_cap_per_level=40000),control_fit_limit=40000,unit=str(out/'control'),runtime=str(out),stage_elapsed_limits=dict(input=120,M4=180,final=240))
    for p in c['input_files']:c['input_files'][p]=sha(p)
    js(out/'CONTROL_CONFIG.json',c);c['_config_sha256']=sha(out/'CONTROL_CONFIG.json')
    with mock.patch.object(continuation_level,'TransferEngine',BudgetEngine):continuation_level.run(c)
    common.CFG=None;common.END=None;common.START=None
    state=out/'control/scenes/scan24/states/M4';native=out/'control/scenes/scan24/stages/M4_MERGE_ONLY'
    c.update(unit=str(out/'variant'),control_state=str(state/'STATE.pkl'),control_candidates=str(state/'ORDERED_CANDIDATES.npz'),control_membership=str(native/'MEMBERSHIP.npz'),control_groups=str(native/'GROUPS.json'),changed_tracked_groups=[])
    for p in list(state.iterdir())+list(native.iterdir()):
        if p.is_file():c['input_files'][str(p)]=sha(p)
    js(out/'VARIANT_CONFIG.json',c);c['_config_sha256']=sha(out/'VARIANT_CONFIG.json');return c

class Contracts(unittest.TestCase):
    def setUp(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def tearDown(self):self.setUp()
    def compare(self,base):
        old=reference().BudgetEngine(base.a,base.r,base.t,base.p);new=EndpointEngine(base.a,base.r,base.t,base.p)
        for e in (old,new):restore(e,copy.deepcopy(state_of(base)));reset_level(e,4);e.fit_limit=40000;e.control_fit_limit=40000
        prefix=old.candidates();actual=new.candidates();equal(prefix,new.prefix_candidates);equal(actual[:len(prefix)],prefix)
        pairs=np.asarray(sorted((i,j) for _,i,j in prefix),np.int64).reshape(-1,2)
        equal(canonical_scores(new,pairs),prefix)
        reset_level(old,4);reset_level(new,4);captured={}
        def capture(name,e,data):
            if name=='competition_complete':captured.update(valid=copy.deepcopy(data['valid']),records=copy.deepcopy(e.records),fits=e.fit_count)
        old.observer=capture;old.pass_once(False)
        def inspect_prefix(name,e,data):
            if name=='prefix_complete':
                equal(sorted(e.prefix_valid,key=lambda z:(z[0],z[1],z[2])),captured['valid']);equal(e.prefix_records,captured['records']);self.assertEqual(e.prefix_fit_count,captured['fits'])
                shadow=replay_prefix(e)
                for key in ('events','carriers','aux','fit_count','next_version','records','stats'):equal(getattr(shadow,key),getattr(old,key))
                baseline=np.full(len(e.x),-1,np.int64)
                for cid,cc in base.carriers.items():
                    if cc.baseline:baseline[cc.rows]=cid
                equal(shadow.primary(baseline),old.primary(baseline))
        new.observer=inspect_prefix;new.pass_once(False)
        print('PREFIX_SHARED_FITS_EXACT',len(base.x),'kernels',old.fit_count,'prefix fits',len(new.supplement_candidates),'supplement',flush=True)
    def test_hard_and_dense_prefix_equivalence(self):
        for kind in ('straight','duplicate','gentle_curve','curve','S','parallel','T','X','gap','tie'):
            with self.subTest(kind=kind):self.compare(fixture(kind,cls=TransferEngine))
        self.compare(dense())
    def test_real_m3_max128_seedlets(self):
        with mock.patch.object(t7,'UNIT',UNIT):t7.BoundedRegression.test_real_m3_max128_seedlets(self)
    def test_endpoint_hard_controls_reversal_and_caps(self):
        for kind in ('straight','gentle_curve','curve','S','duplicate','parallel','T','X','gap','tie'):
            base=fixture(kind,cls=EndpointEngine)
            for reverse in (False,True):
                e=copy.deepcopy(base)
                if reverse:
                    for cc in e.carriers.values():cc.q=cc.q[::-1].copy()
                suffix,ports,stats,rr=endpoint_supplement(e,[])
                for _,i,j in suffix:
                    q,op,_,_=e.proposal(e.carriers[i],e.carriers[j],False);self.assertEqual(op,'endpoint');self.assertIsNotNone(q)
                if kind in ('parallel','T','X','gap','duplicate'):self.assertEqual(suffix,[])
                if kind=='straight':self.assertEqual(len(suffix),1)
        e=dense(EndpointEngine);prefix=BudgetEngine.candidates(e);a=endpoint_supplement(e,prefix)
        e.carriers=dict(reversed(list(e.carriers.items())));b=endpoint_supplement(e,prefix);equal(a,b)
        slot=[(cid,side) for _,i,j in a[0] for cid,side in zip((i,j),a[1][i,j])];self.assertEqual(len(slot),len(set(slot)))
        self.assertEqual(endpoint_supplement(e,prefix,screen_cap=0)[0],[]);self.assertGreater(endpoint_supplement(e,prefix,screen_cap=0)[2]['screen_cap'],0)
        self.assertEqual(endpoint_supplement(e,prefix,append_cap=0)[0],[]);self.assertGreater(endpoint_supplement(e,prefix,append_cap=0)[2]['append_cap'],0)
        e.carriers[0].baseline=False;self.assertIn((0,6),[(i,j) for _,i,j in endpoint_supplement(e,prefix)[0]])
        e.carriers[0].valid=False;self.assertFalse(any(0 in (i,j) for _,i,j in endpoint_supplement(e,prefix)[0]))
    def test_shared_cap_and_single_merge_per_carrier(self):
        e=dense(EndpointEngine);e.fit_limit=1;e.pass_once(False);self.assertEqual(e.fit_count,1);self.assertGreater(e.stats['fit_cap'],0)
        used=[cid for ev in e.events for cid,_ in ev['inputs']];self.assertEqual(len(used),len(set(used)))
    def test_unchanged_fit_and_competition_implementation(self):
        self.assertIs(EndpointEngine.fit,BudgetEngine.fit)
        ref=reference();self.assertEqual(inspect.getsource(BudgetEngine._commit_precomputed),inspect.getsource(ref.BudgetEngine._commit_precomputed))
        self.assertNotIn('local_equivalent',inspect.getsource(EndpointEngine))
    def test_actual_config_contract(self):
        from freeze_unit12 import make_config
        c,h=make_config();ref=json.loads((UNIT.parent/'unit_011/CONFIG.json').read_text())
        for key in ('numeric','p','previous_state','previous_checkpoint','previous_membership','baseline_membership','L1_membership','history_memberships'):equal(c[key],ref[key])
        self.assertEqual(c['decision_sha256'],sha(UNIT/'DECISION.json'));self.assertEqual(c['control_fit_limit'],40000);self.assertEqual(c['kernel_count'],458490);self.assertEqual(len(h),4);self.assertEqual(c['max_seconds'],1800)
        self.assertFalse((UNIT/'source_snapshot').exists());self.assertFalse((UNIT/'scenes').exists())
    def test_native_delivery_resume_later_failure(self):
        for fail in (False,True):
            with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
                out=Path(td);c=native_config(out)
                with mock.patch.object(EndpointEngine,'initialize',side_effect=AssertionError('NO_REFIT')):
                    if fail:
                        with mock.patch.object(endpoint_runner,'statistics_level',side_effect=RuntimeError('INJECTED_AFTER_NATIVE')):
                            with self.assertRaisesRegex(RuntimeError,'INJECTED_AFTER_NATIVE'):endpoint_runner.run(c)
                    else:endpoint_runner.run(c)
                root=out/'variant/scenes/scan24';state=root/'states/M4';native=root/'stages/M4_MERGE_ONLY';verify_checkpoint(state,'M4_STATE')
                self.assertEqual(len(np.load(native/'MEMBERSHIP.npz')['edge_id']),120)
                for cam in ('0012','0036'):self.assertTrue((native/(cam+'_FULL.png')).is_file())
                shadow=json.loads((state/'SHADOW_CONTROL.json').read_text());self.assertEqual(shadow['status'],'VERIFIED');self.assertTrue(shadow['exact_stats']);self.assertEqual(shadow['refit_calls'],0)
                self.assertGreater(json.loads((state/'SUPPLEMENT_STATS.json').read_text())['appended'],0)
                self.assertEqual(len(load_state(state/'STATE.pkl')['events']),9)
                self.assertEqual(len(load_state(c['control_state'])['events']),8)
                result=json.loads((out/'variant/RUN_RESULT.json').read_text());self.assertEqual(result['status'],'partial' if fail else 'complete')
                if not fail:
                    selected=json.loads((native/'diagnostics/SUPPLEMENT_ACCEPTED_SELECTION.json').read_text())
                    self.assertEqual(selected['accepted_supplemental'],1)
                    self.assertEqual([p[0] for p in selected['selected_events'][0]['inputs']],[0,6])
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
            root=out/'variant/scenes/scan24';self.assertTrue((root/'states/M4/UNPROMOTED_STATE.pkl').exists());self.assertFalse((root/'stages/M4_MERGE_ONLY').exists())
        self.tearDown();e=fixture(cls=EndpointEngine)
        for cc in e.carriers.values():cc.baseline=False
        before=copy.deepcopy(state_of(e))
        with self.assertRaisesRegex(RuntimeError,'INCUMBENT_LOST'):endpoint_runner.promotion_check(e,np.full(12,-1),np.repeat([0,6],6),e.r)
        equal(before,state_of(e))

if __name__=='__main__':unittest.main()
