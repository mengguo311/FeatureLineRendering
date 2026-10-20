import unittest
from pathlib import Path
import numpy as np
from parameter_smoke import covariance_and_world_axis, projected_major_sigma, distance_weighted_world_axis, sh_dc_rgb, equal_block_features, prepare_arm_features, validate_fit_manifest, validate_partition


class GaussianParameterMath(unittest.TestCase):
    def test_world_axis_and_covariance_rotation(self):
        scales = np.log(np.array([[4., 2., 1.]], dtype=np.float64))
        identity = np.array([[1., 0., 0., 0.]])
        cov, longest = covariance_and_world_axis(scales, identity)
        np.testing.assert_allclose(cov[0], np.diag([16., 4., 1.]), atol=1e-10)
        np.testing.assert_allclose(longest, [4.])
        q_y_90 = np.array([[np.sqrt(.5), 0., np.sqrt(.5), 0.]])
        rotated, _ = covariance_and_world_axis(scales, q_y_90)
        np.testing.assert_allclose(rotated[0], np.diag([1., 4., 16.]), atol=1e-10)

    def test_rejects_zero_quaternion(self):
        with self.assertRaises(ValueError):
            covariance_and_world_axis(np.zeros((1, 3)), np.zeros((1, 4)))

    def test_projected_sigma_removes_known_filter_variance(self):
        image_cov = np.array([[[26., 0.], [0., 5.]]])
        np.testing.assert_allclose(projected_major_sigma(image_cov, floor=1.), [5.])
        with self.assertRaises(ValueError):
            projected_major_sigma(np.array([[[0., 0.], [0., 0.]]]), floor=1.)

    def test_distance_weighting_uses_camera_z_and_focal(self):
        np.testing.assert_allclose(distance_weighted_world_axis(np.array([2., 2.]), np.array([4., 8.]), 100., 100.), [50., 25.])

    def test_dc_color_is_renderer_convention_not_raw_coefficients(self):
        dc = np.array([[0., 0., 0.], [-10., 1., 2.]])
        rgb = sh_dc_rgb(dc)
        np.testing.assert_allclose(rgb[0], [.5, .5, .5])
        self.assertEqual(rgb[1, 0], 0.)
        self.assertGreater(rgb[1, 2], rgb[1, 1])

    def test_fusion_blocks_have_equal_total_variance(self):
        x = np.array([[0.], [1.], [2.], [3.]])
        y = np.column_stack([x[:, 0], x[:, 0] * 2, x[:, 0] * 4])
        fused = equal_block_features([x, y])
        np.testing.assert_allclose(np.var(fused[:, :1], axis=0).sum(), np.var(fused[:, 1:], axis=0).sum(), rtol=1e-6)

    def test_fusion_weight_survives_final_preparation(self):
        x = np.array([[0.], [1.], [2.], [3.]])
        y = np.column_stack([x[:, 0], x[:, 0] * 2, x[:, 0] * 4])
        fused = equal_block_features([x, y])
        final = prepare_arm_features('I_fusion_xyz_sh_projected', fused)
        np.testing.assert_allclose(np.var(final[:, :1], axis=0).sum(), np.var(final[:, 1:], axis=0).sum(), rtol=1e-6)

    def test_fit_manifest_rejects_reserved_or_changed_view(self):
        good = {'scene':'ficus','model':'original.ply','model_sha256':'abc',
                'fit_cameras':[{'view':'train_r_80'},{'view':'train_r_7'}]}
        self.assertEqual([x['view'] for x in validate_fit_manifest(good,'original.ply','abc')],['train_r_80','train_r_7'])
        bad = dict(good,fit_cameras=[{'view':'train_r_80'},{'view':'test_r_14'}])
        with self.assertRaises(ValueError):
            validate_fit_manifest(bad,'original.ply','abc')

    def test_requires_three_populated_clusters(self):
        with self.assertRaises(ValueError):
            validate_partition(np.array([0,0,1,1],dtype='u1'))
        self.assertEqual(validate_partition(np.array([0,1,2,2],dtype='u1')),3)

    @unittest.skipUnless(Path('/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01/renderer.py').exists(), 'remote native renderer fixture')
    def test_native_perspective_sphere_depth_and_off_axis(self):
        import sys
        sys.path.insert(0, '/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01')
        from renderer import project_cov
        c = {'extrinsic':np.eye(4).tolist(), 'fx':100.,'fy':100.,'cx':0.,'cy':0.,'width':200,'height':200}
        means = np.array([[0.,0.,4.],[0.,0.,8.],[1.,0.,4.]])
        cov = np.repeat(np.eye(3)[None,:,:], 3, axis=0)
        _, z, screen = project_cov(means, cov, c, floor=.3)
        np.testing.assert_allclose(z, [4.,8.,4.])
        size=projected_major_sigma(screen, floor=.3)
        np.testing.assert_allclose(size[:2], [25.,12.5], atol=1e-6)
        self.assertGreater(size[2], size[0])


if __name__ == '__main__':
    unittest.main()
