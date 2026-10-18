import unittest
from env import *
from hierarchy import hierarchical, merge_labels, mutual_match
from protocol import containment
class Hierarchy(unittest.TestCase):
 def test_nested_merge(self):
  lab=np.array([[1,1,2,2,3,3]]);out=merge_labels(lab,np.array([[1,2],[2,3]]),np.array([.3,1.4]),[.5,1,2]);self.assertTrue(containment(out[0],out[1]));self.assertTrue(containment(out[1],out[2]));self.assertEqual(len(np.unique(out[-1])),1)
 def test_depth_step_split_and_hole_retained(self):
  n=60;rgb=np.ones((n,n,3))*.4;m=np.zeros((n,n),bool);m[5:55,5:55]=True;m[20:28,20:28]=False;z=np.ones((n,n))*2;z[:,30:]=4;a=m.astype(float);o=hierarchical(rgb,z,a,m,dict(fx=100,fy=100),'rgb_depth')
  for lab in o['levels']:
   self.assertTrue((lab[m]>0).all());self.assertTrue((lab[~m]==0).all());self.assertNotEqual(lab[35,15],lab[35,45])
 def test_thin_disconnected_component_has_marker(self):
  m=np.zeros((72,72),bool);m[20:60,20:60]=True;m[3,3:20]=True;x=np.ones((72,72,3))*.4;o=hierarchical(x,np.ones((72,72))*2,m.astype(float),m,dict(fx=100,fy=100),'rgb_depth');self.assertTrue((o['levels'][0][m]>0).all());self.assertGreater(o['markers'][3].max(),0)
 def test_many_to_one_not_all_matching(self):
  ab={1:(3,.9),2:(3,.9)};ba={3:(1,.9)};m=mutual_match(ab,ba,.75);self.assertEqual(m,[(1,3)])
 def test_empty_refused(self):
  with self.assertRaises(ValueError):hierarchical(np.zeros((20,20,3)),np.ones((20,20)),np.ones((20,20)),np.zeros((20,20),bool),dict(fx=100,fy=100),'rgb_depth')
if __name__=='__main__':unittest.main()
