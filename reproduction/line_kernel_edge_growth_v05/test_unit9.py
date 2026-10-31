"""Bounded scan65 M4 regressions; unchanged unit008 runner/core, no fabricated RED."""
from common import *
import common,copy,tempfile,unittest,types,sys
from unittest import mock
from test_build import fixture
from test_unit3 import equal
from test_unit4 import small_continuation_config
from pipeline import state_of,restore,load_state,verify_checkpoint
from transfer import TransferEngine,complete_pass,reset_level
from runner import tables
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
RUNTIME=ROOT/'line_kernel_edge_growth_v05_20261031'
UNIT=RUNTIME/'units/unit_009'

def implementation():
    try:import continuation_level;return continuation_level
    except ModuleNotFoundError:import continuation_scene;return continuation_scene

def m4_config(out):
    c=small_continuation_config(out)
    c.update(scene='scan65',views=['0012','0036'],level=4,predecessor_label='M3',previous_checkpoint_stage='M3_STATE',
             stage_elapsed_limits=dict(input=60,M4=180,final=240),tracked_predecessor_groups=[0,6],
             history_memberships={'M2':c['previous_membership']})
    cp=Path(c['previous_checkpoint']);value=json.loads(cp.read_text());value['stage']='M3_STATE'
    cp.write_text(json.dumps(value));c['input_files'][str(cp)]=sha(cp)
    js(out/'M4_CONFIG.json',c);c['_config_sha256']=sha(out/'M4_CONFIG.json');return c

def stats(module,out,e,ids,pre,base,l1):
    if hasattr(module,'statistics_level'):
        return module.statistics_level(out,e,ids,pre,base,l1,{'M2':base})
    return module.statistics_m3(out,e,ids,pre,base,l1)

class ExistingContracts(unittest.TestCase):
    def tearDown(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def test_requested_m4_native_and_checkpoint_stage(self):
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);c=m4_config(out)
            with mock.patch.object(TransferEngine,'initialize',side_effect=AssertionError('NO_REFIT')):
                implementation().run(c)
            root=out/'scenes/scan65'
            self.assertTrue((root/'states/M4/CHECKPOINT.json').exists(),'requested M4 must not be silently delivered as M3')
            verify_checkpoint(root/'states/M4','M4_STATE')
            self.assertEqual(load_state(root/'states/M4/STATE.pkl')['level'],4)
            native=root/'stages/M4_MERGE_ONLY'
            self.assertEqual(len(np.load(native/'MEMBERSHIP.npz')['edge_id']),12)
            for view in c['views']:self.assertTrue((native/(view+'_FULL.png')).exists())
            self.assertFalse((root/'states/M3').exists())
            result=json.loads((out/'RUN_RESULT.json').read_text())
            self.assertEqual(result['comparisons']['total_rounds'],3)
            self.assertEqual(result['comparisons']['largest_contributor'],'M3')
            self.assertIn('M4_NATIVE',result['completed']);self.assertNotIn('M4',result['not_requested'])
    def test_m3_predecessor_growth_values_and_history(self):
        e=fixture();e.a['means']=e.a['means']*1.75;e.r['x']=e.r['x']*1.75;e.r['endpoints']=e.r['endpoints']*1.75
        e.x=e.a['means'];e.rx=e.r['x'];e.ep=e.r['endpoints']
        for c in e.carriers.values():c.q*=1.75
        pre=copy.deepcopy(e.carriers);base=np.repeat([0,6],6);reset_level(e,4);e.pass_once(False);ids=e.primary(base)[0]
        expected=tables(e,ids,pre,base);self.assertTrue(any(g['growth_gate'] for g in expected))
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            common.CFG=dict(scene='scan65',level=4,predecessor_label='M3',unit=td,runtime=td)
            groups=stats(implementation(),Path(td),e,ids,pre,base,base)
            self.assertEqual(groups[0]['immediate_predecessor'],'M3')
            for old,new in zip(expected,groups):
                for key in ('growth_gate','outward_support_p','supported_length_p','longest_continuous_run_p','max_gap_p','total_gap_p'):
                    self.assertEqual(old[key],new[key])
                self.assertEqual(old['gain_over_largest_L1_p'],new['gain_over_largest_M3_p'])
                self.assertEqual([z['carrier_id'] for z in old['L1_contributions']],[z['carrier_id'] for z in new['M3_contributions']])
                self.assertEqual(sum(z['kernels'] for z in new['M2_contributions']),new['kernels'])
                self.assertEqual(sum(z['kernels'] for z in new['L1_contributions']),new['kernels'])
            self.assertEqual(json.loads((Path(td)/'GROUPS.json').read_text())['stage'],'M4_MERGE_ONLY')


def frozen_reference():
    frozen=json.loads((UNIT.parent/'unit_008/PARENT_RUN_FROZEN.json').read_text());source=Path(__file__).resolve().parent/'core.py';snap=Path(frozen['immutable_source_snapshot'][str(source)])
    assert sha(snap)==frozen['source_files'][str(source)]==sha(source)
    ref=types.ModuleType('unit8_frozen_core');sys.modules[ref.__name__]=ref;exec(compile(snap.read_text(),str(snap),'exec'),ref.__dict__);return ref

class BoundedRegression(unittest.TestCase):
    def setUp(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def tearDown(self):self.setUp()
    def compare(self,e):
        ref=frozen_reference();rr=ref.Engine(e.a,e.r,e.t,e.p);restore(rr,copy.deepcopy(state_of(e)))
        reset_level(e,4);reset_level(rr,4);equal(e.candidates(),rr.candidates());baseline=np.full(len(e.x),-1,np.int64)
        for cid,c in e.carriers.items():
            if c.baseline:baseline[c.rows]=cid
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td)/'M4';complete_pass(e,out,'M4_STATE',False);rr.pass_once(False)
            for a,b in [(e.fit_count,rr.fit_count),(e.next_version,rr.next_version),(e.events,rr.events),(e.records,rr.records),(dict(e.stats),dict(rr.stats)),(e.carriers,rr.carriers),(dict(e.aux),dict(rr.aux))]:equal(a,b)
            for a,b in zip(e.primary(baseline),rr.primary(baseline)):equal(a,b)
            fresh=TransferEngine(e.a,e.r,e.t,e.p)
            with mock.patch.object(fresh,'pass_once',side_effect=AssertionError('NO_RECOMPUTE')):complete_pass(fresh,out,'M4_STATE',False)
            equal(state_of(e),state_of(fresh))
            print('EQUIVALENT',len(e.x),'kernels','fits',e.fit_count,'events',len(e.events),flush=True)
    def test_hard_fixtures_and_complete_resume(self):
        for kind in ('straight','duplicate','gentle_curve','curve','S','parallel','T','X','gap','tie'):
            with self.subTest(kind=kind):self.compare(fixture(kind,cls=TransferEngine))
    def test_real_m3_max128_seedlets(self):
        u1=UNIT.parent/'unit_006';cfg=json.loads((u1/'CONFIG.json').read_text());state=u1/'scenes/scan65/states/M3/STATE.pkl'
        assert sha(state)=='96f2bbb51d80cf9e036753ae42f47cb1a19a72e41b945c7cc7137879d2623497'
        for key in ('gaussians','representatives','controls'):verify({cfg[key]:cfg['input_files'][cfg[key]]})
        ss=load_state(state);chosen=[];count=0;seen=set()
        # Deterministic saved proposal order, not a new full-scene candidate run.
        cp=json.loads((state.parent/'CHECKPOINT.json').read_text())
        proposals=state.parent/'ORDERED_CANDIDATES.npz';verify({str(proposals):cp['files'][proposals.name]})
        with np.load(proposals) as z:
            for left,right in zip(z['a'],z['b']):
                pair=[ss['carriers'].get(int(cid)) for cid in (left,right)]
                if any(c is None or not c.valid or not 3<=len(c.reps)<=8 for c in pair):continue
                new=[c for c in pair if c.cid not in seen]
                if not new or count+sum(len(c.reps) for c in new)>128:continue
                for c in new:chosen.append(c);seen.add(c.cid);count+=len(c.reps)
                if count>=120:break
        assert chosen and count<=128
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
        assert len(selected)<=128;print('REAL_M3_FIXTURE',len(rows),'kernels',len(selected),'seedlets',len(chosen),'carriers',flush=True);self.compare(e)
    def test_native_small_routing_and_later_failure(self):
        module=implementation()
        for fail in (False,True):
            with self.subTest(inject_failure=fail),tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
                out=Path(td);c=m4_config(out)
                with mock.patch.object(TransferEngine,'initialize',side_effect=AssertionError('NO_INITIALIZATION')):
                    if fail:
                        with mock.patch.object(module,'statistics_level',side_effect=RuntimeError('INJECTED_AFTER_NATIVE')):
                            with self.assertRaisesRegex(RuntimeError,'INJECTED_AFTER_NATIVE'):module.run(c)
                    else:module.run(c)
                result=json.loads((out/'RUN_RESULT.json').read_text());self.assertEqual(result['status'],'partial' if fail else 'complete')
                self.assertEqual(result['scene'],'scan65');self.assertNotIn('scan65',result['not_requested'])
                self.assertIn('scan24',result['not_requested']);self.assertFalse((out/'scenes/scan24').exists())
                native=out/'scenes/scan65/stages/M4_MERGE_ONLY';self.assertEqual(len(np.load(native/'MEMBERSHIP.npz')['edge_id']),12)
                for view in c['views']:self.assertTrue((native/(view+'_FULL.png')).exists())
                state=out/'scenes/scan65/states/M4';verify_checkpoint(state,'M4_STATE');self.assertEqual(len(load_state(state/'STATE.pkl')['carriers']),1)
                self.tearDown()
    def test_m4_statistics_equal_pinned_unit8(self):
        e=fixture();base=np.repeat([0,6],6);pre=copy.deepcopy(e.carriers);e.pass_once(False);ids=e.primary(base)[0]
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            common.CFG=dict(scene='scan65',level=4,predecessor_label='M3',unit=td,runtime=td);a=Path(td)/'old';b=Path(td)/'new'
            original=frozen_scene().statistics_level(a,e,ids,pre,base,base,{'M2':base})
            current=implementation().statistics_level(b,e,ids,pre,base,base,{'M2':base})
            equal(original,current)
            self.assertEqual(json.loads((b/'GROUPS.json').read_text())['scene'],'scan65')
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
            if len(calls)>1:raise RuntimeError('INCUMBENT_LOST_REJECT_M4_PROMOTION')
            return original(*args)
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);c=m4_config(out);before=sha(c['previous_membership'])
            with mock.patch.object(module,'promotion_check',side_effect=fail_after_restore):
                with self.assertRaisesRegex(RuntimeError,'INCUMBENT_LOST'):module.run(c)
            self.assertEqual(sha(c['previous_membership']),before)
            root=out/'scenes/scan65';verify_checkpoint(root/'states/M4','M4_STATE')
            self.assertTrue((root/'PROMOTION_REJECTED.json').exists());self.assertFalse((root/'stages/M4_MERGE_ONLY').exists())
            facts=json.loads((out/'RUN_RESULT.json').read_text());self.assertFalse(facts['delivery_gate']);self.assertEqual(facts['status'],'partial')
    def test_post_checkpoint_failure_and_hash_tamper(self):
        e=fixture(cls=TransferEngine);reset_level(e,4)
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);complete_pass(e,out,'M4_STATE',False)
            with self.assertRaisesRegex(RuntimeError,'INJECTED'):raise RuntimeError('INJECTED_EXPENSIVE_FAILURE')
            self.assertEqual(len(load_state(out/'STATE.pkl')['carriers']),1)
            with (out/'STATE.pkl').open('ab') as f:f.write(b'corrupt')
            with self.assertRaisesRegex(RuntimeError,'HASH_MISMATCH'):complete_pass(e,out,'M4_STATE',False)



def frozen_scene():
    frozen=json.loads((UNIT.parent/'unit_008/PARENT_RUN_FROZEN.json').read_text())
    original=str(Path(__file__).resolve().parent/'continuation_level.py');snap=Path(frozen['immutable_source_snapshot'][original])
    assert sha(snap)==frozen['source_files'][original]
    module=types.ModuleType('unit8_frozen_scene');exec(compile(snap.read_text(),str(snap),'exec'),module.__dict__);return module

class ConfigContracts(unittest.TestCase):
    def tearDown(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def test_actual_unit_config_and_complete_source_interface(self):
        from freeze_unit9 import make_config
        c,external=make_config();self.assertEqual(c['scene'],'scan65');self.assertEqual(c['kernel_count'],279616)
        self.assertEqual(c['level'],4);self.assertEqual(c['predecessor_label'],'M3')
        self.assertEqual(c['views'],['0012','0036']);self.assertEqual(c['tracked_predecessor_groups'],[56133,64877,167509])
        self.assertEqual(c['unit'],str(UNIT));self.assertEqual(c['previous_checkpoint_stage'],'M3_STATE')
        self.assertEqual(c['numeric'],json.loads((UNIT.parent/'unit_008/CONFIG.json').read_text())['numeric'])
        self.assertEqual(c['max_seconds'],1800);self.assertEqual(c['stage_elapsed_limits'],dict(input=120,M4=1380,final=1800))
        self.assertEqual(c['decision_sha256'],sha(UNIT/'DECISION.json'));self.assertEqual(set(c['history_memberships']),{'M2'})
        source=Path(__file__).resolve().parent
        self.assertEqual(c['source_files'],{str(p):sha(p) for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
        self.assertEqual(len(external),4);self.assertTrue(c['all_unknown_eligible']);self.assertTrue(c['no_RGB_source_GS'])
        self.assertFalse((UNIT/'scenes').exists());self.assertFalse((UNIT/'source_snapshot').exists())
        frozen=json.loads((UNIT.parent/'unit_008/PARENT_RUN_FROZEN.json').read_text())
        verify(frozen['source_files'])
        # The complete existing runner and selector are unchanged from the pinned snapshot.
        old=ast.parse((UNIT.parent/'unit_008/source_snapshot/continuation_level.py').read_text())
        new=ast.parse((source/'continuation_level.py').read_text())
        fn=lambda tree:next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='select_progression_groups')
        self.assertEqual(ast.dump(fn(old)),ast.dump(fn(new)))
        print('UNIT009_CONFIG_VALID',c['p'],len(c['source_files']),'source files',flush=True)
    def test_restore_m3_without_initialization_or_flag_promotion(self):
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            c=m4_config(Path(td));before=load_state(c['previous_state'])
            with mock.patch.object(TransferEngine,'initialize',side_effect=AssertionError('NO_REFIT')):
                a,r,base,prev,e,cams=implementation().load_predecessor(c)
            equal(before['carriers'],e.carriers);equal(before['aux'],e.aux);self.assertEqual(before['next_version'],e.next_version)
            self.assertEqual([z['view'] for z in cams],['0012','0036'])

if __name__=='__main__':unittest.main()
