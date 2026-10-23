"""Owner, boundary, compositing and real-asset regressions for unit007."""
import runtime
import json
import unittest
from pathlib import Path
import numpy as np
from geometry import mesh_data, resize_camera
from render import render
from hybrid import compose
from test_gap_completion import fixture
from linked_contours import contour_masks, render_contours


class LinkedContourTests(unittest.TestCase):
    def test_foreground_owner_labels_and_no_wrap(self):
        depth = np.full((12, 14), 4., np.float32)
        regions = np.full(depth.shape, 4, np.int32)
        regions[:, :7] = 2
        masks = contour_masks(depth, regions)
        self.assertFalse(masks['occlusion'].any())  # labels alone are not edges
        depth[:, :7] = 3.
        self.assertFalse(contour_masks(depth, regions)['occlusion'].any())
        regions[:, :7], regions[:, 7:] = 4, 2
        edge = contour_masks(depth, regions)['occlusion']
        expected = np.zeros_like(edge); expected[:, 6] = True
        np.testing.assert_array_equal(edge, expected)
        # Reverse depth and target assignment: the foreground pixel moves right.
        depth[:, :7], depth[:, 7:] = 4., 3.
        regions[:, :7], regions[:, 7:] = 2, 4
        expected[:] = False; expected[:, 7] = True
        np.testing.assert_array_equal(contour_masks(depth, regions)['occlusion'], expected)
        # Adjacent differences < threshold, but endpoints differ by > threshold.
        depth = np.broadcast_to(3. + .01*np.arange(14), (12, 14)).copy()
        self.assertFalse(contour_masks(depth, np.full(depth.shape, 4))['occlusion'].any())
        self.assertFalse(contour_masks(depth.T, np.full(depth.T.shape, 4))['occlusion'].any())

    def test_background_outline_stays_on_hit_target(self):
        depth = np.full((12, 14), np.inf)
        depth[3:9, 4:10] = 3.
        regions = np.zeros(depth.shape, np.int32); regions[3:9, 4:10] = 4
        masks = contour_masks(depth, regions)
        self.assertTrue(masks['silhouette'].any())
        self.assertFalse(masks['occlusion'].any())
        self.assertFalse(masks['silhouette'][~np.isfinite(depth)].any())
        regions[3:9, 4:10] = 2
        self.assertFalse(contour_masks(depth, regions)['silhouette'].any())

    def test_real_occluder_legacy_exact_max_before_resolve_and_zero_S(self):
        mesh, paths, meta, camera = fixture()
        pair, hi = render_contours(mesh, paths, meta, camera)
        np.testing.assert_array_equal(pair['hatch'], render(mesh, {4:paths}, meta['styles'], camera)['hatch'])
        self.assertTrue(np.all(pair['outlined'] >= pair['hatch']))
        raster = hi['raster']; low = lambda x:x.reshape(96, 2, 96, 2).mean((1, 3))
        np.testing.assert_array_equal(pair['outlined'], low(np.maximum(raster['hatch_hi'], raster['contour_hi'])))
        paper = np.full((96, 96, 3), .95, np.float32)
        for ink in pair.values():
            image, alpha = compose(paper, ink, np.zeros((96, 96), np.float32), True)
            np.testing.assert_array_equal(image, paper); self.assertFalse(alpha.any())
        vertices=np.vstack([mesh['vertices'],[[-.3,-.4,3.4],[.3,-.4,3.4],[-.3,.4,3.4],[.3,.4,3.4]]])
        faces=np.vstack([mesh['faces'],[[6,7,8],[8,7,9]]])
        labels=np.concatenate([mesh['regions'],[2,2]])
        blocked=mesh_data(vertices,faces,labels)
        pair, hi=render_contours(blocked,paths,meta,camera)
        rr=hi['raster']; self.assertTrue((rr['regions_hi']==2).any())
        self.assertFalse(rr['contour_hi'][rr['regions_hi']==2].any())
        for ink in pair.values():self.assertEqual(float(ink[40:56,42:54].sum()),0.)

    def test_real_lego_identity_and_old_raster(self):
        root=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/baseline/portable_demo/examples/lego_bucket_cross')
        with np.load(root/'mesh.npz') as z:mesh=mesh_data(z['vertices'],z['faces'],z['face_regions'])
        with np.load(root/'region_4.npz') as z:paths={k:z[k] for k in z.files}
        before={k:v.copy() for k,v in paths.items()};meta=json.loads((root/'asset.json').read_text())
        self.assertEqual(len(paths['points']),1904);self.assertEqual(len(np.unique(paths['stroke_id'])),351)
        cameras=json.loads((runtime.ACTIVE_UNIT/'CAMERAS.json').read_text())['views']
        camera=resize_camera(next(v['camera'] for v in cameras if v['kind']=='build'),96)
        pair,hi=render_contours(mesh,paths,meta,camera)
        np.testing.assert_array_equal(pair['hatch'],render(mesh,{4:paths},meta['styles'],camera)['hatch'])
        self.assertTrue(hi['contour_ink'].any())
        for key in paths:np.testing.assert_array_equal(paths[key],before[key])


if __name__=='__main__':unittest.main(verbosity=2)
