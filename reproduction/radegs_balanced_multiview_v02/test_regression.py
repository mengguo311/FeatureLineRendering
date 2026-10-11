import unittest,numpy as np
from pathlib import Path
import multiview as m
OLD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/spatial_rgb_gaussian_demo_v01')
class BaselineRegression(unittest.TestCase):
 def test_exact_old_three_scene_balanced(self):
  for scene in ['scan24','scan65','scan63']:
   s=dict(np.load(OLD/'results_v1'/scene/'source_samples.npz'));old=dict(np.load(OLD/'results_v2'/scene/'balanced_gaussians.npz'));oldp=dict(np.load(OLD/'results_v2'/scene/'balanced_provenance.npz'));asset,prov=m.assemble_asset(s,s['votes'])
   self.assertEqual(len(asset['means']),len(old['means']))
   for k in old:
    atol=1e-7 if k=='opacity' else 1e-9;np.testing.assert_allclose(asset[k],old[k],rtol=0,atol=atol,err_msg=scene+':'+k)
   np.testing.assert_array_equal(prov['source_to_asset'],oldp['source_to_balanced_id']);np.testing.assert_array_equal(prov['source_weight'],oldp['source_weight'])
if __name__=='__main__':unittest.main(verbosity=2)
