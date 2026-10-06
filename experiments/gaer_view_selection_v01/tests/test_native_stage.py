"""New-stage full-visibility feature gradient and independent CPU-ray contracts."""
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from binding import backend
from native_ops import feature_mass, render_features
from fixtures import cpu_ray_fixture, flat_fixture, cpu_weights
from stage_runtime import guard
import numpy as np
import torch

class NativeStage(unittest.TestCase):
    @classmethod
    def setUpClass(cls): guard('native_stage_tests')
    def test_full_visibility_matches_all_CPU_accepted_rays(self):
        m=backend(); f,s=cpu_ray_fixture(m)
        expected=cpu_weights(f,s)
        mass,alpha=feature_mass(m,s,f)
        np.testing.assert_allclose(mass,expected.sum((0,1)),rtol=2e-5,atol=2e-6)
        np.testing.assert_allclose(alpha,expected.sum(2),rtol=0,atol=2e-6)
        self.assertTrue(np.all(mass>=0))
        # Exact full-model-T selection features, not a subset with changed T.
        chosen=np.array([0,2]); got=render_features(m,s,f,chosen)
        np.testing.assert_allclose(got,expected[:,:,chosen].sum(2),atol=2e-6,rtol=0)

    def test_flat_texture_is_independent_of_weights(self):
        m=backend(); a,s,truth=flat_fixture(m,False); b,_,_=flat_fixture(m,True)
        ra=m.GaussianRasterizer(s)(**a,attribution=True,K=8)
        rb=m.GaussianRasterizer(s)(**b,attribution=True,K=8)
        self.assertTrue(torch.equal(ra.gaussian_ids,rb.gaussian_ids))
        self.assertTrue(torch.equal(ra.gaussian_weights,rb.gaussian_weights))
        self.assertGreater(float((ra.rgb-rb.rgb).abs().max()),.05)
        # Within a constant coplanar surface, smooth individual footprints vary.
        self.assertGreater(float((ra.gaussian_weights[32,30]-ra.gaussian_weights[32,34]).abs().sum()),.001)
        self.assertEqual(truth['interior_geometry_edges'],0)

if __name__=='__main__': unittest.main(verbosity=2)
