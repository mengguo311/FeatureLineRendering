"""Unit 2 test-first contracts; small fixtures and saved metadata only."""
from common import *
from core import Engine
from pipeline import state_of,load_state
from test_build import fixture
import transfer_behavior as b
import unittest,tempfile,copy
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
U=ROOT/'line_kernel_edge_growth_v05_20261031/units/unit_002'
U1=U.parent/'unit_001'
class NewContracts(unittest.TestCase):
    def test_real_saved_growth_examples_selected(self):
        groups=json.loads((U1/'scenes/scan24/stages/M2_MERGE_ONLY/GROUPS.json').read_text())['groups']
        ids={g['edge_id'] for g in b.select_groups(groups)}
        self.assertTrue({103748,202626}<=ids,'Saved qualifying line/polyline must not be displaced by largest pooled groups')
    def test_scene_contract_is_parameterized(self):
        c=dict(scene='ficus',kernel_count=12,views=['test_r_1','test_r_79'])
        b.scene_contract(c,dict(means=np.zeros((12,3))),[dict(view=v) for v in c['views']])
    def test_pool_resume_preserves_actual_budget_and_versions(self):
        e=fixture('duplicate');e.level=1;e.fit_count=29999;e.pass_once(True)
        self.assertEqual(e.fit_count,30000);self.assertEqual(len(e.events),1)
        with tempfile.TemporaryDirectory(dir=U/'tests') as td:
            p=Path(td)/'STATE.pkl';pk(p,state_of(e));cold=load_state(p);other=fixture('duplicate');b.resume_state(other,cold)
            self.assertEqual(other.fit_count,30000,'Restoring only carrier fields silently replenishes the fit budget')
            self.assertEqual(other.next_version,e.next_version);self.assertEqual(other.events,e.events)
            self.assertEqual(other.carriers[0].version,e.carriers[0].version)
if __name__=='__main__':unittest.main()

# Additional regressions are discovered by build_unit2.py; RED snapshot remains immutable.
import types,sys
from transfer import TransferEngine,complete_pass,reset_level,save_state,export_stage,statistics,diagnostics
from pipeline import verify_checkpoint

SNAP=U1/'source_snapshot/core.py'
ref=types.ModuleType('unit1_frozen_reference');sys.modules[ref.__name__]=ref
manifest=json.loads((U1/'SOURCE_SNAPSHOT.json').read_text())['snapshot_files'];assert sha(SNAP)==manifest[str(SNAP)]
exec(compile(SNAP.read_text(),str(SNAP),'exec'),ref.__dict__)

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

def initialized_pair(a,r,t,p,base,chains):
    ee=TransferEngine(a,r,t,p);rr=ref.Engine(a,r,t,p);ee.initialize(base,chains);rr.initialize(base,chains);equal(ee.carriers,rr.carriers);equal(dict(ee.stats),dict(rr.stats));return ee,rr

def chain_fixture(kind):
    f=fixture(kind);n=len(f.x);chains=dict(nodes=np.arange(len(f.rx)),offsets=np.arange(0,len(f.rx)+1,3),representative_edge_id=np.repeat(np.arange(0,n,6),3))
    base=np.repeat(np.arange(0,n,6),6);return f.a,f.r,f.t,f.p,base,chains

class FullSequence(unittest.TestCase):
    def compare_sequence(self,e,r,base):
        initial=copy.deepcopy(e.carriers)
        with tempfile.TemporaryDirectory(dir=U/'tests') as td:
            out=Path(td)
            for pooling,index in ((True,1),(True,2),(False,3)):
                if index in (1,3):reset_level(e,1 if index==1 else 2);reset_level(r,e.level)
                equal(e.candidates(),r.candidates())
                before=e.fit_count;stage=f'PASS{index}';complete_pass(e,out/stage,stage,pooling);r.pass_once(pooling)
                equal(e.fit_count,r.fit_count);equal(e.next_version,r.next_version);equal(e.records,r.records);equal(e.events,r.events);equal(dict(e.stats),dict(r.stats));equal(e.carriers,r.carriers);equal(dict(e.aux),dict(r.aux))
                if index==2:self.assertGreaterEqual(e.fit_count,before)
                for x,y in zip(e.primary(base),r.primary(base)):equal(x,y)
                # Hash-verified resume skips computation and restores the complete budget/history.
                fresh=TransferEngine(e.a,e.r,e.t,e.p);complete_pass(fresh,out/stage,stage,pooling);equal(fresh.fit_count,e.fit_count);equal(fresh.carriers,e.carriers);equal(fresh.events,e.events)
                print('SEQUENCE',stage,'pooling',pooling,'fit_count',e.fit_count,'events',len(e.events),flush=True)
    def test_small_full_sequences(self):
        for kind in ('straight','duplicate','gentle_curve','curve','S','parallel','T','X','gap','tie'):
            with self.subTest(kind=kind):
                a,r,t,p,base,ch=chain_fixture(kind);e,refe=initialized_pair(a,r,t,p,base,ch);self.compare_sequence(e,refe,base)
    def test_real_ficus_compact_chains(self):
        orch=U.parent.parent/'orchestration';sealed=json.loads((orch/'V03_SEALED_REFERENCE.json').read_text());v03=Path(sealed['root']);paths=[v03/'ficus/REPRESENTATIVES.npz',v03/'ficus/baseline/CHAINS.npz',v03/'ficus/baseline/MEMBERSHIP.npz',v03/'ficus/baseline/GROUPS.json']
        verify({str(p):sealed['files'][str(p.relative_to(v03))] for p in paths})
        source=ROOT/'c2l50_multiview05_v01/arms/C/scenes/ficus/full';lock=json.loads((orch/'INPUT_LOCK.json').read_text())['files'];verify({str(source/n):lock[str(source/n)] for n in ('gaussians.npz','SHARED_CONTROL_AND_SAMPLING.npz')})
        oldr=dict(np.load(paths[0]));oldch=dict(np.load(paths[1]));oldbase=dict(np.load(paths[2]));p=json.loads(paths[3].read_text())['p'];a0=dict(np.load(source/'gaussians.npz'));controls=dict(np.load(source/'SHARED_CONTROL_AND_SAMPLING.npz'))
        chains=[]
        for lo,hi in zip(oldch['offsets'][:-1],oldch['offsets'][1:]):
            if 2<=hi-lo<=8:chains.append(oldch['nodes'][lo:hi])
            if len(chains)==4:break
        selected=np.concatenate(chains);assert len(selected)<=32
        rows=np.concatenate([oldr['member_rows'][oldr['member_offsets'][rid]:oldr['member_offsets'][rid+1]] for rid in selected]);counts=np.array([oldr['member_offsets'][rid+1]-oldr['member_offsets'][rid] for rid in selected]);off=np.r_[0,counts.cumsum()];mapping={int(rid):j for j,rid in enumerate(selected)};mid=off[:-1]+counts//2
        r=dict(x=oldr['x'][selected],t=oldr['t'][selected],endpoints=oldr['endpoints'][selected],kernel_rep=np.repeat(np.arange(len(selected)),counts),member_rows=np.arange(len(rows)),member_offsets=off,mid=mid)
        a={k:v[rows].copy() for k,v in a0.items()};dd=(controls['control'][controls['control_index'][rows]]*controls['derivative_basis'][rows,:,None]).sum(1);t=dd/np.maximum(np.linalg.norm(dd,axis=1)[:,None],1e-15)
        nodes=np.array([mapping[int(rid)] for cc in chains for rid in cc]);offsets=np.r_[0,np.cumsum([len(cc) for cc in chains])];edge=np.empty(len(selected),np.int64);base=np.empty(len(rows),np.int64)
        for lo,hi in zip(offsets[:-1],offsets[1:]):
            cid=int(off[lo]);edge[lo:hi]=cid;base[off[lo]:off[hi]]=cid
        ch=dict(nodes=nodes,offsets=offsets,representative_edge_id=edge);e,rr=initialized_pair(a,r,t,p,base,ch);print('REAL_FICUS_SMALL',len(rows),'kernels',len(selected),'seedlets',flush=True);self.compare_sequence(e,rr,base)
    def test_exhausted_pool_resume_cannot_replenish(self):
        e=fixture('tie');e.fit_count=29999;e.level=1
        with tempfile.TemporaryDirectory(dir=U/'tests') as td:
            p=Path(td);complete_pass(e,p/'first','FIRST',True);budget=e.fit_count;version=e.next_version;self.assertEqual(budget,30000)
            fresh=fixture('tie');complete_pass(fresh,p/'first','FIRST',True);self.assertEqual(fresh.fit_count,budget);self.assertEqual(fresh.next_version,version)
            complete_pass(fresh,p/'second','SECOND',True);self.assertEqual(fresh.fit_count,30000);self.assertEqual(fresh.next_version,version)
    def test_small_native_pipeline_and_crop(self):
        a,r,t,p,baseids,ch=chain_fixture('straight');a['covariance']=np.tile(np.eye(3)*1e-4,(len(baseids),1,1));a['opacity']=np.full(len(baseids),.7);base=dict(edge_id=baseids,reason_code=np.zeros(len(baseids),np.uint8));e=TransferEngine(a,r,t,p);e.initialize(baseids,ch)
        with tempfile.TemporaryDirectory(dir=U/'tests') as td:
            out=Path(td);src=out/'line.npz';nz(src,**a);camfile=ROOT/'line_kernel_edge_grouping_v03/units/unit_001/CAMERAS.json';cams=json.loads(camfile.read_text())['ficus'];c=dict(scene='ficus',kernel_count=len(baseids),views=['test_r_1','test_r_79'],gaussians=str(src),cameras=str(camfile),input_files={str(src):sha(src),str(camfile):sha(camfile)},helper_files={},source_files={},renderer='/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01/renderer.py',libroot=str(ROOT/'c2l50_8build_joint_gs_v01'),visual_selection='frozen unit2 selector')
            b.scene_contract(c,a,cams);pre0=dict(e.carriers);render=helpers(c)['render'];m0,_=export_stage(c,out/'L0',e,a,r,base,base,pre0,render,cams,'L0','fixture');statistics(out/'L0',e,m0['edge_id'],pre0,baseids,'L0')
            reset_level(e,1);complete_pass(e,out/'P1','P1',True);complete_pass(e,out/'P2','P2',True);m1,_=export_stage(c,out/'L1',e,a,r,base,m0,pre0,render,cams,'L1','fixture');statistics(out/'L1',e,m1['edge_id'],pre0,baseids,'L1');pre1=dict(e.carriers)
            reset_level(e,2);complete_pass(e,out/'M','M',False);m2,_=export_stage(c,out/'M2',e,a,r,base,m1,pre1,render,cams,'M2_MERGE_ONLY','fixture');g=statistics(out/'M2',e,m2['edge_id'],pre1,baseids,'M2_MERGE_ONLY');diagnostics(c,out/'D',e,a,m2['edge_id'],g,pre1,base,m1,render,cams)
            self.assertEqual(len(m2['edge_id']),12);self.assertTrue((out/'D/CROPS.json').exists())
            # Exact nearest-neighbor crop, including blank-case preservation.
            rgb=np.full((40,40,3),255,np.uint8);rgb[20,20]=[1,2,3];f=out/'pixel.png';atomic(f,lambda z:Image.fromarray(rgb).save(z,format='PNG'));info=b.crop_family([f],out/'crop');self.assertEqual(info['crop_box_xyxy'],[4,4,37,37]);image=np.asarray(Image.open(info['files'][0]));np.testing.assert_array_equal(image[64:68,64:68],np.tile([1,2,3],(4,4,1)))
            blank=out/'blank.png';atomic(blank,lambda z:Image.fromarray(np.full((40,40,3),255,np.uint8)).save(z,format='PNG'));self.assertEqual(b.crop_family([blank],out/'empty')['status'],'NO_VISIBLE_PIXELS')
