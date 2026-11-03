"""Bounded decision/evidence separation tests; never executes a full asset."""
from runtime_io import *
from adapter import select
from port_paths import Edge
import unittest
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_002/tests')
U.mkdir(parents=True,exist_ok=True)

class ScopeTests(unittest.TestCase):
    def data(self, edges, pairs):
        f=U/('reference_'+str(time.time_ns())+'.npz')
        nz(f,edge_id=np.array([53254,-1]))
        c=dict(reference_membership=str(f),seed_groups=[53254],negative_pairs=[],decision_carrier_cap=128)
        d=dict(leaves={},owner=np.array([1,2]),edges=edges,all_endpoint=edges,pairs=pairs,ambiguous=set())
        return c,d
    def test_rejected_chain_is_evidence_not_recursive_decision(self):
        es=[Edge(0,1,1,2,0,.2),Edge(1,2,1,3,0,.2)]
        c,d=self.data(es,[(1,2),(2,3)]+[(i,i+1) for i in range(3,140)])
        _,contexts=select(c,d)
        self.assertEqual(contexts[0]['carriers'],[1,2,3])
        self.assertEqual(contexts[0]['evidence_carriers'],[1,2,3,4])
        self.assertEqual(contexts[0]['incident_record_ids'],[0,1,2])
        self.assertEqual(contexts[0]['status'],'READY')
    def test_all_competitors_and_disconnected_two_leaf_component(self):
        es=[Edge(0,1,1,2,0,.2),Edge(1,2,1,3,0,3.),Edge(2,3,1,4,0,.2),Edge(3,20,1,21,0,.2)]
        c,d=self.data(es,[(1,2),(2,3),(3,4),(20,21)])
        _,contexts=select(c,d)
        self.assertEqual(sorted(e for ctx in contexts for e in ctx['eligible_edge_ids']),[0,1,2,3])
        self.assertEqual([ctx['carriers'] for ctx in contexts],[[1,2,3,4],[20,21]])
    def test_large_decision_component_never_trimmed(self):
        es=[Edge(i,i,i%2,i+1,0,.2) for i in range(140)]
        c,d=self.data(es,[(e.a,e.b) for e in es])
        _,contexts=select(c,d)
        self.assertEqual(len(contexts[0]['carriers']),141)
        self.assertEqual(contexts[0]['status'],'NOT_RUN_OVERSIZE')

if __name__=='__main__':unittest.main(verbosity=2)
