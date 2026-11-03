"""Vertical small adapter/checkpoint fixtures; no full-asset execution."""
from runtime_io import *
from adapter import Carrier,state_read,validate_candidates
from port_paths import Leaf,PathOracle,greedy,joint
from delivery import export_arm,membership_for
import unittest,pickle,sys,types,shutil
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_002/tests')
class AdapterTests(unittest.TestCase):
    def make(self):
        q=np.array([[0.,0,0],[2.,0,0]])
        ls={i:Leaf(i,i,np.arange((i-1)*6,i*6),np.arange((i-1)*3,i*3),q+[(i-1)*2.1,0,0],True,False,np.array([[0.,2.]])) for i in (1,2,3)}
        z=dict(a=np.array([1,2]),b=np.array([2,3]),operation=np.array(['endpoint','endpoint']),reason=np.array(['accepted','round_conflict']),cost=np.array([.3,.3]),metric_names=np.array(['residual_max','residual_q95','tangent_max']),metrics=np.array([[.1,.05,6.],[.1,.05,6.]]))
        ordered=dict(a=z['a'],b=z['b'],cost=np.array([99.,99.]))
        return ls,z,ordered
    def test_cost_uses_successful_fit_not_rank(self):
        ls,z,ordered=self.make();edges,all_e,pairs=validate_candidates(ls,z,ordered,{(1,2)})
        self.assertEqual([e.eid for e in edges],[1]);self.assertEqual(len(all_e),2);self.assertAlmostEqual(edges[0].cost,.3)
        z['cost'][0]=.4
        with self.assertRaises(AssertionError):validate_candidates(ls,z,ordered,set())
    def test_duplicate_candidate_coverage_blocks(self):
        ls,z,ordered=self.make();ordered['a']=np.array([1,1]);ordered['b']=np.array([2,2])
        with self.assertRaises(AssertionError):validate_candidates(ls,z,ordered,set())
    def test_vertical_checkpoint_survives_later_failure(self):
        ls,z,ordered=self.make();edges,_,_=validate_candidates(ls,z,ordered,set());o=PathOracle(ls);selected,_=joint(edges,o,10)
        m=dict(line_kernel_id=np.arange(18),edge_id=np.repeat([1,2,-1],6),carrier_id=np.repeat([1,2,3],6),reason_code=np.zeros(18,np.int8),primitive_id=np.repeat([11,12,13],6),provisional=np.ones(18,bool))
        means=np.concatenate([np.linspace(c.q[0],c.q[-1],6) for c in ls.values()]);repends=np.concatenate([np.repeat(c.q[None,:,:],3,axis=0) for c in ls.values()])
        d=dict(p=1.,leaves=ls,edges=edges,membership=m,asset=dict(primitive_id=m['primitive_id'],means=means),representatives=dict(mid=np.arange(0,18,2),endpoints=repends),arrays=dict(carrier_id=np.array([1,2,3])))
        root=U/('vertical_'+str(time.time_ns()));c=dict(membership='fixture',state='fixture',input_files={'fixture':'fixture'})
        cold,groups=export_arm(root,c,d,selected,o,[],{},'fixture-binding')
        self.assertEqual(cold['edge_id'].tolist(),[1]*18);self.assertEqual(len(groups[0]['leaves']),3)
        try:raise RuntimeError('simulated post-checkpoint diagnostic failure')
        except RuntimeError:pass
        verify_checkpoint(root,'fixture-binding');self.assertTrue((root/'MEMBERSHIP.npz').exists())
        with self.assertRaises(AssertionError):verify_checkpoint(root,'wrong-binding')
    def test_insufficient_dormant_support_stays_unknown(self):
        from port_paths import Edge
        ls={1:Leaf(1,1,np.arange(6),np.arange(3),np.array([[0.,0,0],[.5,0,0]]),True,False,np.array([[0.,.5]])),2:Leaf(2,1,np.arange(6,12),np.arange(3,6),np.array([[.6,0,0],[1.1,0,0]]),True,False,np.array([[0.,.5]]))}
        original=dict(edge_id=np.array([1]*6+[-1]*6),reason_code=np.ones(12,np.int8),line_kernel_id=np.arange(12))
        d=dict(leaves=ls,edges=[Edge(0,1,1,2,0,.2)],membership=original)
        m,gs,_=membership_for(d,[0],PathOracle(ls))
        np.testing.assert_array_equal(m['edge_id'],original['edge_id']);self.assertEqual(gs[0]['unknown_retained'],6)
    def test_restricted_schema_rejects_unapproved_global(self):
        path=U/('bad_'+str(time.time_ns())+'.pkl');path.write_bytes(pickle.dumps(Path('/tmp/forbidden')))
        with self.assertRaises(pickle.UnpicklingError):state_read(path)
    def test_bounded_real_leaf_roundtrip(self):
        fixture=dict(np.load(U/'REAL_LEAVES.npz',allow_pickle=False));n=len(fixture['ids']);self.assertGreater(n,0);self.assertLessEqual(n,4)
        mod=types.ModuleType('core');Original=type('Carrier',(),{});Original.__module__='core';mod.Carrier=Original;sys.modules['core']=mod;carriers={}
        for j,cid in enumerate(fixture['ids']):
            cc=Original();lo,hi=fixture['offsets'][j:j+2];q=fixture['knots'][lo:hi]
            cc.__dict__.update(cid=int(cid),version=int(fixture['versions'][j]),q=q,kind='polyline',reps=np.arange(3),rows=np.arange(6),valid=True,baseline=False,origins=())
            carriers[int(cid)]=cc
        path=U/('real_schema_'+str(time.time_ns())+'.pkl');path.write_bytes(pickle.dumps(dict(carriers=carriers,aux={},next_version=100)))
        restored=state_read(path)
        for j,cid in enumerate(fixture['ids']):
            np.testing.assert_array_equal(restored['carriers'][int(cid)].q,carriers[int(cid)].q)
        del sys.modules['core']
if __name__=='__main__':unittest.main(verbosity=2)
