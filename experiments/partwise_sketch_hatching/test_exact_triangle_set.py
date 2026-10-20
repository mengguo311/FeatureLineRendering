"""Independent tiny set-idempotence checks; --old calls preserved round013."""
import round014_common
import sys
import unittest
from unittest.mock import patch
import numpy as np
import core
import mesh_attachment as adapter
import planar_fragments as old
import planar_fragments_exact as new

RED = '--old' in sys.argv
if RED:
    sys.argv.remove('--old')
ENGINE = old if RED else new
CAM = {'R': np.eye(3), 't': np.zeros(3), 'center': np.array([8., 8.]),
       'eye': np.zeros(3), 'focal': 8., 'size': 16}
PATH = np.array([[-1., -1., 4.], [1., -1., 4.]])
OWNER = np.array([[-3., -3., 4.], [3., -3., 4.], [0., 3., 4.]])
UV = np.array([[3., 3.], [4., 3.], [3., 4.]])

def triangle(z=3.):
    return np.column_stack(((UV - 8.) * z / 8., np.full(3, z)))

def scene(triangles):
    vertices = np.concatenate([OWNER] + list(triangles))
    faces = np.arange(len(vertices)).reshape(-1, 3)
    return core.finalize_mesh(vertices, faces, np.ones(len(faces), int))

def call(triangles, engine=ENGINE):
    return adapter.render_validated(scene(triangles), [0], [0], PATH,
                                    engine.render, CAM, .8, 2, 2., .006)

def count_subtractions(triangles):
    # One owner and a disjoint cutter leave one fragment: each invocation
    # corresponds to processing one cutter. The actual algorithm runs unchanged.
    with patch.object(ENGINE, 'difference', wraps=ENGINE.difference) as counted:
        result = call(triangles)
    return counted.call_count, result

class ExactTriangleSetTests(unittest.TestCase):
    def test_exact_duplicate_is_processed_once(self):
        count, _ = count_subtractions([triangle(), triangle()])
        self.assertEqual(count, 1, 'A minus (T union T) processes one set member')

    @unittest.skipIf(RED, 'additional candidate safety checks')
    def test_winding_new_vertex_ids_are_same_geometry(self):
        count, _ = count_subtractions([triangle(), triangle()[[2, 1, 0]]])
        self.assertEqual(count, 1)

    @unittest.skipIf(RED, 'additional candidate safety checks')
    def test_one_ulp_different_triangle_is_retained(self):
        other = triangle()
        other[0, 0] = np.nextafter(other[0, 0], np.inf)
        count, _ = count_subtractions([triangle(), other])
        self.assertEqual(count, 2)

    @unittest.skipIf(RED, 'additional candidate safety checks')
    def test_equal_projection_different_depth_is_retained(self):
        count, _ = count_subtractions([triangle(3.), triangle(2.)])
        self.assertEqual(count, 2)

    @unittest.skipIf(RED, 'additional candidate safety checks')
    def test_duplicate_output_idempotence_all_arrays(self):
        a = call([triangle()])
        b = call([triangle(), triangle(), triangle()[::-1]])
        self.assertEqual(set(a), set(b))
        for key in a:
            np.testing.assert_array_equal(a[key], b[key], err_msg=key)

    @unittest.skipIf(RED, 'additional candidate safety checks')
    def test_nondeduplicated_output_is_old_output_exactly(self):
        tris = [triangle(3.), triangle(2.)]
        a, b = call(tris), call(tris, old)
        for key in a:
            np.testing.assert_array_equal(a[key], b[key], err_msg=key)

    @unittest.skipIf(RED, 'additional candidate safety checks')
    def test_duplicate_co_depth_nonowner_still_rejected(self):
        with self.assertRaisesRegex(new.UnsupportedGeometry, 'ambiguous_nonowner_depth'):
            call([OWNER.copy(), OWNER[::-1].copy()])

    @unittest.skipIf(RED, 'additional candidate safety checks')
    def test_duplicate_tilt_still_rejected(self):
        tri = triangle()
        tri[0, 2] += .1
        with self.assertRaisesRegex(new.UnsupportedGeometry, 'nonfrontoparallel_triangle'):
            call([tri, tri[::-1]])

if __name__ == '__main__':
    unittest.main(verbosity=2)
