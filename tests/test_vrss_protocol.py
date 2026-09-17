"""Small CPU regressions for projection and TRAIN-only M1a input isolation."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
import torch
from src.common import Camera, project
from src.render import render_gbuffer
from src.dt_pull import PullField

spec = importlib.util.spec_from_file_location('m1a_seeds', Path(__file__).resolve().parents[1] / 'scripts/explore/syn/m1a_seeds.py')
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)

class ProtocolTests(unittest.TestCase):
    def test_full_K_pull_per_camera_and_gradient(self):
        Ks = [np.array([[100., 3, 21], [0, 50, 13], [0, 0, 1]]),
              np.array([[80., 0, 19], [0, 70, 14], [0, 0, 1]])]
        cams = [Camera(K, np.eye(4), 40, 48) for K in Ks]
        buf = np.ones((2, 40, 48), np.float32)
        field = PullField(cams, [0, 1], buf, buf, buf, device='cpu')
        p = torch.tensor([[.1, .2, 2]], requires_grad=True)
        uv, _ = field.project(p)
        for v, cam in enumerate(cams):
            expected, _ = project(p.detach().numpy(), cam)
            np.testing.assert_allclose(uv[v].detach(), expected, atol=1e-6)
        self.assertAlmostEqual(uv[0, 0, 1].item(), 18.)
        uv.sum().backward()
        self.assertTrue(torch.isfinite(p.grad).all())
        np.testing.assert_allclose(field.project(p, 1, 2)[0].detach(), uv[1:2].detach())

    def test_gbuffer_uses_fy_and_principal_point(self):
        cam = Camera([[100, 0, 20], [0, 50, 15], [0, 0, 1]], np.eye(4), 40, 48)
        g = {'mu':np.array([[0., .2, 2.]]), 'opacity':np.array([.9]),
             'normal':np.array([[0., 0., 1.]]), 'scale_max':np.array([.001])}
        gb = render_gbuffer(g, np.array([True]), cam, device='cpu')
        self.assertEqual(np.unravel_index(gb['alpha'].numpy().argmax(), (40, 48)), (20, 20))

    def test_explicit_train_indices(self):
        np.testing.assert_array_equal(seed.validate_train_indices([1, 7, 99], 100), [1, 7, 99])
        for bad in (None, [], [5], [0], [100], [-1], [1, 1], [1.0]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                seed.validate_train_indices(bad, 100)

if __name__ == '__main__':
    unittest.main()
