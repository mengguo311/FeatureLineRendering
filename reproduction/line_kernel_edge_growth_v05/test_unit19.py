"""M5-only interface and bounded saved-M4 regressions; no full science."""
from common import *
import common,copy,tempfile,unittest,types,sys
from unittest import mock
from test_build import fixture
from test_endpoint_contract import dense
from test_unit3 import equal
import test_unit7 as t7
import test_unit12 as t12
from pipeline import state_of,restore,load_state,verify_checkpoint
from transfer import TransferEngine,reset_level
from protected_engine import ProtectedEngine
from progressive_engine import complete_pass,load_control,control_dir
import progressive_runner as impl
from runner import tables
UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_019')
SOURCE=Path(__file__).resolve().parent

def native_config(out):
    with mock.patch.object(t12,'UNIT',UNIT):c=t12.native_config(out)
    root=out/'control/scenes/scan24';state=root/'states/M4';native=root/'stages/M4_MERGE_ONLY'
    history={'M2':c['previous_membership'],'M3':c['previous_membership']}
    for key in list(c):
        if key.startswith(('control_','joint_')):c.pop(key)
    dispute=out/'PREVIOUS_PROTECTION.json';js(dispute,dict(disputed_outputs=[0]))
    c.update(unit=str(out/'progressive'),level=5,predecessor_label='M4',previous_state=str(state/'STATE.pkl'),previous_checkpoint=str(state/'CHECKPOINT.json'),previous_checkpoint_stage='M4_STATE',predecessor_config=str(out/'CONTROL_CONFIG.json'),predecessor_config_sha256=sha(out/'CONTROL_CONFIG.json'),previous_membership=str(native/'MEMBERSHIP.npz'),previous_carriers=str(native/'CARRIERS.npz'),previous_groups=str(native/'GROUPS.json'),previous_lineage=str(native/'LINEAGE.json'),previous_protection=str(dispute),history_memberships=history,internal_controls=True,control_fit_limit=40000,fit_caps_by_round=[30000,30000,40000,40000],stage_elapsed_limits=dict(input=120,M5=180,final=240),tracked_predecessor_groups=[0,6])
    for p in list(state.iterdir())+list(native.iterdir())+[dispute,out/'CONTROL_CONFIG.json']:
        if p.is_file():c['input_files'][str(p)]=sha(p)
    cams_path=out/'FICUS_FIXTURE_CAMERAS.json';cams=json.loads(Path(c['cameras']).read_text());views=['test_r_1','test_r_79'];cams['ficus']=[dict(cam,view=view) for cam,view in zip(cams['scan24'],views)];js(cams_path,cams);c.update(scene='ficus',views=views,cameras=str(cams_path));c['input_files'][str(cams_path)]=sha(cams_path)
    js(out/'M5_CONFIG.json',c);c['_config_sha256']=sha(out/'M5_CONFIG.json');return c

class Contracts(unittest.TestCase):
    def setUp(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def tearDown(self):self.setUp()
    def compare(self,base):
        f=json.loads((UNIT.parent/'unit_018/PARENT_RUN_FROZEN.json').read_text());original=str(SOURCE/'protected_engine.py');snap=Path(f['immutable_source_snapshot'][original]);assert sha(snap)==f['source_files'][original]==sha(original)
        m=types.ModuleType('unit18_pinned_protected');sys.modules[m.__name__]=m;exec(compile(snap.read_text(),str(snap),'exec'),m.__dict__)
        engines=[m.ProtectedEngine(base.a,base.r,base.t,base.p),ProtectedEngine(base.a,base.r,base.t,base.p)]
        for e in engines:restore(e,copy.deepcopy(state_of(base)));reset_level(e,5);e.fit_limit=40000;e.control_fit_limit=40000
        old,new=engines;equal(old.candidates(),new.candidates());old.pass_once(False);new.pass_once(False)
        equal(state_of(old),state_of(new))
        for name in ('prefix_candidates','supplement_candidates','prefix_valid','prefix_records','prefix_fit_count','joint_ambiguous_pairs','protection_conflicts','disputed_output_ids','protected_input_ids','protected_output_ids'):equal(getattr(old,name),getattr(new,name))
        for name in ('prefix_shadow','joint_shadow'):equal(state_of(getattr(old,name)),state_of(getattr(new,name)))
        used=[cid for ev in new.events for cid,_ in ev['inputs']];self.assertEqual(len(used),len(set(used)))
        print('PINNED_LEVEL5_EXACT',len(base.x),'kernels',new.fit_count,'fits',flush=True)
    def test_hard_and_dense(self):
        for kind in ('straight','duplicate','gentle_curve','curve','S','parallel','T','X','gap','tie'):
            with self.subTest(kind=kind):self.compare(fixture(kind,cls=TransferEngine))
        self.compare(dense())
    def test_actual_config(self):
        from freeze_unit19 import make_config
        c,h=make_config();old=json.loads((UNIT.parent/'unit_016/CONFIG.json').read_text())
        for key in ('numeric','endpoint_supplement','p','gaussians','controls','representatives','views'):equal(c[key],old[key])
        self.assertEqual(c['decision_sha256'],sha(UNIT/'DECISION.json'));self.assertEqual(len(h),4)
        self.assertEqual(c['scene'],'ficus');self.assertEqual(c['views'],['test_r_1','test_r_79']);self.assertEqual(c['kernel_count'],285956);self.assertEqual(impl.level_contract(c),(5,'M5','M4'))
        self.assertEqual(set(c['history_memberships']),{'M2','M3'})
        self.assertFalse(any(k in c for k in ('control_state','joint_state','control_candidates','joint_candidates')))
        self.assertEqual(c['stage_elapsed_limits'],dict(input=120,M5=1380,final=1800))
        self.assertFalse((UNIT/'scenes').exists());self.assertFalse((UNIT/'source_snapshot').exists())
    def test_native_resume_and_later_failure(self):
        for fail in (False,True):
            with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
                out=Path(td);c=native_config(out)
                with mock.patch.object(ProtectedEngine,'initialize',side_effect=AssertionError('NO_REFIT')):
                    if fail:
                        with mock.patch.object(impl,'statistics_level',side_effect=RuntimeError('INJECTED_AFTER_NATIVE')):
                            with self.assertRaisesRegex(RuntimeError,'INJECTED_AFTER_NATIVE'):impl.run(c)
                    else:impl.run(c)
                root=out/'progressive/scenes/ficus';state=root/'states/M5';native=root/'stages/M5_MERGE_ONLY'
                verify_checkpoint(state,'M5_STATE');self.assertEqual(len(np.load(native/'MEMBERSHIP.npz')['edge_id']),120)
                for view in ('test_r_1','test_r_79'):self.assertTrue((native/(view+'_FULL.png')).exists())
                for kind in ('prefix','joint'):
                    p=control_dir(c,kind);verify_checkpoint(p,'M5_'+kind.upper()+'_SHARED_CONTROL')
                    self.assertEqual(json.loads((p/'CONTROL_PROVENANCE.json').read_text())['status'],'INTERNAL_SHARED_FIT_CONTROL')
                    self.assertEqual(json.loads((state/('SHADOW_CONTROL.json' if kind=='prefix' else 'SHADOW_JOINT.json')).read_text())['historical_replay'],False)
                result=json.loads((out/'progressive/RUN_RESULT.json').read_text());self.assertEqual(result['status'],'partial' if fail else 'complete')
                if not fail:
                    self.assertEqual(result['comparisons']['total_rounds'],4);self.assertEqual(result['comparisons']['largest_contributor'],'M4')
                    gg=json.loads((native/'GROUPS.json').read_text())['groups'];self.assertTrue(any(g['inherited_dispute'] for g in gg))
                    self.assertTrue(all(not g['eligible_new_growth'] for g in gg if g['inherited_dispute']))
                    with mock.patch.object(ProtectedEngine,'pass_once',side_effect=AssertionError('NO_RECOMPUTE')):impl.run(c)
                fresh=dense(ProtectedEngine)
                with mock.patch.object(fresh,'pass_once',side_effect=AssertionError('NO_RECOMPUTE')):complete_pass(fresh,state,'M5_STATE')
                cp=control_dir(c,'prefix')/'STATE.pkl'
                with cp.open('ab') as f:f.write(b'corrupt')
                with self.assertRaisesRegex(RuntimeError,'HASH_MISMATCH'):complete_pass(fresh,state,'M5_STATE')
                self.tearDown()
    def test_m4_growth_statistics_unchanged(self):
        e=fixture();e.a['means']=e.a['means']*1.75;e.r['x']=e.r['x']*1.75;e.r['endpoints']=e.r['endpoints']*1.75;e.x=e.a['means'];e.rx=e.r['x'];e.ep=e.r['endpoints']
        for cc in e.carriers.values():cc.q*=1.75
        pre=copy.deepcopy(e.carriers);base=np.repeat([0,6],6);reset_level(e,5);e.pass_once(False);ids=e.primary(base)[0];expected=tables(e,ids,pre,base)
        self.assertTrue(any(g['growth_gate'] for g in expected))
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            common.CFG=dict(unit=td,runtime=td,scene='scan24',level=5,predecessor_label='M4')
            got=impl.statistics_level(Path(td),e,ids,pre,base,base,{'M2':base,'M3':base},disputed_override=set())
            for x,y in zip(expected,got):
                for key in ('growth_gate','outward_support_p','supported_length_p','longest_continuous_run_p','max_gap_p','total_gap_p'):self.assertEqual(x[key],y[key])
                self.assertEqual(x['gain_over_largest_L1_p'],y['gain_over_largest_M4_p'])
                for label in ('L1','M2','M3','M4'):self.assertEqual(sum(p['kernels'] for p in y[label+'_contributions']),y['kernels'])
    def test_geometry_and_caps(self):t12.Contracts.test_endpoint_hard_controls_reversal_and_caps(self)
    def test_real_m4_max128_seedlets(self):
        u1=UNIT.parent/'unit_016';cfg=json.loads((u1/'CONFIG.json').read_text());state=u1/'scenes/ficus/states/M4/STATE.pkl'
        assert sha(state)=='7d1457b144b0c58b8a3fe1fd1f1620e967158c1ace8326c64e6d996671378900'
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
        assert len(selected)<=128;print('REAL_M4_FIXTURE',len(rows),'kernels',len(selected),'seedlets',len(chosen),'carriers',flush=True);self.compare(e)

if __name__=='__main__':unittest.main()
