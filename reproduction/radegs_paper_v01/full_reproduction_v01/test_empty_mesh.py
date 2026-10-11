import unittest
from unittest.mock import Mock
import numpy as np
import open3d as o3d
from test_tsdf_touch import grid
from empty_mesh import extract_mesh


class EmptyMeshTests(unittest.TestCase):
    def test_four_observations_preserve_native_nonempty_mesh(self):
        g=grid();d=o3d.t.geometry.Image(np.full((16,16),1.133,np.float32))
        k=o3d.core.Tensor(np.array([[30,0,8],[0,30,8],[0,0,1]],np.float64));e=o3d.core.Tensor(np.eye(4))
        coords=g.compute_unique_block_coordinates(d,k,e,1.,8.)
        for _ in range(4):g.integrate(coords,d,k,e,1.,8.)
        expected=g.extract_triangle_mesh().to_legacy()
        mesh,detail=extract_mesh(g)
        self.assertGreater(len(mesh.triangles),0)
        # Native OpenMP append order is not part of mesh geometry.
        a=np.asarray(mesh.vertices);b=np.asarray(expected.vertices)
        np.testing.assert_array_equal(a[np.lexsort(a.T)],b[np.lexsort(b.T)])
        self.assertEqual(len(mesh.triangles),len(expected.triangles))
        self.assertFalse(detail['empty'])

    def test_unrelated_native_error_is_not_swallowed(self):
        g=Mock();g.extract_triangle_mesh.side_effect=RuntimeError('different failure')
        with self.assertRaisesRegex(RuntimeError,'different failure'):extract_mesh(g)

    def test_one_observation_is_empty_at_unchanged_default_weight_threshold(self):
        g=grid();d=o3d.t.geometry.Image(np.full((16,16),1.133,np.float32))
        k=o3d.core.Tensor(np.array([[30,0,8],[0,30,8],[0,0,1]],np.float64));e=o3d.core.Tensor(np.eye(4))
        coords=g.compute_unique_block_coordinates(d,k,e,1.,8.)
        g.integrate(coords,d,k,e,1.,8.)
        mesh,detail=extract_mesh(g)
        self.assertEqual(len(mesh.vertices),0);self.assertEqual(len(mesh.triangles),0)
        self.assertTrue(detail['empty'])
        self.assertEqual(detail['weight_threshold'],3.)


if __name__=='__main__':unittest.main(verbosity=2)
