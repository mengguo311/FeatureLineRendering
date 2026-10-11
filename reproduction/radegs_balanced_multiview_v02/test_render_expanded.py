import unittest
import numpy as np
import core
import render_expanded as r
class RenderTests(unittest.TestCase):
 def test_shared_projection_matches_reference_each_arm(self):
  c={'width':31,'height':25,'fx':25.,'fy':24.,'extrinsic':np.eye(4).tolist()}
  a={'means':np.array([[0.,0.,2.],[.05,0.,3.],[-.1,.2,2.5]]),'covariance':np.eye(3)[None]*np.array([.03,.04,.06])[:,None,None]**2,'opacity':np.array([.7,.9,.5]),'colors':np.zeros((3,3))}
  d=np.full((25,31),2.6);alpha=np.ones_like(d)
  out=r.render_pair(a,c,24,d,alpha)
  np.testing.assert_array_equal(out['balanced'],core.render(a,c,d,alpha))
  b=dict(a);b['opacity']=-np.expm1(np.log1p(-a['opacity'])*3/24)
  np.testing.assert_array_equal(out['density_compensated'],core.render(b,c,d,alpha))
 def test_three_view_identity_and_unknown_occlusion(self):
  c={'width':15,'height':15,'fx':14.,'fy':14.,'extrinsic':np.eye(4).tolist()}
  a={'means':np.array([[0.,0.,2.]]),'covariance':np.eye(3)[None]*.01,'opacity':np.array([.8]),'colors':np.zeros((1,3))}
  out=r.render_pair(a,c,3)
  np.testing.assert_array_equal(out['balanced'],out['density_compensated'])
  self.assertLess(out['balanced'][7,7,0],.21)
  hidden=r.render_pair(a,c,3,np.ones((15,15)),np.ones((15,15)))
  np.testing.assert_array_equal(hidden['balanced'],np.ones((15,15,3),np.float32))
if __name__=='__main__':unittest.main()
