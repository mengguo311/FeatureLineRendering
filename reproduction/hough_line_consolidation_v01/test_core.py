from pilotio import *
import unittest
from core import fit_line, support_intervals, verify_gap, associate_hypotheses, eligible_fragment

class ScientificContract(unittest.TestCase):
    def test_no_evidence_is_never_confirmation(self):
        self.assertEqual(verify_gap([])['status'],'inferred')
        self.assertFalse(verify_gap([])['render_gap'])
    def test_unsupported_middle_splits_even_one_hypothesis(self):
        x=np.r_[np.arange(12.),np.arange(20.,32.)]
        intervals=support_intervals(x,1.)
        self.assertEqual(len(intervals),2)
        self.assertLess(intervals[0][1],intervals[1][0])
    def test_crossing_membership_not_destructively_consumed(self):
        t=np.arange(-10.,11.); x=np.vstack([np.c_[t,t*0,t*0],np.c_[t*0,t,t*0]])
        hs=[(np.zeros(3),np.array([1.,0,0])),(np.zeros(3),np.array([0.,1,0]))]
        memberships=associate_hypotheses(x,hs,.1)
        self.assertEqual(int(memberships[10].sum()),2)
        self.assertEqual(int(memberships[31].sum()),2)
    def test_curve_not_eligible_for_global_straightening(self):
        t=np.linspace(-1.5,1.5,100); x=np.c_[20*np.cos(t),20*np.sin(t),t*0]
        self.assertFalse(eligible_fragment(x,1.))
    def test_orthogonal_fit_rotated_line(self):
        d=unit(np.array([1.,2.,3.])); x=np.arange(20.)[:,None]*d
        a,b=fit_line(x,np.ones(len(x)),1.)
        self.assertLess(np.linalg.norm(np.cross(x-a,b),axis=1).max(),1e-10)
if __name__=='__main__': unittest.main(verbosity=2)
