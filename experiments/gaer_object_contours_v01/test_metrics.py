import unittest,json
import numpy as np
import runtime as rt
class MetricsTests(unittest.TestCase):
 def test_profile_config_and_unmasked_stray(self):
  from pipeline import quality_config
  from silhouette import evidence,metrics
  cfg=json.loads((rt.ART/'PROTOCOL.json').read_text());a=np.zeros((80,80),np.float32);a[10:70,10:70]=1;e=evidence(a,cfg['silhouette']);ink=e['target'].copy();ink[35:40,35:40]=1;m,_=metrics(ink,e,quality_config(cfg))
  self.assertEqual(m['interior_threshold_pixels'],25);self.assertGreater(m['interior_ink_mass_fraction'],0);self.assertGreater(m['boundary_coverage'],.95)
if __name__=='__main__':unittest.main()
