"""Test-first bounded counterfactual policy fixtures; no asset science."""
from runtime_io import *
from port_paths import Edge,Leaf,PathOracle,joint
from unittest.mock import patch
import unittest
try:
    from ambiguity_policy import select_ambiguity,certify_component
    IMPLEMENTED=True
except ModuleNotFoundError:
    # Execute the actual unit002 mask-filtered selection as RED baseline.
    from adapter import select
    IMPLEMENTED=False
    def select_ambiguity(c,d):
        return select(c,d)[1],{}
    def certify_component(edges,oracle,previous,seconds,guard=lambda:None,max_rounds=32):
        return previous,{'status':'legacy_local_mask','certificates':[]}
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_003/tests')

def always(chain):return True,'ok',{}
class AmbiguityTests(unittest.TestCase):
    def data(self,overlap=False):
        es=[Edge(0,1,1,2,0,.1),Edge(1,1,1,3,0,.2),Edge(2,2,0,4,0,.2)]
        pp=[(1,2),(1,3),(2,4)]+([(4,5)] if overlap else [])
        z=dict(a=np.array([x[0] for x in pp]),b=np.array([x[1] for x in pp]),operation=np.array(['endpoint']*3+(['overlap'] if overlap else [])),reason=np.array(['ambiguous']*len(pp)))
        f=U/('reference_'+str(time.time_ns())+'.npz');nz(f,edge_id=np.array([53254]))
        c=dict(reference_membership=str(f),seed_groups=[53254],negative_pairs=[],decision_carrier_cap=128)
        return c,dict(edges=[],all_endpoint=es,pairs=pp,ambiguous=set(pp[:3]),candidates=z,owner=np.array([1]))
    def test_masked_competitors_are_present_before_selection(self):
        c,d=self.data();ctx,_=select_ambiguity(c,d)
        self.assertEqual(len(ctx),1)
        self.assertEqual(ctx[0]['carriers'],[1,2,3,4]);self.assertEqual(ctx[0]['eligible_edge_ids'],[0,1,2])
    def test_any_incident_successful_overlap_excludes_whole_component(self):
        c,d=self.data(True);ctx,audit=select_ambiguity(c,d)
        self.assertEqual(ctx,[])
        if IMPLEMENTED:self.assertEqual(audit['overlap_blocked_components'],1)
    def test_locally_ambiguous_globally_unique_recovers(self):
        c,d=self.data();out,r=certify_component(d['all_endpoint'],always,dict(greedy=[],joint=[]),5)
        self.assertEqual(out['joint'],[1,2]);self.assertEqual(out['greedy'],[])
        self.assertEqual(r['status'],'certified_complete')
        self.assertEqual({x['edge'] for x in r['certificates'] if x['certified']},{1,2})
    def test_symmetric_optimal_alternatives_remain_unassigned(self):
        es=[Edge(0,1,1,2,0,.2),Edge(1,1,1,3,0,.2)]
        out,r=certify_component(es,always,dict(greedy=[],joint=[]),5)
        self.assertEqual(out,dict(greedy=[],joint=[]));self.assertEqual(r['status'],'certified_complete')
        self.assertTrue(all(not x['certified'] for x in r['certificates']))
    def test_incomplete_component_reverts_both_arms(self):
        if not IMPLEMENTED:self.skipTest('new API not implemented')
        previous=dict(greedy=[7],joint=[8]);es=[Edge(0,1,1,2,0,.2)]
        with patch('ambiguity_policy.joint',return_value=([],dict(status='cut_limit',seconds=0,cuts=[]))):
            out,r=certify_component(es,always,previous,5)
        self.assertEqual(out,previous);self.assertEqual(r['status'],'fallback_partial')
    def test_filtered_subpaths_rechecked_and_unknown_kept(self):
        if not IMPLEMENTED:self.skipTest('new API not implemented')
        from delivery import membership_for
        ls={i:Leaf(i,i,np.arange((i-1)*3,i*3),np.array([i]),np.array([[i*.6,0,0],[i*.6+.5,0,0]]),True,False,np.array([[0,.5]])) for i in (1,2,3)}
        es=[Edge(0,1,1,2,0,.2),Edge(1,2,1,3,0,.2)];oracle=PathOracle(ls)
        out,r=certify_component(es,oracle,dict(greedy=[],joint=[]),5)
        self.assertEqual(out['joint'],[0,1]);self.assertTrue(r['postfilter_guard_passed'])
        m,g,_=membership_for(dict(edges=es,leaves=ls,membership=dict(edge_id=np.full(9,-1))),out['joint'],oracle)
        self.assertTrue(np.all(m['edge_id']<0));self.assertEqual(g[0]['unknown_retained'],9)
    def test_budget_zero_preserves_both_previous_states(self):
        if not IMPLEMENTED:self.skipTest('new API not implemented')
        old=dict(greedy=[4],joint=[5]);out,r=certify_component([Edge(0,1,1,2,0,.2)],always,old,0)
        self.assertEqual(out,old);self.assertEqual(r['status'],'fallback_partial')
if __name__=='__main__':unittest.main(verbosity=2)
