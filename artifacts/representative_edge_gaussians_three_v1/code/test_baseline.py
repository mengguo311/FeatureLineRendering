import unittest
import numpy as np
import legacy_core as c
class HistoricalA(unittest.TestCase):
 def test_view_mass_normalization_and_ties(self):
  cfg=dict(min_visible_views=2,min_raw_visibility_mass=1,tiers_percent=[1,3,10],fixed_frame_ids=[1,14])
  ss=[]
  for mass,den,num in [(10,[2,2,0],[[2,0,0,2],[1,0,0,1],[0,0,0,0]]),(100,[20,20,0],[[0,0,0,0],[10,0,0,10],[0,0,0,0]])]:
   d=np.array(den,dtype=float);s=dict(denominator=d,numerator=np.array(num,dtype=float),side_numerator=np.zeros((3,4)),raw_cached_mass=mass,topk=4,split='F')
   for k in ('positive_mass','nonedge_mass','soft_nonedge_mass'):s[k]=np.zeros((3,4))
   for k in ('front_mass','deeper_mass','foreground_mass','interior_mass','outline_mass'):s[k]=d.copy()
   ss.append(s)
  a=c.aggregate_views(ss,cfg);np.testing.assert_allclose(a['baseline_union'],[.5,.5,0]);self.assertEqual(a['eligible'].tolist(),[True,True,False]);self.assertTrue(a['unknown'][2]);self.assertEqual(c.rank_tiers(a,cfg,'baseline_union')['1'].tolist(),[0])
if __name__=='__main__':unittest.main(verbosity=2)
