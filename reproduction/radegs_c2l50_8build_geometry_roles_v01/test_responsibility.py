import unittest
from env import *
from responsibility import ProjectedSource,measure_difference
class QueryTests(unittest.TestCase):
 def build(self,uv,z,S,op,ids=None,groups=None):return ProjectedSource(np.array(uv,float),np.array(z,float),np.array(S,float),np.array(op,float),np.ones((len(z),3))*.4,np.arange(len(z)) if ids is None else np.array(ids),groups)
 def test_transparent_front_and_layers(self):
  p=self.build([[0,0]]*3,[1,2,3],[np.eye(2)]*3,[0,.5,.5]);r=p.query([0,0]);np.testing.assert_allclose(r['weight'],[0,.5,.25]);self.assertAlmostEqual(r['alpha'],.75);self.assertEqual(r['median'],2)
 def test_ink_excluded(self):
  with self.assertRaises(ValueError):self.build([[0,0]],[1],[np.eye(2)],[.5],groups=np.array([1]))
 def test_far_large_kernel_allN(self):
  p=self.build([[100,0],[0,0]],[2,3],[np.diag([2500,1]),np.eye(2)],[.7,.4],[97,12]);a=p.query([0,0]);b=p.query([0,0],all_N=True);np.testing.assert_array_equal(a['ids'],[97,12]);np.testing.assert_allclose(a['weight'],b['weight'],rtol=0,atol=2e-12)
 def test_same_kernel_both_sides_not_boundary(self):
  p=self.build([[0,0]],[2],[np.eye(2)*10],[.9]);a=p.query([-1,0]);b=p.query([1,0]);d=measure_difference([a],[b]);self.assertAlmostEqual(d['L1'],0);self.assertAlmostEqual(d['overlap'],1)
 def test_source_reorder(self):
  a=self.build([[0,0],[1,0]],[2,3],[np.eye(2)]*2,[.5,.5],[10,11]);b=self.build([[1,0],[0,0]],[3,2],[np.eye(2)]*2,[.5,.5],[11,10]);np.testing.assert_array_equal(a.query([0,0])['ids'],b.query([0,0])['ids']);np.testing.assert_allclose(a.query([0,0])['weight'],b.query([0,0])['weight'],rtol=0,atol=0)
 def test_empty_nonfinite(self):
  p=self.build([[0,0]],[2],[np.eye(2)],[0]);self.assertEqual(p.query([100,100])['alpha'],0)
  with self.assertRaises(ValueError):self.build([[np.nan,0]],[2],[np.eye(2)],[.5])
 def test_full_intrinsics_roundtrip(self):
  c=dict(fx=1100,fy=950,cx=388.3,cy=290.2,extrinsic=[[0,-1,0,.2],[1,0,0,-.3],[0,0,1,.7],[0,0,0,1]]);X=np.array([[.3,.1,2],[-.2,.4,4]]);uv,z=projection(X,c);np.testing.assert_allclose(unproject(uv,z,c),X,rtol=0,atol=1e-14)
if __name__=='__main__':unittest.main(verbosity=2)
