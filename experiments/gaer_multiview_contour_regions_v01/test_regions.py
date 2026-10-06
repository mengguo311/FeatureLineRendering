import unittest,numpy as np
from regions import build_region
class RegionsTest(unittest.TestCase):
 def test_anchored_fixed_and_false_bridge(self):
  xyz=np.array([[-.5,0,0],[-.48,0,0],[.5,0,0]],np.float32)
  m=dict(xyz=xyz,scales=np.ones((3,3),np.float32)*.015,rotations=np.tile([1,0,0,0],(3,1)))
  s=dict(score=np.ones(3),distinct_views=np.ones(3,dtype=np.uint8))
  x=build_region(m,np.arange(3),s,1.0,[],[],grid_resolution=64)
  self.assertGreater(len(x['faces']),0);self.assertEqual(x['component_count'],2)
  self.assertTrue(set(np.unique(x['vertex_anchor_ids'])).issubset({0,1,2}))
  self.assertLess(x['vertex_displacement'].max(),.12)
  self.assertTrue(np.isfinite(x['vertices']).all())
if __name__=='__main__':unittest.main()
