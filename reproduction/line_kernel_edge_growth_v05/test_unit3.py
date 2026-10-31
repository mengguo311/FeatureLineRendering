"""Bounded unit_003 tests; no complete-asset computation or old-unit writes."""
from common import *
import common,copy,tempfile,unittest
from unittest import mock
from test_build import fixture
import scene_runner
import types,sys
from pipeline import state_of,load_state
from transfer import TransferEngine,complete_pass,reset_level

ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
RUNTIME=ROOT/'line_kernel_edge_growth_v05_20261031'
UNIT=RUNTIME/'units/unit_003'
U2=UNIT.parent/'unit_002'

def chain_fixture(kind='straight'):
    e=fixture(kind);n=len(e.x)
    chains=dict(nodes=np.arange(len(e.rx)),offsets=np.arange(0,len(e.rx)+1,3),representative_edge_id=np.repeat(np.arange(0,n,6),3))
    return e.a,e.r,e.t,e.p,np.repeat(np.arange(0,n,6),6),chains

def small_config(out):
    a,r,t,p,base,ch=chain_fixture()
    a['covariance']=np.tile(np.eye(3)*1e-4,(len(base),1,1));a['opacity']=np.full(len(base),.7)
    for name,data in [('line',a),('representatives',r),('membership',dict(edge_id=base,reason_code=np.zeros(len(base),np.uint8))),('chains',ch),('controls',dict(control=t[:,None,:],control_index=np.arange(len(base)),derivative_basis=np.ones((len(base),1))))]:nz(out/(name+'.npz'),**data)
    js(out/'DECISION.json',dict(scope='12-row regression only'))
    cameras=ROOT/'line_kernel_edge_grouping_v03/units/unit_001/CAMERAS.json'
    inputs={str(z):sha(z) for z in out.glob('*.npz')};inputs[str(cameras)]=sha(cameras)
    c=dict(unit=str(out),runtime=str(out),scene='scan65',kernel_count=len(base),views=['0012','0036'],p=p,gaussians=str(out/'line.npz'),controls=str(out/'controls.npz'),representatives=str(out/'representatives.npz'),baseline_membership=str(out/'membership.npz'),chains=str(out/'chains.npz'),cameras=str(cameras),renderer='/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01/renderer.py',libroot=str(ROOT/'c2l50_8build_joint_gs_v01'),input_files=inputs,source_files={},helper_files={},decision_path=str(out/'DECISION.json'),decision_sha256=sha(out/'DECISION.json'),max_seconds=240,science_deadline=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(minutes=5)).isoformat(),unit_deadline=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(minutes=5)).isoformat(),stage_elapsed_limits=dict(control=30,L0=60,L1=120,M2=180,final=240),visual_selection='unchanged unit2 selector',reference_results=[])
    js(out/'CONFIG.json',c);c['_config_sha256']=sha(out/'CONFIG.json');return c

class RoutingContracts(unittest.TestCase):
    def tearDown(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def test_no_old_scene_replay(self):
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);c=small_config(out)
            with mock.patch('transfer.control_replay',side_effect=AssertionError('FORBIDDEN_OLD_SCENE_REPLAY')):scene_runner.run(c)
            self.assertFalse((out/'controls/scan24').exists())
            self.assertEqual(json.loads((out/'RUN_RESULT.json').read_text())['status'],'complete')
    def test_saved_labels_use_config_scene(self):
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);c=small_config(out)
            with mock.patch('transfer.control_replay',return_value=None):scene_runner.run(c)
            result=json.loads((out/'RUN_RESULT.json').read_text())
            self.assertIn('scan65/M2_NATIVE',result['completed'])
            self.assertFalse(any('ficus' in v or 'SCAN24' in v for v in result['completed']))
            self.assertNotIn('scan65',result['not_requested'])
            for level in ('L0','L1','M2_MERGE_ONLY'):
                path=out/'scenes/scan65/stages'/level
                self.assertEqual(len(np.load(path/'MEMBERSHIP.npz')['edge_id']),12)
                for view in c['views']:self.assertTrue((path/(view+'_FULL.png')).exists())

def equal(a,z):
    if isinstance(a,np.ndarray):np.testing.assert_array_equal(a,z)
    elif hasattr(a,'cid'):
        for k in vars(a):equal(getattr(a,k),getattr(z,k))
    elif isinstance(a,dict):
        assert a.keys()==z.keys(),(a.keys(),z.keys())
        for k in a:equal(a[k],z[k])
    elif isinstance(a,(tuple,list)):
        assert len(a)==len(z)
        for x,y in zip(a,z):equal(x,y)
    else:assert a==z,(a,z)

def frozen_reference():
    manifest=json.loads((U2/'PARENT_RUN_FROZEN.json').read_text());source=Path(__file__).resolve().parent/'core.py'
    snap=Path(manifest['immutable_source_snapshot'][str(source)])
    assert sha(snap)==manifest['source_files'][str(source)]==sha(source)
    ref=types.ModuleType('unit2_frozen_core');sys.modules[ref.__name__]=ref
    exec(compile(snap.read_text(),str(snap),'exec'),ref.__dict__);return ref

class ScientificEquivalence(unittest.TestCase):
    def setUp(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def compare_sequence(self,a,r,t,p,base,ch):
        ref=frozen_reference();e=TransferEngine(a,r,t,p);rr=ref.Engine(a,r,t,p)
        e.initialize(base,ch);rr.initialize(base,ch);equal(e.carriers,rr.carriers);equal(dict(e.stats),dict(rr.stats))
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            for index,pooling in ((1,True),(2,True),(3,False)):
                if index in (1,3):reset_level(e,1 if index==1 else 2);reset_level(rr,e.level)
                equal(e.candidates(),rr.candidates());before=e.fit_count
                path=Path(td)/str(index);stage=f'PASS{index}';complete_pass(e,path,stage,pooling);rr.pass_once(pooling)
                for x,y in ((e.fit_count,rr.fit_count),(e.next_version,rr.next_version),(e.events,rr.events),(e.records,rr.records),(dict(e.stats),dict(rr.stats)),(e.carriers,rr.carriers),(dict(e.aux),dict(rr.aux))):equal(x,y)
                if index==2:self.assertGreaterEqual(e.fit_count,before)
                for x,y in zip(e.primary(base),rr.primary(base)):equal(x,y)
                fresh=TransferEngine(a,r,t,p)
                with mock.patch.object(fresh,'pass_once',side_effect=AssertionError('COMPLETE_STAGE_MUST_NOT_RECOMPUTE')):complete_pass(fresh,path,stage,pooling)
                equal(state_of(fresh),state_of(e));print('SEQUENCE',stage,'fits',e.fit_count,'events',len(e.events),flush=True)
    def test_hard_fixture_sequences(self):
        for kind in ('straight','duplicate','gentle_curve','curve','S','parallel','T','X','gap','tie'):
            with self.subTest(kind=kind):self.compare_sequence(*chain_fixture(kind))
    def test_real_scan65_compact_chains(self):
        orch=RUNTIME/'orchestration';sealed=json.loads((orch/'V03_SEALED_REFERENCE.json').read_text());v03=Path(sealed['root'])
        paths=[v03/'scan65/REPRESENTATIVES.npz',v03/'scan65/baseline/CHAINS.npz',v03/'scan65/baseline/MEMBERSHIP.npz',v03/'scan65/baseline/GROUPS.json']
        verify({str(z):sealed['files'][str(z.relative_to(v03))] for z in paths})
        source=ROOT/'c2l50_multiview05_v01/arms/C/scenes/scan65/full';lock=json.loads((orch/'INPUT_LOCK.json').read_text())['files']
        verify({str(source/n):lock[str(source/n)] for n in ('gaussians.npz','SHARED_CONTROL_AND_SAMPLING.npz')})
        oldr=dict(np.load(paths[0]));oldch=dict(np.load(paths[1]));p=json.loads(paths[3].read_text())['p']
        a0=dict(np.load(source/'gaussians.npz'));controls=dict(np.load(source/'SHARED_CONTROL_AND_SAMPLING.npz'));chains=[]
        for lo,hi in zip(oldch['offsets'][:-1],oldch['offsets'][1:]):
            if 2<=hi-lo<=8:chains.append(oldch['nodes'][lo:hi])
            if len(chains)==4:break
        selected=np.concatenate(chains);assert len(selected)<=128
        rows=np.concatenate([oldr['member_rows'][oldr['member_offsets'][rid]:oldr['member_offsets'][rid+1]] for rid in selected])
        counts=np.array([oldr['member_offsets'][rid+1]-oldr['member_offsets'][rid] for rid in selected]);off=np.r_[0,counts.cumsum()];mapping={int(rid):j for j,rid in enumerate(selected)}
        r=dict(x=oldr['x'][selected],t=oldr['t'][selected],endpoints=oldr['endpoints'][selected],kernel_rep=np.repeat(np.arange(len(selected)),counts),member_rows=np.arange(len(rows)),member_offsets=off,mid=off[:-1]+counts//2)
        a={k:v[rows].copy() for k,v in a0.items()};dd=(controls['control'][controls['control_index'][rows]]*controls['derivative_basis'][rows,:,None]).sum(1);t=dd/np.maximum(np.linalg.norm(dd,axis=1)[:,None],1e-15)
        nodes=np.array([mapping[int(rid)] for cc in chains for rid in cc]);offsets=np.r_[0,np.cumsum([len(cc) for cc in chains])];edge=np.empty(len(selected),np.int64);base=np.empty(len(rows),np.int64)
        for lo,hi in zip(offsets[:-1],offsets[1:]):
            cid=int(off[lo]);edge[lo:hi]=cid;base[off[lo]:off[hi]]=cid
        ch=dict(nodes=nodes,offsets=offsets,representative_edge_id=edge)
        print('REAL_SCAN65_SMALL',len(rows),'kernels',len(selected),'seedlets',flush=True);self.compare_sequence(a,r,t,p,base,ch)
    def test_exhausted_budget_and_tampered_resume(self):
        e=fixture('tie');e.fit_count=29999;e.level=1
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);complete_pass(e,out/'first','FIRST',True);self.assertEqual(e.fit_count,30000);version=e.next_version
            fresh=fixture('tie');complete_pass(fresh,out/'first','FIRST',True);complete_pass(fresh,out/'second','SECOND',True)
            self.assertEqual(fresh.fit_count,30000);self.assertEqual(fresh.next_version,version)
            with (out/'second/STATE.pkl').open('ab') as f:f.write(b'corruption')
            with self.assertRaisesRegex(RuntimeError,'HASH_MISMATCH'):complete_pass(fresh,out/'second','SECOND',True)
    def test_export_survives_diagnostic_failure(self):
        with tempfile.TemporaryDirectory(dir=UNIT/'tests') as td:
            out=Path(td);c=small_config(out)
            try:
                with mock.patch.object(scene_runner,'diagnostics',side_effect=RuntimeError('INJECTED_DIAGNOSTIC_FAILURE')):
                    with self.assertRaisesRegex(RuntimeError,'INJECTED_DIAGNOSTIC_FAILURE'):scene_runner.run(c)
                result=json.loads((out/'RUN_RESULT.json').read_text());self.assertEqual(result['status'],'partial');self.assertIn('scan65/M2_NATIVE',result['completed'])
                cp=out/'scenes/scan65/states/M2';scene_runner.verify_checkpoint(cp,'M2_STATE');self.assertTrue(load_state(cp/'STATE.pkl')['carriers'])
                self.assertTrue((out/'scenes/scan65/stages/M2_MERGE_ONLY/0012_FULL.png').exists())
            finally:common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
