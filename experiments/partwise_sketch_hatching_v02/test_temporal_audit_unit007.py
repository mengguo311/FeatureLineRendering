"""Necessary oracle/metric controls for the frozen unit007 temporal audit.

Synthetic ink here checks the estimator, not application rendering quality.
The separate validator injects faults into the actual saved stroke PNGs.
"""
import json
import unittest
import numpy as np
from experiments.partwise_sketch_hatching_v02 import temporal_audit_unit007 as audit


def camera():
    return dict(R=np.eye(3), t=np.array([0., 0., 3.]), eye=np.array([0., 0., -3.]),
                focal=20., center=np.array([32., 32.]), size=64)


def cylinder():
    return dict(profiles_ry={'1': [[0., -1.], [1., -1.], [1., 1.], [0., 1.]]})


class AnalyticReferenceTests(unittest.TestCase):
    def test_cylinder_arbitrary_rays_against_closed_form(self):
        cam = camera()
        uv = np.array([[32., 32.], [37., 33.25], [27.125, 31.75]])
        depth, labels = audit.analytic_rays(cylinder(), cam, uv)
        dx = (uv[:, 0]-32.)/20.
        # (dx*t)^2 + (-3+t)^2 = 1; near positive root.
        expected = (6.-np.sqrt(36.-32.*(1.+dx**2)))/(2.*(1.+dx**2))
        np.testing.assert_allclose(depth, expected, rtol=0, atol=1e-12)
        np.testing.assert_array_equal(labels, np.ones(3, dtype=int))

    def test_plane_annulus_and_background(self):
        cam = dict(R=np.array([[1., 0., 0.], [0., 0., 1.], [0., -1., 0.]]),
                   t=np.array([0., 0., 2.]), eye=np.array([0., 2., 0.]),
                   focal=20., center=np.array([32., 32.]), size=64)
        asset = dict(profiles_ry={'3': [[.5, 0.], [1.5, 0.]]})
        depth, parts = audit.analytic_rays(asset, cam, np.array([[42., 32.], [32., 32.], [52., 32.]]))
        self.assertAlmostEqual(depth[0], 2.)
        self.assertEqual(parts.tolist(), [3, 0, 0])
        self.assertTrue(np.isinf(depth[1:]).all())

    def test_linear_degenerate_cone_ray(self):
        cam = camera()
        # Ray (0,1,1), cone radius=y: (-3+t)^2=t^2 -> t=1.5.
        asset = dict(profiles_ry={'2': [[0., 0.], [4., 4.]]})
        depth, parts = audit.analytic_rays(asset, cam, np.array([[32., 52.]]))
        self.assertAlmostEqual(depth[0], 1.5)
        self.assertEqual(int(parts[0]), 2)

    def test_midpoint_length_mass_including_cap_and_short_path(self):
        for length in (.001, .1, 2.):
            points = np.array([[0., 0., -1.], [0., length, -1.]])
            sampled = audit.sample_path(points)
            self.assertAlmostEqual(float(sampled['world_weight'].sum()), length)
            self.assertEqual(sampled['count'], min(128, max(8, int(np.ceil(length/.008)))))
            self.assertGreater(sampled['world'][0, 1], 0.)
            self.assertLess(sampled['world'][-1, 1], length)


class ActualOutputMetricTests(unittest.TestCase):
    def setUp(self):
        self.camera = camera()
        self.asset = cylinder()
        self.points = np.array([[0., -.8, -1.], [0., .8, -1.]])
        self.reference = audit.reference_maps(self.asset, self.camera)
        self.ink = np.zeros((64, 64), dtype=np.uint8)
        self.ink[24:41, 32] = 255

    def evaluate(self, ink, frame=0, points=None):
        return audit.evaluate_frame(ink, self.points if points is None else points, 1,
            self.camera, self.asset, 'fixture', 'orbit', frame, self.reference)

    def test_no_edit_drift_dropout_and_common_visible_denominator(self):
        original = self.evaluate(self.ink, 0)
        repeat = self.evaluate(self.ink, 1)
        noedit = audit.summarize([original, repeat])['per_part']['1']
        self.assertEqual(noedit['status'], 'GO')
        self.assertEqual(noedit['temporal']['normal_residual_change_abs_px']['max'], 0.)
        shifted = np.zeros_like(self.ink)
        shifted[:, 3:] = self.ink[:, :-3]
        drift = self.evaluate(shifted, 1)
        self.assertEqual(drift['summary']['missing_world_fraction'], 1.)
        dropout = self.evaluate(np.zeros_like(self.ink), 1)
        self.assertEqual(dropout['summary']['missing_world_fraction'], 1.)
        failed = audit.summarize([original, dropout, self.evaluate(self.ink, 2)])['per_part']['1']
        self.assertEqual(failed['status'], 'NO_GO')
        self.assertEqual(failed['temporal']['missing_either_world_fraction'], 1.)
        self.assertAlmostEqual(failed['temporal']['dropout_world_fraction'], .5)
        self.assertAlmostEqual(failed['temporal']['reappearance_world_fraction'], .5)
        self.assertIsNone(dropout['summary']['centroid_abs_px']['p95'])
        json.dumps(audit.summarize([original, dropout]), allow_nan=False)

    def test_short_endpoint_exclusion_is_reported_and_not_success(self):
        points = np.array([[0., -.01, -1.], [0., .01, -1.]])
        row = self.evaluate(self.ink, 0, points)
        self.assertGreater(row['summary']['raw_visible_world_length'], 0.)
        self.assertEqual(row['summary']['class_counts']['visible'], 0)
        self.assertEqual(row['summary']['class_counts']['boundary'], row['sample_count'])
        self.assertEqual(audit.summarize([row])['per_part']['1']['status'], 'UNMEASURED')

    def test_nonlocal_self_overlap_is_geometry_only_and_disclosed(self):
        points = np.array([[-.8, -.8, -1.], [.8, .8, -1.], [-.8, .8, -1.], [.8, -.8, -1.]])
        sample = audit.sample_path(points)
        ambiguous, arc, total = audit.projected_ambiguity(points, sample, self.camera)
        self.assertTrue(ambiguous.any())
        self.assertTrue(np.all(arc >= 0.))
        self.assertTrue(np.all(arc <= total))
        before = self.evaluate(self.ink, 0, points)
        absent = self.evaluate(np.zeros_like(self.ink), 0, points)
        self.assertEqual(before['samples']['class'], absent['samples']['class'])

    def test_hidden_profile_support_never_upgrades_visibility(self):
        hidden = np.array([[0., -.8, 1.], [0., .8, 1.]])
        row = self.evaluate(self.ink, 0, hidden)
        self.assertGreater(row['summary']['hidden_profile_present'], 0)
        self.assertEqual(row['summary']['class_counts']['visible'], 0)
        result = audit.summarize([row])
        self.assertEqual(result['hidden_visibility_verdict'], 'DIAGNOSTIC_ONLY_NO_FALSE_HIDDEN_GO')
        self.assertEqual(result['status'], 'UNMEASURED')


if __name__ == '__main__':
    unittest.main()
