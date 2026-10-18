import unittest
from env import *
from protocol import visibility, transfer, containment, require_source_ids, gate
class Protocol(unittest.TestCase):
 def camera(self):return dict(fx=102.,fy=137.,cx=32.1,cy=24.7,width=70,height=60,extrinsic=np.eye(4).tolist())
 def test_projection_roundtrip(self):
  c=self.camera();uv=np.array([[1.1,4.8],[32.,30.],[50.,40.]]);z=np.array([2.,3.,4.]);x=unproject(uv,z,c);v,d=projection(x,c);np.testing.assert_allclose(v,uv,atol=1e-12);np.testing.assert_allclose(d,z,atol=1e-12)
 def test_occlusion_not_opposition(self):
  c=self.camera();z=np.ones((60,70))*2;a=np.ones_like(z);r=visibility(np.array([[20,20],[21,20],[-1,4],[25,25]]),np.array([2.,4.,2.,1.]),z,a,c)
  self.assertEqual(r.tolist(),[1,2,3,4])
 def test_invalid_unknown_not_background(self):
  c=self.camera();z=np.ones((60,70))*2;a=np.ones_like(z);a[20,20]=.1;r=visibility(np.array([[20,20]]),np.array([2.]),z,a,c);self.assertEqual(int(r[0]),0)
 def test_same_camera_transfer_and_hole(self):
  c=self.camera();m=np.zeros((60,70),bool);m[10:45,10:55]=True;m[20:30,25:35]=False;z=np.ones_like(m,float)*2;a=np.ones_like(z);r,arr=transfer(m,z,a,c,m,z,a,c);self.assertEqual(r['visible_inside_fraction'],1.);self.assertEqual(r['comparable_fraction'],1.)
 def test_all_occluded_no_false_negative(self):
  c=self.camera();m=np.ones((60,70),bool);z=np.ones_like(m,float)*3;a=np.ones_like(z);r,ar=transfer(m,z,a,c,np.zeros_like(m),z*.5,a,c);self.assertIsNone(r['visible_inside_fraction']);self.assertEqual(r['visible'],0)
 def test_containment_all_pixel(self):
  a=np.array([[0,1,2],[0,1,2]]);b=np.array([[0,3,3],[0,3,3]]);self.assertTrue(containment(a,b));b[1,1]=4;self.assertFalse(containment(a,b))
 def test_source_id_not_line_parent(self):
  with self.assertRaises(ValueError):require_source_ids(np.array([0,1]),np.array([0,1]))
  require_source_ids(np.array([0,1]),np.array([0,0]))
 def test_empty_and_unknown_not_go(self):
  self.assertEqual(gate(dict(nonempty=False,engineering=True,visual=True,transfer=True)), 'NO_GO');self.assertEqual(gate(dict(nonempty=True,engineering=False,visual=True,transfer=True)), 'ENGINEERING_INVALID')
if __name__=='__main__':unittest.main()
