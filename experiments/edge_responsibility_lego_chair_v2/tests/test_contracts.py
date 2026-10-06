import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from evidence import signed_map, classify_contrast, profile_vector,build_reference
from evaluation import centered_identity, analytic_rays, decide_gates


class Contracts(unittest.TestCase):
    def test_rejected_texture_does_not_feed_main_score(self):
        x=np.indices((64,64))[1]
        rgb=np.repeat(np.where((x//4)%2,.8,.2)[...,None],3,2)
        ref,maps=build_reference(rgb,np.ones((64,64)),'fixture','stripes')
        self.assertEqual(len(ref['samples']),0)
        self.assertGreater(float(maps['broad'].sum()),0)
        self.assertEqual(float(maps['trusted'].sum()),0)

    def test_two_ray_occlusion_and_signed_identity(self):
        r = analytic_rays()
        self.assertAlmostEqual(r['contrast'], .176, places=12)
        self.assertAlmostEqual(r['without_front'], .44, places=12)
        self.assertEqual(r['signed_terms'][0], 0)
        self.assertAlmostEqual(r['pixel_alpha_derivative'], -.44, places=9)
        self.assertAlmostEqual(r['opacity_logit_fd'], -.1056, places=6)
        self.assertLess(r['same_color_response'], 1e-12)

    def test_bilinear_signed_sampler_is_exact_adjoint(self):
        s = {'center': [24.2, 23.7], 'normal': [.6, .8], 'radius': 12, 'samples': 97}
        rng = np.random.default_rng(8)
        im = rng.normal(size=(48, 48, 3))
        m = signed_map(s, (48, 48))
        p = profile_vector(im, s, linear=False)
        t = np.linspace(-12, 12, 97)
        diff = p[t >= 9.6].mean(0) - p[t <= -9.6].mean(0)
        np.testing.assert_allclose((im * m[..., None]).sum((0, 1)), diff, atol=1e-7)
        self.assertAlmostEqual(float(m.sum()), 0, places=6)

    def test_background_and_center_are_required(self):
        dw = np.array([-.1, .3])
        col = np.array([[.1, .2, .3], [.8, .4, .5]])
        bg = np.ones(3)
        u = np.array([1., 0, 0])
        terms, b, identity = centered_identity(dw, col, -.2, bg, u, np.full(3, .5))
        self.assertAlmostEqual(float(terms.sum() + b), .03)
        self.assertAlmostEqual(identity, 0)
        self.assertNotAlmostEqual(float(terms.sum()), .03)

    def test_negative_and_weak_truth_allow_empty(self):
        self.assertEqual(classify_contrast(0, False), 'no_visible_edge')
        self.assertEqual(classify_contrast(.001, True), 'low_contrast')
        self.assertEqual(classify_contrast(.2, True), 'clear_color_transition')
        self.assertEqual(decide_gates([True, False, True])['optimization'], 'NOT_RUN')


if __name__ == '__main__':
    unittest.main()
