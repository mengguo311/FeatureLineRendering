"""Actual CUDA acceptance checks with independent FP32 analytic fixtures."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from runtime import ART, EXP, OUT, atomic_json, guard, sha
from native import load_backend
import numpy as np
import torch

PROTOCOL = json.loads((EXP / 'protocol.json').read_text())
TOL = PROTOCOL['absolute_fp32_tolerance']
FIXTURES = json.loads((EXP / 'tests/fixtures.json').read_text())
EVIDENCE = {'protocol_sha256': sha(EXP / 'protocol.json'), 'analytic': {}, 'gradients': {}, 'training': {}}

def settings(m, h=1, w=1, degree=0, bg=(.2, .3, .4)):
    eye = torch.eye(4, device='cuda')
    return m.GaussianRasterizationSettings(h, w, 1., 1., torch.tensor(bg, device='cuda'),
                    1., eye, eye, degree, torch.zeros(3, device='cuda'), False, False)

def center_fixture(name):
    spec = FIXTURES[name]
    n = len(spec['depths'])
    xyz = torch.zeros(n, 3, device='cuda')
    xyz[:, 2] = torch.tensor(spec['depths'], device='cuda')
    rot = torch.zeros(n, 4, device='cuda'); rot[:, 0] = 1.
    return dict(means3D=xyz, means2D=torch.zeros_like(xyz),
                opacities=torch.tensor(spec['opacities'], device='cuda').reshape(n, 1),
                scales=torch.full((n, 3), .12, device='cuda'), rotations=rot,
                colors_precomp=torch.full((n, 3), .6, device='cuda'))

def oracle(name):
    """Centered H=W=1 splats have power=0; no Gaussian falloff approximation."""
    spec = FIXTURES[name]; T = np.float32(1); total = np.float32(0); accepted = []
    for i in sorted(range(len(spec['depths'])), key=lambda i: (spec['depths'][i], i)):
        if np.float32(spec['depths'][i]) <= np.float32(.2):
            continue
        alpha = min(np.float32(.99), np.float32(spec['opacities'][i]))
        if alpha < np.float32(1 / 255):
            continue
        next_T = np.float32(T * np.float32(np.float32(1) - alpha))
        if next_T < np.float32(.0001):
            break
        weight = np.float32(T * alpha)
        accepted.append((i, float(weight)))
        total = np.float32(total + weight); T = next_T
    return sorted(accepted, key=lambda v: -v[1]), float(total), float(T)

def render(m, fixture, attribution=False, K=8, h=1, w=1, degree=0):
    kw = dict(attribution=True, K=K) if attribution else {}
    return m.GaussianRasterizer(settings(m, h, w, degree))(**fixture, **kw)

def maxerr(a, b):
    return float((a - b).abs().max()) if a.numel() else 0.

def gradient_fixture(mode='sh'):
    # One pixel avoids unordered inter-pixel atomic gradient reductions. All
    # parameter groups influence a nontrivial loss away from alpha/color clamps.
    xyz = torch.tensor([[.08, -.04, .7], [-.12, .06, 1.1], [.1, .1, 1.6]], device='cuda')
    f = dict(means3D=xyz, means2D=torch.zeros_like(xyz),
             opacities=torch.tensor([[.22], [.31], [.18]], device='cuda'),
             scales=torch.tensor([[.16, .09, .12], [.11, .18, .08], [.14, .10, .2]], device='cuda'),
             rotations=torch.tensor([[.9, .1, .2, .3], [.8, .2, -.3, .1], [.85, -.1, .15, .25]], device='cuda'))
    f['rotations'] = torch.nn.functional.normalize(f['rotations'], dim=1)
    if mode == 'sh':
        coeff = torch.arange(3 * 16 * 3, device='cuda', dtype=torch.float32).reshape(3, 16, 3)
        f['shs'] = .015 * torch.sin(coeff * .31)
    else:
        f['colors_precomp'] = torch.tensor([[.4, .6, .3], [.7, .2, .5], [.25, .45, .65]], device='cuda')
    return {k: v.detach().clone().requires_grad_(True) for k, v in f.items()}

def loss(rgb):
    return ((rgb - torch.tensor([.11, .73, .37], device='cuda')[:, None, None]) ** 2
            * torch.tensor([.6, 1.3, .9], device='cuda')[:, None, None]).sum() + .07 * rgb.prod()

class NativeChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        guard('native_tests')
        torch.set_num_threads(2)
        cls.actual = load_backend('actual')
        cls.original = load_backend('original')
        cls.patched = load_backend('patched')

    def test_analytic_accepted_weights_ids_and_mass(self):
        for name in FIXTURES:
            with self.subTest(fixture=name):
                f = center_fixture(name); expected, total, T = oracle(name)
                r = render(self.patched, f, True, K=32)
                ids = r.gaussian_ids.cpu().numpy()[0, 0]
                weights = r.gaussian_weights.cpu().numpy()[0, 0]
                want_ids = np.full(32, -1, np.int32); want_weights = np.zeros(32, np.float32)
                for k, (i, v) in enumerate(expected):
                    want_ids[k], want_weights[k] = i, v
                np.testing.assert_array_equal(ids, want_ids)
                np.testing.assert_allclose(weights, want_weights, atol=TOL, rtol=0)
                self.assertLessEqual(abs(float(r.all_contribution_sum) - total), TOL)
                self.assertLessEqual(abs(float(r.final_T) - T), TOL)
                self.assertLessEqual(abs(float(r.all_contribution_sum) - float(r.accumulated_alpha)), TOL)
                for t in (r.gaussian_weights, r.all_contribution_sum, r.final_T):
                    self.assertTrue(torch.isfinite(t).all()); self.assertFalse(t.requires_grad)
                rgb_actual, rad_actual = render(self.actual, f)
                rgb_original, rad_original = render(self.original, f)
                rgb_off, rad_off = render(self.patched, f)
                for rgb, rad in [(rgb_original, rad_original), (rgb_off, rad_off), (r.rgb, r.radii)]:
                    self.assertTrue(torch.equal(rgb_actual, rgb), (name, maxerr(rgb_actual, rgb)))
                    self.assertTrue(torch.equal(rad_actual, rad))
                EVIDENCE['analytic'][name] = dict(ids=ids.tolist(), weights=weights.tolist(),
                    expected_accepted=expected, all_sum=float(r.all_contribution_sum), final_T=float(r.final_T),
                    sum_alpha_error=abs(float(r.all_contribution_sum) - float(r.accumulated_alpha)), rgb_max_error=0.)
        # Rear high opacity has lower actual weight than the front's lower opacity.
        self.assertEqual(EVIDENCE['analytic']['occlusion']['ids'][:3], [1, 2, 0])
        self.assertEqual(EVIDENCE['analytic']['ties']['ids'][:2], [1, 0])
        self.assertEqual(EVIDENCE['analytic']['early_termination']['ids'][:3], [0, 1, -1])

    def test_K_prefix_monotonic_layout_cpu_and_default(self):
        f = center_fixture('center_many')
        prev = None; records = []
        for K in (1, 4, 8, 16, 32):
            r = render(self.patched, f, True, K=K)
            self.assertEqual(r.gaussian_ids.dtype, torch.int32)
            self.assertEqual(r.gaussian_weights.dtype, torch.float32)
            self.assertEqual(tuple(r.gaussian_ids.shape), (1, 1, K))
            self.assertTrue(r.gaussian_ids.is_contiguous() and r.gaussian_weights.is_contiguous())
            self.assertTrue(torch.all(r.gaussian_weights[..., 1:] <= r.gaussian_weights[..., :-1]))
            self.assertEqual(r.gaussian_ids.cpu().numpy().dtype, np.int32)
            self.assertEqual(r.gaussian_weights.cpu().numpy().dtype, np.float32)
            mass = float(r.gaussian_weights.sum())
            if prev:
                self.assertTrue(torch.equal(prev.gaussian_ids, r.gaussian_ids[..., :prev.gaussian_ids.shape[-1]]))
                self.assertTrue(torch.equal(prev.gaussian_weights, r.gaussian_weights[..., :prev.gaussian_weights.shape[-1]]))
                self.assertGreaterEqual(mass, float(prev.gaussian_weights.sum()))
            records.append(dict(K=K, topk_mass=mass, full_alpha=float(r.accumulated_alpha)))
            prev = r
        default = self.patched.GaussianRasterizer(settings(self.patched))(**f, attribution=True)
        self.assertEqual(default.gaussian_ids.shape[-1], 8)
        for bad in (-3, 0, 33, 1.5, True):
            with self.assertRaises(ValueError):
                render(self.patched, f, True, K=bad)
        # Arbitrary bounded positive K, rather than only specialized powers of two.
        self.assertEqual(render(self.patched, f, True, K=7).gaussian_ids.shape[-1], 7)
        EVIDENCE['K_checks'] = records

    def test_edge_pixels_empty_tiles_and_culling(self):
        f = center_fixture('near_clip')
        # Small footprint and actual projection produce empty edge pixels in 33x35.
        f['scales'].fill_(.005)
        r = render(self.patched, f, True, K=4, h=33, w=35)
        bg = r.accumulated_alpha == 0
        self.assertTrue(bg.any())
        self.assertTrue(torch.all(r.gaussian_ids[bg] == -1))
        self.assertTrue(torch.all(r.gaussian_weights[bg] == 0))
        self.assertTrue(torch.all(r.final_T[bg] == 1))
        self.assertTrue(torch.all(r.all_contribution_sum[bg] == 0))
        self.assertLessEqual(maxerr(r.all_contribution_sum, r.accumulated_alpha), TOL)
        original, _ = render(self.actual, f, h=33, w=35)
        self.assertTrue(torch.equal(original, r.rgb))
        # A model with zero primitives inherits pinned stock's zero RGB special case.
        empty = render(self.patched, center_fixture('empty_model'), True, K=4, h=3, w=5)
        self.assertTrue(torch.all(empty.gaussian_ids == -1)); self.assertTrue(torch.all(empty.final_T == 1))
        EVIDENCE['background'] = dict(empty_pixels=int(bg.sum()), pixel_count=bg.numel(),
                                      sum_alpha_max_error=maxerr(r.all_contribution_sum, r.accumulated_alpha))

    def test_native_footprint_clipped_image_boundary(self):
        # Identity projection: x=-1 maps to pixel -0.5. The Gaussian center is
        # outside the image but its positive-alpha footprint covers pixel x=0.
        f = center_fixture('occlusion')
        f['means3D'][:, 0] = -1.
        f['scales'].fill_(.015)
        r = render(self.patched, f, True, K=8, h=17, w=19)
        self.assertGreater(float(r.accumulated_alpha[:, 0].max()), 0.)
        self.assertEqual(float(r.accumulated_alpha[:, -1].max()), 0.)
        original, _ = render(self.actual, f, h=17, w=19)
        off, _ = render(self.patched, f, h=17, w=19)
        self.assertTrue(torch.equal(original, r.rgb) and torch.equal(original, off))
        self.assertLessEqual(maxerr(r.all_contribution_sum, r.accumulated_alpha), TOL)
        EVIDENCE['image_boundary'] = dict(accepted_left_column=True, empty_right_column=True,
            rgb_bitwise_equal=True, sum_alpha_max_error=maxerr(r.all_contribution_sum, r.accumulated_alpha))

    def test_full_backward_and_optimizer_step(self):
        for mode in ('sh', 'colors'):
            snapshots = {}
            for label, backend, debug in [('actual', self.actual, False), ('original', self.original, False),
                                          ('off', self.patched, False), ('on', self.patched, True)]:
                f = gradient_fixture(mode)
                optimizer = torch.optim.Adam(list(f.values()), lr=.002, foreach=False)
                r = render(backend, f, debug, degree=3 if mode == 'sh' else 0)
                rgb = r.rgb if debug else r[0]
                if debug:
                    self.assertTrue(rgb.requires_grad)
                    for t in (r.gaussian_ids, r.gaussian_weights, r.all_contribution_sum, r.final_T):
                        self.assertFalse(t.requires_grad); self.assertIsNone(t.grad_fn)
                value = loss(rgb); value.backward()
                grads = {k: v.grad.detach().clone() for k, v in f.items()}
                for k in ('means3D', 'scales', 'rotations', 'opacities', 'shs' if mode == 'sh' else 'colors_precomp'):
                    self.assertGreater(float(grads[k].abs().max()), 0., k)
                    self.assertTrue(torch.isfinite(grads[k]).all())
                optimizer.step()
                state = [{k: v.detach().clone() if torch.is_tensor(v) else v for k, v in s.items()}
                         for s in optimizer.state.values()]
                snapshots[label] = dict(rgb=rgb.detach().clone(), grads=grads,
                                         params={k: v.detach().clone() for k,v in f.items()}, state=state)
            ref = snapshots['actual']; measurements = {}
            for label in ('original', 'off', 'on'):
                s = snapshots[label]
                self.assertTrue(torch.equal(ref['rgb'], s['rgb']))
                errs = {k: maxerr(ref['grads'][k], s['grads'][k]) for k in ref['grads']}
                # This fixture intentionally permits exact checks without inter-pixel atomics.
                for k in ref['grads']:
                    self.assertTrue(torch.equal(ref['grads'][k], s['grads'][k]), (mode, label, k, errs[k]))
                    self.assertTrue(torch.equal(ref['params'][k], s['params'][k]), (mode, label, k))
                for a, b in zip(ref['state'], s['state']):
                    for k in a:
                        self.assertTrue(torch.equal(a[k], b[k]) if torch.is_tensor(a[k]) else a[k] == b[k])
                measurements[label] = dict(gradient_max_errors=errs, exact_gradients=True,
                                          exact_updated_parameters=True, exact_optimizer_states=True)
            EVIDENCE['gradients'][mode] = measurements
            EVIDENCE['training'][mode] = dict(optimizer='Adam', lr=.002, loss='weighted quadratic RGB + product',
                nonzero_groups={k: float(v.abs().max()) for k,v in ref['grads'].items()}, compared_backends=list(snapshots))

    def test_raw_model_Adam_one_step(self):
        reference_fixture = gradient_fixture('sh')
        raw_values = dict(xyz=reference_fixture['means3D'].detach(),
            log_scale=reference_fixture['scales'].detach().log(),
            raw_rotation=reference_fixture['rotations'].detach(),
            opacity_logit=torch.logit(reference_fixture['opacities'].detach()),
            sh_dc=reference_fixture['shs'].detach()[:, :1].contiguous(),
            sh_rest=reference_fixture['shs'].detach()[:, 1:].contiguous())
        snapshots = {}
        for label, backend, debug in [('actual', self.actual, False), ('original', self.original, False),
                                     ('off', self.patched, False), ('on', self.patched, True)]:
            params = torch.nn.ParameterDict({k: torch.nn.Parameter(v.clone()) for k,v in raw_values.items()})
            optimizer = torch.optim.Adam(params.parameters(), lr=.002, foreach=False)
            fixture = dict(means3D=params['xyz'], means2D=torch.zeros_like(params['xyz'], requires_grad=True),
                opacities=params['opacity_logit'].sigmoid(), scales=params['log_scale'].exp(),
                rotations=torch.nn.functional.normalize(params['raw_rotation'], dim=1),
                shs=torch.cat([params['sh_dc'], params['sh_rest']], dim=1))
            result = render(backend, fixture, debug, degree=3)
            rgb = result.rgb if debug else result[0]
            loss(rgb).backward()
            grads = {k: p.grad.clone() for k,p in params.items()}
            self.assertTrue(all(float(g.abs().max()) > 0 for g in grads.values()))
            optimizer.step()
            snapshots[label] = dict(grads=grads, params={k:p.detach().clone() for k,p in params.items()})
        ref = snapshots['actual']
        for label in ('original', 'off', 'on'):
            for k in raw_values:
                self.assertTrue(torch.equal(ref['grads'][k], snapshots[label]['grads'][k]), (label,k))
                self.assertTrue(torch.equal(ref['params'][k], snapshots[label]['params'][k]), (label,k))
        EVIDENCE['raw_model_training'] = dict(optimizer='Adam', lr=.002, steps=1,
            exact_gradients=True, exact_updated_parameters=True, groups=list(raw_values),
            nonzero_gradient_max={k:float(g.abs().max()) for k,g in ref['grads'].items()},
            activations='exp(log_scale), sigmoid(opacity_logit), normalized quaternion, SH dc+rest concat',
            compared_backends=list(snapshots))

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(NativeChecks)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    torch.cuda.synchronize()
    EVIDENCE.update(passed=result.wasSuccessful(), tests=result.testsRun,
                    failures=[str(e) for _,e in result.failures], errors=[str(e) for _,e in result.errors])
    atomic_json(ART / 'results/NATIVE_TESTS.json', EVIDENCE)
    raise SystemExit(0 if result.wasSuccessful() else 1)
