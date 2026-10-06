import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from validation import causal_metrics
from binding import backend
from fixtures import cpu_ray_fixture,cpu_weights
from native_ops import deletion
from stage_runtime import guard
import numpy as np
import torch

class CausalContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls): guard('causal_stage_tests')
    def test_frozen_region_metrics(self):
        h=w=25; sdf=np.tile(np.arange(w)-12,(h,1)).astype(float)
        rgb=np.zeros((3,h,w)); alpha=(sdf>0).astype(float)
        changed=rgb.copy();changed[:,:,20]=1
        p=np.column_stack((np.arange(3,22),np.full(19,12.)))
        n=np.tile([0.,1.],(len(p),1))
        out=causal_metrics(rgb,changed,alpha,alpha,sdf,p,n)
        self.assertEqual(out['ring2_mse'],0.)
        self.assertGreater(out['outside4_mse'],0.)
        self.assertEqual(out['alpha_foreground_lost_pixels'],0)

    def test_actual_deletion_changes_T_CPU_truth_and_preserves_input(self):
        m=backend(); f,s=cpu_ray_fixture(m); saved={k:v.clone() for k,v in f.items()}
        rgb,alpha=deletion(m,s,f,np.array([0,2]))
        altered={k:v.clone() for k,v in f.items()};altered['opacities'][[0,2]]=0
        expected=cpu_weights(altered,s).sum(2)
        np.testing.assert_allclose(alpha,expected,atol=2e-6,rtol=0)
        np.testing.assert_allclose(rgb[0],expected,atol=2e-6,rtol=0)
        self.assertTrue(all(torch.equal(f[k],saved[k]) for k in f))

if __name__=='__main__': unittest.main(verbosity=2)
