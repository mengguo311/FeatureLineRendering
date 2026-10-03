"""Small independent fixtures for path provenance, finite NMS, and stage gates."""
import json
import copy
from pathlib import Path
import unittest
from unittest import mock

import numpy as np

import paths
import pipeline_io


CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'CONFIG.json').read_text())


def source(shape):
    return ({name: np.zeros(shape, dtype=float) for name in ['A', 'B_delta_D', 'B_delta_A']},
            {'alpha': np.ones(shape, dtype=float)})


class PathSourceCalibration(unittest.TestCase):
    def test_closed_loop_is_ordered_and_lexicographic(self):
        mask = np.zeros((12, 12), bool)
        mask[[4, 5, 6, 5], [5, 6, 5, 4]] = True
        result = paths.trace_paths(mask)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]), 5)
        np.testing.assert_array_equal(result[0][0], [5, 4])
        np.testing.assert_array_equal(result[0][-1], result[0][0])
        self.assertEqual(len({tuple(x) for x in result[0][:-1]}), 4)

    def test_union_does_not_duplicate_path_and_preserves_sources(self):
        response, native = source((40, 100))
        response['A'][20, 10:91] = 1
        response['B_delta_D'][20, 10:91] = .8
        response['B_delta_A'][20, 10:91] = .9
        records, counts = paths.extract_paths(response, native, CONFIG, 'synthetic')
        self.assertEqual(counts['construction_paths'], 1)
        self.assertEqual(records[0]['source_bits'], 7)
        self.assertEqual(records[0]['endpoint_degrees'], [1, 1])
        self.assertEqual(records[0]['points'].shape, (32, 2))

    def test_nms_uses_finite_maximum_and_b_requires_alpha(self):
        response, native = source((12, 12))
        response['B_delta_D'][5, 5] = .8
        response['B_delta_D'][5, 6] = np.inf
        response['B_delta_D'][4, 5] = np.nan
        _, bits = paths.evidence_mask(response, native, CONFIG)
        self.assertEqual(int(bits[5, 5]), 2)
        self.assertEqual(int(bits[5, 6]), 0)
        self.assertEqual(int(bits[4, 5]), 0)
        native['alpha'][5, 5] = .079
        _, bits = paths.evidence_mask(response, native, CONFIG)
        self.assertEqual(int(bits[5, 5]), 0)
        response['A'][5, 5] = 1
        _, bits = paths.evidence_mask(response, native, CONFIG)
        self.assertEqual(int(bits[5, 5]), 1)

    def test_validation_evidence_keeps_short_paths_and_direction(self):
        response, native = source((40, 40))
        response['A'][20, 10:16] = 1
        records, _ = paths.extract_paths(response, native, CONFIG, 'synthetic')
        self.assertEqual(len(records), 0)
        evidence = paths.Evidence(response, native, CONFIG)
        self.assertGreater(len(evidence.candidates([[12, 20]], [[1, 0]])[0]), 0)
        self.assertEqual(len(evidence.candidates([[12, 20]], [[0, 1]])[0]), 0)
        self.assertGreater(len(evidence.candidates([[12, 20]], [[-1, 0]])[0]), 0)


class StageOrderingCalibration(unittest.TestCase):
    def test_stage_rejects_before_any_metadata_or_array_read(self):
        with mock.patch.object(pipeline_io, 'check_freeze') as freeze, mock.patch.object(pipeline_io.np, 'load') as load:
            with self.assertRaises(ValueError):
                pipeline_io.load_view('validation', 'C_007')
            freeze.assert_not_called()
            load.assert_not_called()

    def test_final_decode_requires_asset_seal(self):
        with mock.patch.object(pipeline_io, 'check_freeze'), mock.patch.object(pipeline_io, 'verify_seal', side_effect=ValueError('missing asset seal')) as seal, mock.patch.object(pipeline_io.np, 'load') as load:
            with self.assertRaisesRegex(ValueError, 'missing asset seal'):
                pipeline_io.load_view('render', 'C_007')
            seal.assert_called_once_with('ASSET_SEAL.json')
            load.assert_not_called()


class FixedWorldRenderCalibration(unittest.TestCase):
    def test_perspective_depth_and_unoccluded_diagnostic(self):
        import render_result
        camera = {'w2c': np.eye(4).tolist(), 'native_K': [[100., 0., 400.], [0., 100., 400.], [0., 0., 1.]]}
        shape = (800, 800)
        native = {name: np.full(shape, value, dtype=float) for name, value in [('alpha', 1.), ('depth', 3.2), ('median_depth', 3.2), ('moment2', 3.2**2)]}
        native.update(topk_depth=np.full((*shape, 1), 3.2), topk_w=np.ones((*shape, 1)), topk_id=np.zeros((*shape, 1), dtype=int))
        path = {'persistent_id': 'test_fixed', 'controls_xyz': [[-1., 0., 2.], [1., 0., 4.]], 'width_px': 2, 'color_rgb': [0, 96, 220]}
        white = np.full((*shape, 3), 255, dtype=np.uint8)
        original = copy.deepcopy(path)
        actual, counts = render_result.paint(white, [path], camera, native)
        # x400 has perspective-correct Z=3, not linearly interpolated Z=3.333.
        np.testing.assert_array_equal(actual[400, 400], path['color_rgb'])
        np.testing.assert_array_equal(actual[400, 425], [255, 255, 255])
        diagnostic, _ = render_result.paint(white, [path], camera, native, diagnostic=True)
        np.testing.assert_array_equal(diagnostic[400, 425], CONFIG['render']['proposal_diagnostic_rgb'])
        self.assertGreater(counts['occluded'], 0)
        self.assertEqual(path, original)
        edited = copy.deepcopy(path)
        edited['width_px'] = 4
        edited['color_rgb'] = [220, 0, 200]
        self.assertEqual(pipeline_io.geometry_hash([edited]), pipeline_io.geometry_hash([path]))
        edit_pixels, _ = render_result.paint(white, [edited], camera, native)
        np.testing.assert_array_equal(edit_pixels[400, 400], edited['color_rgb'])
        self.assertGreater(np.count_nonzero(np.any(edit_pixels != actual, axis=2)), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
