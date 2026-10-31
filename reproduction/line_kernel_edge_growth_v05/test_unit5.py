"""Bounded unit005 tests; original RED is recorded before scene continuation."""
from common import *
import common,copy,tempfile,unittest,types,sys
from unittest import mock
from test_build import fixture
from test_unit3 import equal
from test_unit4 import small_continuation_config
from pipeline import state_of,restore,load_state,verify_checkpoint
from transfer import TransferEngine,complete_pass,reset_level
from transfer_behavior import select_groups
import continuation_runner
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');RUNTIME=ROOT/'line_kernel_edge_growth_v05_20261031';UNIT=RUNTIME/'units/unit_005'

def implementation():
    try:import continuation_scene;return continuation_scene
    except ModuleNotFoundError:return continuation_runner

def ficus_config(out):
    c=small_continuation_config(out);c['scene']='ficus';c['views']=['test_r_1','test_r_79'];c['previous_checkpoint_stage']='M2_STATE'
    cp=Path(c['previous_checkpoint']);value=json.loads(cp.read_text());value['stage']='M2_STATE';cp.write_text(json.dumps(value));c['input_files'][str(cp)]=sha(cp)
    js(out/'FICUS_CONFIG.json',c);c['_config_sha256']=sha(out/'FICUS_CONFIG.json');return c

class NewContracts(unittest.TestCase):
    def tearDown(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def test_configured_predecessor_stage_loads_without_refit(self):
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            c=ficus_config(Path(td))
            with mock.patch.object(TransferEngine,'initialize',side_effect=AssertionError('NO_REFIT')):
                a,r,base,prev,e,cams=implementation().load_predecessor(c)
            self.assertEqual([z['view'] for z in cams],c['views']);self.assertEqual(e.next_version,23)
            self.assertEqual(e.carriers[0].version,11);self.assertEqual(len(a['means']),12)
    def test_statistics_uses_actual_scene(self):
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            common.CFG=dict(scene='ficus',unit=td,runtime=td);e=fixture();base=np.repeat([0,6],6)
            implementation().statistics_m3(Path(td),e,base,e.carriers,base,base)
            self.assertEqual(json.loads((Path(td)/'GROUPS.json').read_text())['scene'],'ficus')
    def test_real_three_fragment_growth_is_selected(self):
        u4=UNIT.parent/'unit_004';path=u4/'scenes/scan24/stages/M3_MERGE_ONLY/GROUPS.json';seal=json.loads((u4/'SEAL.json').read_text())
        assert sha(path)==seal['files'][str(path.relative_to(u4))]
        groups=json.loads(path.read_text())['groups'];module=implementation()
        selector=getattr(module,'select_progression_groups',select_groups)
        self.assertIn(69519,[g['edge_id'] for g in selector(groups)])

def frozen_reference():
    frozen=json.loads((UNIT.parent/'unit_004/PARENT_RUN_FROZEN.json').read_text());source=Path(__file__).resolve().parent/'core.py';snap=Path(frozen['immutable_source_snapshot'][str(source)])
    assert sha(snap)==frozen['source_files'][str(source)]==sha(source)
    ref=types.ModuleType('unit4_frozen_core');sys.modules[ref.__name__]=ref;exec(compile(snap.read_text(),str(snap),'exec'),ref.__dict__);return ref

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
        u1=UNIT.parent/'unit_002';cfg=json.loads((u1/'CONFIG.json').read_text());state=u1/'scenes/ficus/states/M2/STATE.pkl'
        assert sha(state)=='053f61f503abdb41c39297da4d8551ab43b9ef8dd0dc91ef30cd2378c5714a33'
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
        module=implementation()
        for fail in (False,True):
            with self.subTest(inject_failure=fail),tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
                out=Path(td);c=ficus_config(out)
                with mock.patch.object(TransferEngine,'initialize',side_effect=AssertionError('NO_INITIALIZATION')):
                    if fail:
                        with mock.patch.object(module,'statistics_m3',side_effect=RuntimeError('INJECTED_AFTER_NATIVE')):
                            with self.assertRaisesRegex(RuntimeError,'INJECTED_AFTER_NATIVE'):module.run(c)
                    else:module.run(c)
                result=json.loads((out/'RUN_RESULT.json').read_text());self.assertEqual(result['status'],'partial' if fail else 'complete')
                self.assertEqual(result['scene'],'ficus');self.assertNotIn('ficus',result['not_requested'])
                self.assertIn('scan24',result['not_requested']);self.assertFalse((out/'scenes/scan24').exists())
                native=out/'scenes/ficus/stages/M3_MERGE_ONLY';self.assertEqual(len(np.load(native/'MEMBERSHIP.npz')['edge_id']),12)
                for view in c['views']:self.assertTrue((native/(view+'_FULL.png')).exists())
                state=out/'scenes/ficus/states/M3';verify_checkpoint(state,'M3_STATE');self.assertEqual(len(load_state(state/'STATE.pkl')['carriers']),1)
                self.tearDown()
    def test_statistics_values_equal_pinned_unit4(self):
        e=fixture();base=np.repeat([0,6],6);pre=copy.deepcopy(e.carriers);e.pass_once(False);ids=e.primary(base)[0]
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            common.CFG=dict(scene='ficus',unit=td,runtime=td);a=Path(td)/'old';b=Path(td)/'new'
            original=continuation_runner.statistics_m3(a,e,ids,pre,base,base)
            current=implementation().statistics_m3(b,e,ids,pre,base,base)
            equal(original,current)
            self.assertEqual(json.loads((b/'GROUPS.json').read_text())['scene'],'ficus')
            equal(json.loads((a/'METRICS.json').read_text()),json.loads((b/'METRICS.json').read_text()))
    def test_incumbent_boundary_rejects_promotion_preserves_state(self):
        module=implementation();e=fixture(cls=TransferEngine)
        for c in e.carriers.values():c.baseline=False
        baseline=np.full(12,-1,np.int64);previous=np.repeat([0,6],6)
        before=copy.deepcopy(state_of(e))
        with self.assertRaisesRegex(RuntimeError,'INCUMBENT_LOST'):module.promotion_check(e,baseline,previous,e.r)
        equal(before,state_of(e))
    def test_runner_preserves_complete_state_on_rejected_promotion(self):
        module=implementation();original=module.promotion_check;calls=[]
        def fail_after_restore(*args):
            calls.append(True)
            if len(calls)>1:raise RuntimeError('INCUMBENT_LOST_REJECT_M3_PROMOTION')
            return original(*args)
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);c=ficus_config(out);before=sha(c['previous_membership'])
            with mock.patch.object(module,'promotion_check',side_effect=fail_after_restore):
                with self.assertRaisesRegex(RuntimeError,'INCUMBENT_LOST'):module.run(c)
            self.assertEqual(sha(c['previous_membership']),before)
            root=out/'scenes/ficus';verify_checkpoint(root/'states/M3','M3_STATE')
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
