import unittest
from env import *
from subject import binary_cut, energy, seeds, consensus, depth_component, gated_stage
class Core(unittest.TestCase):
 def test_cut_exact_enum(self):
  d0=np.array([1.,0.,4.,1.]);d1=np.array([0.,3.,0.,2.]);i=np.array([0,1,2]);j=i+1;w=np.array([.2,2.,.8]);m=binary_cut(d0,d1,i,j,w);e=energy(m,d0,d1,i,j,w)
  self.assertAlmostEqual(e,min(energy(np.array([(k>>b)&1 for b in range(4)],bool),d0,d1,i,j,w) for k in range(16)),places=10)
 def test_empty_subject_refuses(self):
  with self.assertRaises(ValueError):seeds(np.ones((40,50,3)),np.ones((40,50)),np.ones((40,50)),0)
 def test_border_object_not_background(self):
  x=np.ones((60,60,3));x[10:50,:40]=.2;a=np.ones((60,60));fg,bg,_,_=seeds(x,a,a,0);self.assertFalse(bg[30,0]);self.assertTrue(fg.any())
 def test_disconnected_thin_and_holes(self):
  m=np.zeros((30,30),bool);m[5:25,5:25]=True;m[10:20,10:20]=False;m[2,2:25]=True
  out=consensus([m,m,m],np.ones_like(m,float),np.ones_like(m,float),np.ones_like(m,float)*2)
  np.testing.assert_array_equal(out['candidate'],m);self.assertFalse(out['candidate'][15,15]);self.assertTrue(out['candidate'][2,7])
 def test_unknown_not_foreground_false(self):
  m=np.ones((4,4),bool);a=np.ones((4,4));a[0,0]=.2;z=np.ones((4,4));z[1,1]=np.nan;o=consensus([m,m,m],a,z,np.ones((4,4))*2);self.assertTrue(o['unknown'][0,0] and o['unknown'][1,1]);self.assertTrue(o['candidate'].all())
 def test_no_alpha_semantics(self):
  x=np.ones((60,60,3))*.5;x[15:45,15:45]=.9;a=np.ones((60,60));fg,bg,_,_=seeds(x,a,a,0);self.assertTrue(bg.any());self.assertFalse(fg.all())
 def test_depth_continuity_not_subject(self):
  z=np.ones((25,25))*2;a=np.ones_like(z);c=dict(fx=100,fy=110);o=depth_component(z,a,c);self.assertTrue(o.all())
 def test_depth_step_not_global_nearcut(self):
  z=np.ones((31,31))*2;z[:,23:]=5;a=np.ones_like(z);o=depth_component(z,a,dict(fx=100,fy=100));self.assertTrue(o[:, :23].all());self.assertFalse(o[:,23:].any())
 def test_parent_gate_not_run(self):
  self.assertEqual(gated_stage('NO_GO'),'NOT_RUN');self.assertEqual(gated_stage('ENGINEERING_INVALID'),'NOT_RUN');self.assertEqual(gated_stage('GO'),'READY')
if __name__=='__main__':unittest.main()
