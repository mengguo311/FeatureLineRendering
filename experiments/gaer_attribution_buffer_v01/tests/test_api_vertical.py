"""First vertical acceptance test: run against stock for durable RED, patched for GREEN."""
import os
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from runtime import guard
from native import load_backend
import torch

class VerticalAPI(unittest.TestCase):
    def test_real_gpu_attribution_api(self):
        guard('vertical_api')
        m = load_backend(os.environ.get('GAER_TEST_BACKEND', 'patched'))
        eye = torch.eye(4, device='cuda')
        s = m.GaussianRasterizationSettings(1, 1, 1., 1., torch.zeros(3, device='cuda'),
                                            1., eye, eye, 0, torch.zeros(3, device='cuda'), False, False)
        r = m.GaussianRasterizer(s)(means3D=torch.tensor([[0., 0., 1.]], device='cuda'),
            means2D=torch.zeros(1, 3, device='cuda'), opacities=torch.tensor([[.5]], device='cuda'),
            colors_precomp=torch.ones(1, 3, device='cuda'), scales=torch.ones(1, 3, device='cuda') * .1,
            rotations=torch.tensor([[1., 0., 0., 0.]], device='cuda'), attribution=True)
        torch.cuda.synchronize()
        self.assertEqual(r.gaussian_ids.shape, (1, 1, 8))
        self.assertEqual(r.gaussian_ids.dtype, torch.int32)
        self.assertEqual(r.gaussian_weights.dtype, torch.float32)
        self.assertEqual(r.gaussian_ids[0, 0].cpu().tolist(), [0] + [-1] * 7)
        self.assertEqual(r.gaussian_weights[0, 0].cpu().tolist(), [.5] + [0.] * 7)
        self.assertEqual(float(r.all_contribution_sum[0, 0]), .5)
        self.assertEqual(float(r.final_T[0, 0]), .5)

if __name__ == '__main__':
    unittest.main(verbosity=2)
