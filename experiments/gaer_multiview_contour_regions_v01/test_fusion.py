import unittest,numpy as np
from fusion import fuse, evidence
class FusionTest(unittest.TestCase):
 def test_distinct_views_and_lowmass(self):
  mass=np.array([[2.,.00001,4],[3,.00001,5]])
  rim=np.array([[1.,.00001,0],[0,.00001,3.]])
  x=fuse(mass,rim,['r_7','r_33'])
  self.assertEqual(x['distinct_views'].tolist(),[1,0,1])
  self.assertEqual(x['high'].tolist(),[True,False,True])
  with self.assertRaises(ValueError):fuse(mass,rim,['r_7','r_7'])
 def test_holes_not_filled(self):
  a=np.zeros((41,41));a[5:36,5:36]=1;a[15:26,15:26]=0
  x=evidence(a);self.assertTrue(x['holes'][20,20]);self.assertTrue(x['boundary'][15,14]);self.assertFalse(x['foreground'][20,20])
 def test_map_mass(self):
  a=np.zeros((41,41));a[10:31,10:31]=1;x=evidence(a)
  self.assertEqual(x['maps'].shape,(41,41,3));self.assertTrue(np.isfinite(x['maps']).all())
if __name__=='__main__':unittest.main()
