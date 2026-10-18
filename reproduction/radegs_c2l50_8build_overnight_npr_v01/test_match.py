import unittest
from env import np,project,unproject
from matching import visible_state,mutual,downstream
class MatchTests(unittest.TestCase):
 def test_occluded_not_visible_negative(self):
  c=dict(width=5,height=5,fx=100,fy=120,cx=2,cy=2);st=visible_state(np.array([[2,2],[2,2],[2,2],[-1,2]]),np.array([2.,3.,1.,2.]),np.full((5,5),2.),np.ones((5,5)),c);np.testing.assert_array_equal(st,[1,2,4,3])
 def test_invalid_and_low_alpha_unknown(self):
  c=dict(width=5,height=5,fx=100,fy=120);st=visible_state(np.array([[2,2]]),np.array([2.]),np.full((5,5),np.nan),np.zeros((5,5)),c);self.assertEqual(st[0],0)
 def test_colors_are_not_identity(self):self.assertEqual(mutual({1:(2,.9),2:(1,.95)},{2:(1,.9),1:(2,.95)}),[(1,2),(2,1)])
 def test_multiple_blocks_without_visual_pass_no_go(self):self.assertEqual(downstream(3,False),'NO_GO');self.assertEqual(downstream(1,True),'NO_GO')
 def test_full_intrinsics_roundtrip(self):
  c=dict(fx=900,fy=1200,cx=333.5,cy=290,extrinsic=np.eye(4).tolist());uv=np.array([[0.,0.],[500,350]]);z=np.array([2.,3.]);q,zz=project(unproject(uv,z,c),c);np.testing.assert_allclose(q,uv,atol=1e-10);np.testing.assert_allclose(zz,z,atol=1e-10)
if __name__=='__main__':unittest.main()
