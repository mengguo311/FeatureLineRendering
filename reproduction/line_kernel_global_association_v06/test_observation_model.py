from runtime_io import *
import unittest
from test_overlap_model import fixture
from observation_model import model_compatibility
from pair_model import model_compatibility as legacy
class DomainTests(unittest.TestCase):
    def test_old_q_tail_is_not_an_observation(self):
        d=fixture(2);leaf=d['leaves'][0];leaf.q=np.array([[-.2,0,0],[6.2,0,0]])
        q=np.array([[0.,0,0],[6.,0,0]])
        self.assertEqual(legacy(d,0,q)[1],'finite_domain')
        ok,why,met=model_compatibility(d,0,q)
        self.assertTrue(ok,why)
    def test_centers_outside_must_not_be_clamped_into_domain(self):
        d=fixture(2);d['asset']['means'][0,0]=-.1;q=d['leaves'][0].q
        self.assertTrue(legacy(d,0,q)[0])
        self.assertFalse(model_compatibility(d,0,q)[0])
if __name__=='__main__':unittest.main(verbosity=2)

class GuardRegression(unittest.TestCase):
    def test_reverse_and_nonmonotone(self):
        d=fixture(2);q=d['leaves'][0].q.copy();d['leaves'][0].q=q[::-1].copy()
        ok,why,m=model_compatibility(d,0,q);self.assertTrue(ok);self.assertTrue(m['reverse'])
        d['leaves'][0].q=np.array([[0.,0,0],[6.,0,0],[3.,0,0]])
        self.assertEqual(model_compatibility(d,0,q)[1],'nonmonotone')
    def test_diagnostic_unclamped_centers_and_support(self):
        d=fixture(2);d['asset']['means'][0,0]=-.1;q=d['leaves'][0].q.copy()
        ok,why,m=model_compatibility(d,0,q);a=m['domain_audit'];self.assertFalse(ok);self.assertEqual(a['centers']['outside_count'],1);self.assertEqual(a['centers']['worst_left_row'],0);self.assertAlmostEqual(a['centers']['left_p'],.1)
        d=fixture(2);d['leaves'][0].q[:,0]=[-.2,6.2];ok,why,m=model_compatibility(d,0,q);self.assertTrue(ok);self.assertGreater(m['domain_audit']['support_interval_endpoints']['absolute_clamping_p'],0.)
    def test_curve_and_segment_tie_regression(self):
        d=fixture(2);q=np.array([[0.,0,0],[3.,.3,0],[6.,0,0]]);d['leaves'][0].q=q.copy()
        old=legacy(d,0,q);new=model_compatibility(d,0,q);self.assertTrue(old[0]);self.assertTrue(new[0])
        for k in ['residual_max','residual_q95','tangent_max','cost','reverse']:self.assertEqual(old[2][k],new[2][k])
    def test_unchanged_parallel_branch_and_gap(self):
        from observation_model import model_group_guard
        from pair_model import model_group_guard as pinned
        self.assertIs(model_group_guard,pinned)
        d=fixture(2,offsets=[0.,.6]);self.assertEqual(model_group_guard(d,d['leaves'][0].q,[0,1])[1],'parallel')
        d=fixture(3);dirs=np.array([[1.,0,0],[-.5,.8660254,0],[-.5,-.8660254,0]])
        d['representatives']['x']=np.concatenate([np.array([.5,1.6,2.8])[:,None]*v for v in dirs]);d['representatives']['t']=np.repeat(dirs,3,axis=0)
        self.assertEqual(model_group_guard(d,d['leaves'][0].q,[0,1,2])[1],'branch')
        d=fixture(2);d['leaves'][0].intervals=np.array([[0.,1.]]);d['leaves'][1].intervals=np.array([[5.,6.]])
        self.assertEqual(model_group_guard(d,d['leaves'][0].q,[0,1])[1],'unsupported_gap')
    def test_unknown_and_seed_pair_preserved(self):
        from observation_model import build_extra_bank
        from pair_delivery import membership_for
        d=fixture(2,length=2.);m=dict(status='RECOVERED',model_key=[1,0,1],seed_pair=[0,1],anchor=0,q=d['leaves'][0].q.tolist(),kind='line')
        hs,_=build_extra_bank(d,dict(carriers=[0,1]),[m]);self.assertTrue(hs);self.assertTrue(all(h['leaves']==[0,1] for h in hs))
        for i,h in enumerate(hs):h['hid']=i
        out,gs,_=membership_for(d,[hs[0]],hs);self.assertTrue(np.all(out['edge_id'][:6]>=0));self.assertTrue(np.all(out['edge_id'][6:]<0))
