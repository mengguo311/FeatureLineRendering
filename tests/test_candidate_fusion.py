import unittest
import numpy as np
from src.common import Camera
from src.candidate_fusion import group,shuffled_ids,match_counts,linelets

CFG=dict(radius_spacing=3.,min_id_weight=.1,min_views=3,min_angle_deg=10.,lift_cos=.35,min_tangent_cos=.7,min_tangent_fraction=.6,pca_weight=.15,max_clusters=30,half_length_spacing=[.75,3.])
class FusionTest(unittest.TestCase):
 def setup_data(self):
  g=dict(mu=np.c_[np.linspace(-.1,.1,20),np.zeros(20),np.full(20,2.)],scale_max=np.full(20,.02))
  cams=[]
  for x in [-1.,0.,1.]:
   w=np.eye(4);w[0,3]=-x;cams.append(Camera([[50.,0,50],[0,50,50],[0,0,1]],w,100,100))
  o=dict(anchor=np.tile([0.,0.,2.],(3,1)),lift=np.tile([1.,0.,0.],(3,1)),plane=np.tile([0.,1.,0.],(3,1)),tangent=np.tile([1.,0.],(3,1)),ids=np.tile([9,10],(3,1)),weights=np.full((3,2),.5),view=np.arange(3),source=np.zeros(3,int),strength=np.ones(3))
  return g,cams,o
 def test_multiview_shared_ids_not_just_position(self):
  g,c,o=self.setup_data();a,s=group(o,g,np.ones(20,bool),c,.01,CFG);self.assertEqual(len(a),1)
  o['ids']=np.arange(6).reshape(3,2);a,s=group(o,g,np.ones(20,bool),c,.01,CFG);self.assertEqual(len(a),0)
 def test_same_view_duplicates_not_support(self):
  g,c,o=self.setup_data();o['view'][:]=0;a,s=group(o,g,np.ones(20,bool),c,.01,CFG);self.assertFalse(a)
 def test_null_counts_and_determinism(self):
  g,c,o=self.setup_data();a=shuffled_ids(o,20,4);b=shuffled_ids(o,20,4)
  np.testing.assert_array_equal(a['ids'],b['ids']);np.testing.assert_array_equal(a['anchor'],o['anchor'])
  r,n=match_counts(o,o,4);self.assertEqual(len(r['anchor']),len(n['anchor']))
 def test_persistent_linelet_tangent(self):
  g,c,o=self.setup_data();a,_=group(o,g,np.ones(20,bool),c,.01,CFG);l=linelets(a)
  self.assertGreater(abs(l['t'][0,0]),.9);self.assertGreater(l['l'][0],0)
if __name__=='__main__':unittest.main()
