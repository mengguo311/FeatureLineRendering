"""Paper equations and native recurrence, CPU only; CUDA integration is separate."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

import torch
import paper_losses as paper

ROOT = Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
VARIANT = ROOT / 'sources/paper_text_variant'


class PaperMathTests(unittest.TestCase):
    def test_eq23_double_sum_camera_z_and_detached_weights(self):
        d = torch.tensor([.4, 1.7, 4.2], dtype=torch.double, requires_grad=True)
        w = torch.tensor([.35, .21, .11], dtype=torch.double, requires_grad=True)
        expected = sum(w[i].detach()*w[j].detach()*(d[i]-d[j])**2
                       for i in range(3) for j in range(3))
        actual = paper.distortion_reference(d, w)
        self.assertTrue(torch.allclose(actual, expected, atol=1e-13))
        gd, gw = torch.autograd.grad(actual, (d, w), allow_unused=True)
        self.assertIsNone(gw)
        self.assertTrue(torch.allclose(gd, 4*w.detach()*(w.detach().sum()*d-(w.detach()*d).sum())))
        self.assertTrue(torch.autograd.gradcheck(lambda z: paper.distortion_reference(z, w), (d,)))
        self.assertTrue(torch.allclose(paper.distortion_reference(3*d, w), 9*actual))
        self.assertTrue(torch.allclose(paper.distortion_reference(d, 2*w), 4*actual))

    def test_eq24_alpha_weighted_identity_and_gradients(self):
        w = torch.tensor([.3, .2], dtype=torch.double, requires_grad=True)
        normals = torch.tensor([[0., 0., 1.], [0., .6, .8]], dtype=torch.double, requires_grad=True)
        target = torch.tensor([0., 0., 1.], dtype=torch.double, requires_grad=True)
        alpha = w.sum().reshape(1, 1, 1)
        mixed = (w[:, None]*normals).sum(0).reshape(3, 1, 1)
        actual = paper.normal_consistency(alpha, mixed, target.reshape(3, 1, 1))
        expected = (w*(1-(normals*target).sum(-1))).sum()
        self.assertTrue(torch.allclose(actual, expected))
        ga = torch.autograd.grad(actual, (w, normals, target), retain_graph=True)
        ge = torch.autograd.grad(expected, (w, normals, target))
        for a, e in zip(ga, ge):
            self.assertTrue(torch.allclose(a, e))
        self.assertAlmostEqual(actual.item(), .04)
        self.assertTrue(torch.autograd.gradcheck(paper.normal_consistency,
                          (alpha.detach().requires_grad_(), mixed.detach().requires_grad_(),
                           target.reshape(3,1,1).detach().requires_grad_())))

    def test_exact_schedule(self):
        self.assertEqual(sum(paper.geometry_active(i) for i in range(1,30001)), 15000)
        self.assertFalse(paper.geometry_active(15000))
        self.assertTrue(paper.geometry_active(15001))
        with self.assertRaises(ValueError):
            paper.geometry_active(0)

    def test_median_normal_uses_only_selected_depth_and_camera_z_rays(self):
        d = torch.full((1,5,5), 2., dtype=torch.double, requires_grad=True)
        normal = paper.median_depth_normal(d, 10., 11.)
        self.assertEqual(tuple(normal.shape), (3,5,5))
        # Matches inherited C24 row-cross-column camera orientation.
        self.assertTrue(torch.allclose(normal[:,2,2], torch.tensor([0.,0.,-1.],dtype=torch.double)))
        self.assertEqual(normal[:,0,:].abs().sum().item(), 0.)
        self.assertTrue(torch.autograd.gradcheck(lambda z: paper.median_depth_normal(z,10.,11.), (d,)))


class NativeHostTests(unittest.TestCase):
    def test_same_header_used_in_cuda_has_double_sum_forward_and_backward(self):
        header = VARIANT / 'submodules/diff-gaussian-rasterization/cuda_rasterizer/paper_distortion.cuh'
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'test.cpp'
            source.write_text(f'''#include "{header}"
extern "C" double forward(double d, double w, double m, double s, double q) {{
 return paper_distortion_increment(d,w,m,s,q); }}
extern "C" double backward(double d, double w, double m, double s) {{
 return paper_distortion_gradient(d,w,m,s); }}
''')
            lib = Path(tmp)/'test.so'
            subprocess.run(['g++','-shared','-fPIC','-O2',str(source),'-o',str(lib)],check=True)
            dll = ctypes.CDLL(str(lib))
            dll.forward.argtypes = [ctypes.c_double]*5
            dll.backward.argtypes = [ctypes.c_double]*4
            dll.forward.restype = dll.backward.restype = ctypes.c_double
            depths, weights = [.4,1.7,4.2], [.35,.21,.11]
            result = mass = moment = second = 0.
            for d,w in zip(depths,weights):
                result += dll.forward(d,w,mass,moment,second)
                mass += w
                moment += w*d
                second += w*d*d
            oracle = sum(w*v*(d-e)**2 for d,w in zip(depths,weights) for e,v in zip(depths,weights))
            self.assertAlmostEqual(result, oracle, places=12)
            for i,(d,w) in enumerate(zip(depths,weights)):
                eps=1e-5
                def value(z):
                    ds=depths.copy();ds[i]=z
                    return sum(a*b*(x-y)**2 for x,a in zip(ds,weights) for y,b in zip(ds,weights))
                self.assertAlmostEqual(dll.backward(d,w,mass,moment),
                                       (value(d+eps)-value(d-eps))/(2*eps),places=8)


if __name__ == '__main__':
    unittest.main(verbosity=2)
