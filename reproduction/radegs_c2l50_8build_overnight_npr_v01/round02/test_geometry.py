from env import *
import unittest
from geometry import correspond, normal_evidence, local_edges
def camera():return dict(fx=80.,fy=100.,cx=4.,cy=4.,width=9,height=9,extrinsic=np.eye(4).tolist())
class TestGeometry(unittest.TestCase):
 def test_full_camera(self):
  c=camera();uv=np.array([[2.,3],[6,7]]);X=unproject(uv,np.array([2.,3]),c);q,z=project(X,c);np.testing.assert_allclose(q,uv,atol=1e-12);np.testing.assert_allclose(z,[2,3])
 def test_visible_and_occluded(self):
  c=camera();uv=np.array([[4,4]]);z=np.full((9,9),2.);a=np.ones_like(z);state,target=correspond(unproject(uv,[2],c),uv,c,c,z,a);self.assertEqual(state[0],1)
  state,_=correspond(unproject(uv,[3],c),uv,c,c,z,a);self.assertEqual(state[0],2)
  state,_=correspond(unproject(uv,[1],c),uv,c,c,z,a);self.assertEqual(state[0],4)
 def test_unknown_and_outside(self):
  c=camera();z=np.full((9,9),2.);uv=np.array([[4,4],[20,20]]);s,_=correspond(unproject(uv,[2,2],c),uv,c,c,z,np.zeros_like(z));np.testing.assert_array_equal(s,[0,3])
 def test_cross_layer_not_edge(self):
  c=camera();z=np.ones((9,9))*2;z[:,5:]=3;m=np.ones_like(z,bool);uv=np.c_[np.tile(np.arange(9),9),np.repeat(np.arange(9),9)];X=unproject(uv,z.ravel(),c);i,j,d=local_edges(m,X,z.ravel()/np.sqrt(c['fx']*c['fy']));self.assertFalse(np.any((uv[i,0]==4)&(uv[j,0]==5)))
 def test_thin_leaf_hole_not_filled(self):
  m=np.zeros((9,9),bool);m[4,1:8]=1;m[4,4]=0;uv=np.c_[np.nonzero(m)[1],np.nonzero(m)[0]];X=unproject(uv,np.ones(len(uv))*2,camera());i,j,d=local_edges(m,X,np.ones(len(X))*.022);self.assertEqual(len(i),4)
 def test_sloped_plane_normal(self):
  c=camera();y,x=np.mgrid[:9,:9];z=2/(1+.2*(x-4)/80);ar=normal_evidence(z,np.ones_like(z),c,[0,0,1]);self.assertTrue(ar['valid'][4,4]);self.assertLess(ar['planarity_p'][4,4],1e-9);self.assertAlmostEqual(ar['angle'][4,4],np.degrees(np.arctan(.2)),places=7)
 def test_step_normal_unknown(self):
  c=camera();z=np.ones((9,9))*2;z[:,5:]=3;ar=normal_evidence(z,np.ones_like(z),c,[0,0,1]);self.assertFalse(ar['valid'][4,4])
if __name__=='__main__':unittest.main()
