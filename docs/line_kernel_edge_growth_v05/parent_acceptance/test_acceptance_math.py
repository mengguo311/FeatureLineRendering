import unittest,numpy as np
from acceptance_math import project,interval_union
class MathTests(unittest.TestCase):
 def test_finite_line_projection(self):
  s,d,t=project(np.array([[-1.,1,0],[5,-1,0],[2,2,0]]),np.array([[0.,0,0],[4,0,0]]))
  np.testing.assert_allclose(s,[0,4,2]);np.testing.assert_allclose(d,[np.sqrt(2),np.sqrt(2),2]);np.testing.assert_allclose(t,[[1,0,0]]*3)
 def test_corner_tie_selects_first_segment(self):
  s,d,t=project(np.array([[1.,1,0],[2,1,0]]),np.array([[0.,0,0],[2,0,0],[2,2,0]]))
  np.testing.assert_allclose(s,[1,3]);np.testing.assert_allclose(d,[1,0]);np.testing.assert_allclose(t,[[1,0,0],[0,1,0]])
 def test_union_deduplicates_without_filling_gaps(self):
  a,l,r,g,total=interval_union(np.array([[0.,2],[3,1],[5,6],[6,6]]));np.testing.assert_allclose(a,[[0,3],[5,6]]);self.assertEqual((l,r,g,total),(4,3,2,2))
 def test_union_numerical_epsilon(self):
  a,l,r,g,total=interval_union(np.array([[0.,1],[1+0.5e-8,2]]));np.testing.assert_allclose(a,[[0,2]]);self.assertEqual((l,r,g,total),(2,2,0,0))
if __name__=='__main__':unittest.main(verbosity=2)
