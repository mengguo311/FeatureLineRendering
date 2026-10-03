"""Independent synthetic calibration fixtures; initially executed before implementation.

Expected projections are computed here from camera matrices, never production code.
These finite examples do not establish universal silhouette identifiability.
"""
import importlib
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE.parent / 'CONFIG.json').read_text())


def camera(eye, target=(0., 0., 4.)):
    eye = np.asarray(eye, dtype=float)
    forward = np.asarray(target) - eye
    forward /= np.linalg.norm(forward)
    right = np.cross([0., 1., 0.], forward)
    right /= np.linalg.norm(right)
    down = np.cross(forward, right)
    rotation = np.stack([right, down, forward])
    w2c = np.eye(4)
    w2c[:3, :3] = rotation
    w2c[:3, 3] = -rotation @ eye
    return {'native_K': [[400., 0., 399.5], [0., 400., 399.5], [0., 0., 1.]],
            'w2c': w2c.tolist(), 'native_width': 800, 'native_height': 800}


def independent_project(xyz, cam):
    xyz = np.asarray(xyz, dtype=float)
    matrix = np.asarray(cam['w2c'])
    q = np.c_[xyz, np.ones(len(xyz))] @ matrix.T
    h = q[:, :3] @ np.asarray(cam['native_K']).T
    return h[:, :2] / h[:, 2:3], q[:, 2]


def native(depth=4., alpha=1., shape=(800, 800)):
    out = {name: np.full(shape, value, dtype=np.float32) for name, value in
           [('alpha', alpha), ('depth', depth), ('median_depth', depth),
            ('moment2', alpha * depth * depth)]}
    out['topk_depth'] = np.zeros((*shape, 4), np.float32)
    out['topk_w'] = np.zeros((*shape, 4), np.float32)
    out['topk_id'] = np.full((*shape, 4), -1, np.int32)
    out['topk_depth'][..., 0] = depth
    out['topk_w'][..., 0] = alpha
    out['topk_id'][..., 0] = 0
    return out


class GeometryCalibration(unittest.TestCase):
    def setUp(self):
        self.g = importlib.import_module('geometry')
        self.cams = [camera((-1., 0., 0.)), camera((0., 0., 0.)), camera((1., 0., 0.))]
        t = np.linspace(0., 1., 32)
        self.xyz = np.c_[-.45 + .9*t, -.3 + .6*t, 4. + .1*t]
        self.obs = [independent_project(self.xyz, c)[0] for c in self.cams]

    def test_projection_independent_known_points(self):
        for cam in self.cams:
            uv, z = self.g.project(self.xyz, cam)
            expected_uv, expected_z = independent_project(self.xyz, cam)
            np.testing.assert_allclose(uv, expected_uv, atol=1e-10)
            np.testing.assert_allclose(z, expected_z, atol=1e-10)

    def test_same_line_three_views_recovered(self):
        xyz, diagnostics = self.g.triangulate(self.obs, self.cams, CONFIG)
        np.testing.assert_allclose(xyz, self.xyz, atol=1e-7)
        self.g.validate_shape(xyz, self.cams, CONFIG)

    def test_repeated_equal_lines_abstain(self):
        self.assertIsNone(self.g.unique_choice([.2, .2, 3.], CONFIG))
        self.assertIsNone(self.g.unique_choice([.2, .7, 3.], CONFIG))
        self.assertEqual(self.g.unique_choice([.2, 1.2, 3.], CONFIG), 0)
        self.assertIsNone(self.g.unique_choice([], CONFIG))

    def test_small_baseline_rejected(self):
        cams = [camera((x, 0., 0.)) for x in [-.00001, 0., .00001]]
        obs = [independent_project(self.xyz, c)[0] for c in cams]
        with self.assertRaises(ValueError):
            self.g.triangulate(obs, cams, CONFIG)

    def test_view_moving_inconsistent_line_rejected(self):
        # Third-view displacement violates the same-world-line fixture.
        moved = [x.copy() for x in self.obs]
        moved[2][:, 1] += 80.
        with self.assertRaises(ValueError):
            self.g.triangulate(moved, self.cams, CONFIG)

    def test_collapsed_and_nonfinite_geometry_rejected(self):
        with self.assertRaises(ValueError):
            self.g.validate_shape(np.tile([0., 0., 4.], (16, 1)), self.cams, CONFIG)
        invalid = self.xyz.copy()
        invalid[2, 0] = np.nan
        with self.assertRaises(ValueError):
            self.g.validate_shape(invalid, self.cams, CONFIG)

    def test_path_order_and_reversal(self):
        result = self.g.ordered_match(self.obs[0], self.obs[1][::-1], self.cams[0], self.cams[1], CONFIG)
        self.assertGreaterEqual(result['coverage'], .7)
        mapping = np.asarray(result['mapping'], dtype=int)
        self.assertGreaterEqual(len(mapping), 23)
        self.assertTrue(np.all(np.diff(mapping[:, 0]) >= 0))
        self.assertTrue(np.all(np.diff(mapping[:, 1]) <= 0))

    def proposal_fixture(self, two=False):
        names = CONFIG['construction'][:3]
        cameras = dict(zip(names, self.cams))
        records = {}
        for name, cam in cameras.items():
            records[name] = []
            for index in range(2 if two else 1):
                points = self.xyz.copy()
                points[:, 1] += index * 1.3
                uv, _ = independent_project(points, cam)
                records[name].append({'id': name + '_synthetic_' + str(index), 'points': uv,
                    'length': float(np.linalg.norm(np.diff(uv, axis=0), axis=1).sum()),
                    'source_bits': 1, 'curvature': np.zeros(30)})
        return records, cameras

    def test_complete_proposal_positive_and_layer_conflict(self):
        records, cameras = self.proposal_fixture()
        good = lambda view, uv, z: {'supported': np.ones(len(z), bool),
                                   'layer_conflict': np.zeros(len(z), bool)}
        proposals, diagnostics = self.g.build_proposals(records, cameras, CONFIG, good)
        self.assertEqual(len(proposals), 1)
        self.assertTrue(proposals[0]['construction_ok'])
        bad = lambda view, uv, z: {'supported': np.ones(len(z), bool),
                                  'layer_conflict': np.ones(len(z), bool)}
        rejected, _ = self.g.build_proposals(records, cameras, CONFIG, bad)
        self.assertEqual(len(rejected), 1)
        self.assertFalse(rejected[0]['construction_ok'])
        self.assertIn('construction_layer_conflict', rejected[0]['construction_reasons'])

    def test_complete_null_forced_wrong_associations(self):
        records, cameras = self.proposal_fixture(two=True)
        good = lambda view, uv, z: {'supported': np.ones(len(z), bool),
                                   'layer_conflict': np.zeros(len(z), bool)}
        proposals, diagnostics = self.g.build_proposals(records, cameras, CONFIG, good)
        self.assertEqual(sum(p['construction_ok'] for p in proposals), 2)
        self.assertTrue(diagnostics['null']['sufficient'])
        self.assertFalse(diagnostics['null']['rematched'])
        self.assertEqual(sum(p['construction_ok'] for p in diagnostics['null_proposals']), 0)


class PathCalibration(unittest.TestCase):
    def test_order_empty_and_no_gap_bridge(self):
        paths = importlib.import_module('paths')
        mask = np.zeros((20, 20), dtype=bool)
        self.assertEqual(len(paths.trace_paths(mask)), 0)
        mask[5, 2:8] = True
        mask[5, 10:16] = True
        traces = paths.trace_paths(mask)
        self.assertEqual(len(traces), 2)
        for trace in traces:
            trace = np.asarray(trace)
            self.assertTrue(np.all(np.linalg.norm(np.diff(trace, axis=0), axis=1) <= np.sqrt(2)))
            sampled = paths.resample(trace, 32)
            self.assertEqual(np.asarray(sampled).shape, (32, 2))


class NativeDepthCalibration(unittest.TestCase):
    def setUp(self):
        self.f = importlib.import_module('fields')
        self.uv = np.array([[399., 399.], [401., 399.], [403., 399.]])

    def test_occlusion_disocclusion_and_uncertain_visibility(self):
        field = native()
        v = self.f.classify_visibility(field, self.uv, np.array([3., 4., 5.]), CONFIG)
        np.testing.assert_array_equal(v['occluded'], [False, False, True])
        np.testing.assert_array_equal(v['visible'], [True, True, False])
        low = native(alpha=.01)
        v = self.f.classify_visibility(low, self.uv, np.array([5., 5., 5.]), CONFIG)
        np.testing.assert_array_equal(v['visible'], [True, True, True])
        np.testing.assert_array_equal(v['uncertain'], [True, True, True])

    def test_absolute_layer_weight_and_conflict(self):
        field = native(alpha=.5)
        field['topk_depth'][..., 1] = 5.
        field['topk_w'][..., 1] = .04
        field['topk_id'][..., 1] = 1
        support = self.f.depth_support(field, self.uv, np.array([4., 4., 4.]), CONFIG)
        np.testing.assert_array_equal(support['layer_conflict'], [False]*3)
        field['topk_w'][..., 1] = .05
        support = self.f.depth_support(field, self.uv, np.array([4., 4., 4.]), CONFIG)
        np.testing.assert_array_equal(support['layer_conflict'], [True]*3)
        np.testing.assert_array_equal(support['supported'], [False]*3)

    def test_outside_and_behind_separate_from_occlusion(self):
        uv = np.array([[-1., 300.], [800., 300.], [300., 300.]])
        result = self.f.classify_visibility(native(), uv, np.array([4., 4., -1.]), CONFIG)
        self.assertEqual(int(np.sum(result['occluded'])), 0)
        self.assertEqual(int(np.sum(result['visible'])), 0)

    def test_missing_low_alpha_kept_in_denominators(self):
        uv = np.c_[np.linspace(300., 420., 64), np.full(64, 399.)]
        tangent = np.tile([1., 0.], (64, 1))
        empty = lambda points, directions: [np.empty((0, 2)) for _ in points]
        result = self.f.validate_view(native(alpha=.01), uv, np.full(64, 4.), tangent, empty, CONFIG)
        self.assertTrue(result['eligible'])
        self.assertEqual(result['counts']['V'], 64)
        self.assertEqual(result['counts']['U'], 64)
        self.assertEqual(result['counts']['K'], 64)
        self.assertEqual(result['ratios']['position_direction_support'], 0.)
        self.assertEqual(result['ratios']['uncertain'], 1.)
        self.assertFalse(result['passed'])

    def test_empty_denominators_supply_no_vote(self):
        uv = np.c_[np.linspace(-200., -100., 64), np.full(64, 399.)]
        empty = lambda points, directions: [np.empty((0, 2)) for _ in points]
        result = self.f.validate_view(native(), uv, np.full(64, 4.), np.tile([1., 0.], (64, 1)), empty, CONFIG)
        self.assertFalse(result['eligible'])
        self.assertFalse(result['positive_vote'])
        self.assertTrue(all(value is None for value in result['ratios'].values()))

    def test_unjustified_absence_cannot_change_occlusion(self):
        field = native()
        # Occluder at projection x399, but compatible same-tangent evidence at x401.
        for name, value in [('depth', 5.), ('median_depth', 5.), ('moment2', 25.)]:
            field[name][399, 401] = value
        field['topk_depth'][399, 401, 0] = 5.
        callback = lambda points, directions: [np.array([[400., 399.], [401., 399.]]) for _ in points]
        result = self.f.validate_view(field, np.array([[399., 399.]]), np.array([5.]),
                                      np.array([[1., 0.]]), callback, CONFIG)
        self.assertEqual(result['counts']['O'], 1)
        self.assertEqual(result['counts']['V'], 0)
        self.assertEqual(result['counts']['A_absence'], 1)
        self.assertEqual(result['ratios']['unjustified_absence'], 1.)
        self.assertFalse(result['passed'])


class StageCalibration(unittest.TestCase):
    def test_final_camera_forbidden_in_construction(self):
        io = importlib.import_module('pipeline_io')
        io.assert_stage_access('construction', 'F_001')
        with self.assertRaises(ValueError):
            io.assert_stage_access('construction', 'C_007')
        with self.assertRaises(ValueError):
            io.assert_stage_access('construction', 'F_014')

    def test_corrupted_sealed_asset_rejected(self):
        io = importlib.import_module('pipeline_io')
        workspace = HERE.parents[2]
        tmpbase = workspace / 'out/mic_persistent_line_feasibility_v1/tests'
        tmpbase.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='sealed_fixture_', dir=tmpbase) as tmp:
            tmp = Path(tmp)
            xyz = np.array([[0., 0., 4.], [1., 0., 4.]], dtype='<f8')
            offsets = np.array([0, 2], dtype='<i8')
            digest = hashlib.sha256(xyz.tobytes() + offsets.tobytes()).hexdigest()
            record = {'paths': [{'persistent_id': 'synthetic', 'controls_xyz': xyz.tolist()}],
                      'geometry_sha256': digest}
            target = tmp/'ASSET.json'
            target.write_text(json.dumps(record))
            np.savez(tmp/'ASSET.npz', controls=xyz, offsets=offsets)
            seal = {'geometry_sha256': digest, 'files': {
                name: hashlib.sha256((tmp/name).read_bytes()).hexdigest()
                for name in ['ASSET.json', 'ASSET.npz']}}
            (tmp/'ASSET_SEAL.json').write_text(json.dumps(seal))
            self.assertEqual(io.load_asset(target)['geometry_sha256'], digest)
            record['paths'][0]['controls_xyz'][0][0] = .1
            target.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                io.load_asset(target)


if __name__ == '__main__':
    unittest.main(verbosity=2)
