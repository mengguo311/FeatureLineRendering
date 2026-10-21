from runtime import *
import unittest
from unittest.mock import patch
from diagnostic import headroom_status, topology, curve_evidence, display_metrics
from reference import ray_depth
sys.path.insert(0, str(WORK / 'experiments/partwise_sketch_hatching'))
from experiments.partwise_sketch_hatching import core_walk_v2 as walker

class HeadroomTests(unittest.TestCase):
    def test_no_connected_boundary_is_not_h2_success(self):
        self.assertEqual(headroom_status(0., 0., True), 'ZERO_HEADROOM')

    def test_missing_evidence_unknown_and_no_crossing_zero(self):
        self.assertEqual(headroom_status(1., 2., False), 'UNKNOWN')
        self.assertEqual(headroom_status(float('nan'), 2., True), 'UNKNOWN')
        self.assertEqual(headroom_status(1., 0., True), 'ZERO_HEADROOM')
        self.assertEqual(headroom_status(1., .3, True), 'ELIGIBLE')

    def test_invalid_curve_and_internal_ring_not_semantic_boundary(self):
        p = [[0, 0, 0], [1, 0, 0]]
        self.assertEqual(curve_evidence(p, {}), 'UNKNOWN')
        evidence = dict(source='authored GT', confirmed=True, kind='physical_profile_ring')
        self.assertEqual(curve_evidence([[0,0,0],[0,0,0]], evidence), 'UNKNOWN')
        self.assertEqual(curve_evidence(p, evidence), 'AUTHORED_STRUCTURE_ONLY')
        self.assertEqual(curve_evidence([[float('nan'),0,0],[1,0,0]], evidence), 'UNKNOWN')

    def test_no_knn_connecting_separate_surfaces(self):
        vertices = [[0,0,0],[1,0,0],[0,1,0],[1.000001,0,0],[1.000001,1,0],[.000001,1,0]]
        m = core.finalize_mesh(vertices, [[0,1,2],[3,4,5]], [1,2])
        result = topology(m)
        self.assertEqual(result['component_count'], 2)
        self.assertEqual(result['shared_part_boundary_length_world'], 0.)

    def test_real_walker_crosses_same_label_and_stops_at_different_label(self):
        vertices = [[0,0,0],[1,0,0],[0,1,0],[1,1,0]]
        faces = [[0,1,2],[1,3,2]]
        m = core.finalize_mesh(vertices, faces, [1,2])
        t = topology(m)
        self.assertAlmostEqual(t['shared_part_boundary_length_world'], np.sqrt(2))
        with patch.object(walker, 'field', return_value=np.array([1.,0.,0.])):
            audit = {}
            ff, bb = walker.walk(m,0,np.array([.6,.2,.2]),1,'mixed',0,0.,.7,.1,1,audit)
            self.assertEqual(audit['reason'], 'part_boundary')
            self.assertEqual(set(ff), {0})
            self.assertAlmostEqual(audit['arc_world'], .6)
            m['parts'][:] = 1
            audit2 = {}
            ff2, bb2 = walker.walk(m,0,np.array([.6,.2,.2]),1,'mixed',0,0.,.7,.1,1,audit2)
            self.assertEqual(audit2['reason'], 'length_reached')
            self.assertIn(1, ff2)
            self.assertAlmostEqual(audit2['arc_world'], .7)

    def test_display_controls_and_fixed_non_target(self):
        labels = np.tile(np.array([1,1,2,2,3,3]), (6,1))
        hatch = np.zeros((6,6)); hatch[2,:] = .5
        contours = np.zeros((6,6)); contours[0,:] = .9
        rings = np.zeros((6,6)); rings[4,:] = .8
        before = 1 - np.maximum(hatch, contours)
        after = 1 - np.maximum(np.maximum(hatch, contours), rings)
        def score(image, h=hatch, c=contours):
            return display_metrics(before,image,hatch,h,contours,c,rings,labels)
        self.assertEqual(score(after)['status'], 'VALID_DISPLAY')
        self.assertTrue(score(after)['hatch_exact'])
        self.assertEqual(score(before)['status'], 'ENGINEERING_INVALID')
        self.assertEqual(score(np.ones_like(after),np.zeros_like(hatch))['status'], 'ENGINEERING_INVALID')
        drift = np.ones_like(after); drift[:,1:] = after[:,:-1]
        self.assertEqual(score(drift)['status'], 'ENGINEERING_INVALID')
        changed = hatch.copy(); changed[2,2] = 0
        self.assertFalse(score(after,changed)['hatch_exact'])

    def test_output_guard_rejects_old_output(self):
        with self.assertRaises(ValueError): output_path(BASE/'forbidden_probe.json')

    def test_independent_continuous_hiding_reference_known_intersections(self):
        _,_,cfg=load_asset()
        depths,parts=ray_depth(cfg['asset'],np.array([[0.,3.,0.],[2.,1.,0.],[2.,.08,0.]]),
                               np.array([[0.,-1.,0.],[-1.,0.,0.],[-1.,0.,0.]]))
        np.testing.assert_allclose(depths,[1.28,1.925,1.42],rtol=0,atol=1e-12)
        np.testing.assert_array_equal(parts,[2,2,3])

if __name__ == '__main__':
    unittest.main(verbosity=2)
