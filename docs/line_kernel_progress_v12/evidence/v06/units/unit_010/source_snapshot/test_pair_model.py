"""Unit005 bounded test-first specifications; no full original asset loading."""
from runtime_io import *
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from test_overlap_model import fixture
from overlap_model import compatibility,mapped_intervals
CORE=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_018/source_snapshot/core.py')

def recoverable():
    d=fixture(2,offsets=[0.,.4]);d['asset']['means'][:6,1]=-.2;d['asset']['means'][6:,1]=.6
    d['representatives']['x']=d['asset']['means'][d['representatives']['mid']].copy()
    return d

class LegacyBehaviorRed(unittest.TestCase):
    def test_host_support_must_use_new_model_coordinates(self):
        leaf=fixture(2)['leaves'][0];target=SimpleNamespace(cid=leaf.cid,q=np.array([[-1.,0,0],[7.,0,0]]))
        # Existing helper copies host intervals. New fitted model must remap them.
        from pair_model import map_support
        np.testing.assert_array_equal(map_support(leaf,target.q),[[1.,7.]])

class PairModelTests(unittest.TestCase):
    def test_recover_joint_model_when_both_old_anchors_fail(self):
        from pair_model import fit_engine,fit_pair,build_extra_bank
        d=recoverable();self.assertFalse(compatibility(d,0,1)[0]);self.assertFalse(compatibility(d,1,0)[0])
        engine=fit_engine(CORE,d);m=fit_pair(engine,d,0,1,0,None,lambda:None)
        self.assertEqual(engine.fit_count,1);self.assertEqual(m['status'],'RECOVERED');np.testing.assert_allclose(np.array(m['q'])[:,1],.2,atol=1e-12)
        hs,recs=build_extra_bank(d,dict(carriers=[0,1]),[m]);self.assertTrue(hs)
        self.assertTrue(all(set(m['seed_pair'])<=set(h['leaves']) for h in hs));self.assertAlmostEqual(hs[0]['metrics']['supported_length_p'],6.)
    def test_saved_metrics_mismatch_blocks_pair(self):
        from pair_model import fit_engine,fit_pair
        d=recoverable();e=fit_engine(CORE,d);m=fit_pair(e,d,0,1,0,dict(residual_max=99.),lambda:None)
        self.assertEqual(m['status'],'REPRODUCTION_MISMATCH');self.assertEqual(e.fit_count,1)
    def test_mandatory_partner_cannot_be_dropped(self):
        from pair_model import fit_engine,fit_pair,build_extra_bank
        d=fixture(3);e=fit_engine(CORE,d);m=fit_pair(e,d,0,2,0,None,lambda:None)
        hs,_=build_extra_bank(d,dict(carriers=[0,1,2]),[m]);self.assertTrue(hs)
        self.assertTrue(all(2 in h['leaves'] and 0 in h['leaves'] for h in hs))
    def test_model_finite_domain_applies_to_host(self):
        from pair_model import model_compatibility
        d=fixture(2);ok,why,_=model_compatibility(d,0,np.array([[.1,0,0],[5.9,0,0]]));self.assertFalse(ok);self.assertEqual(why,'finite_domain')
    def test_shared_bank_greedy_trap(self):
        from pair_model import select_greedy,select_joint
        hs=[dict(hid=0,anchor=0,model_key=[1,0,1],leaves=[0,1],benefit=3.),dict(hid=1,anchor=0,model_key=[1,0,2],leaves=[0,2],benefit=2.),dict(hid=2,anchor=1,model_key=[1,1,3],leaves=[1,3],benefit=2.)]
        self.assertEqual(select_greedy(hs),[0]);sel,rec=select_joint(hs,5);self.assertEqual(sel,[1,2]);self.assertEqual(rec['status'],'optimal')
    def test_no_solver_without_budget(self):
        from pair_model import select_joint
        self.assertEqual(select_joint([],0)[1]['status'],'partial')

if __name__=='__main__':unittest.main(verbosity=2)
