"""Reproduce the archived center/resolution flaw before replacing its path."""
import unittest
from pathlib import Path
import numpy as np
import cv2
from src.foundation import native_render, project_jacobian
from test_multiscene import asset_fixture
try:
    from src.corrected_sampling import resize_intrinsics, area_downsample, render_measurement
except ImportError:
    # Archived path: multiply all K rows and independently splat at target size.
    def resize_intrinsics(K, source_hw, destination_hw):
        K=np.array(K,float).copy();K[0]*=destination_hw[1]/source_hw[1];K[1]*=destination_hw[0]/source_hw[0];return K
    def area_downsample(a):return cv2.resize(a,(a.shape[1]//2,a.shape[0]//2),interpolation=cv2.INTER_AREA)
    def render_measurement(asset,K,w2c,background):
        k=resize_intrinsics(K,(800,800),(400,400))
        return native_render(asset,k,w2c,400,400,background)['stock_rgb']


class SamplingTests(unittest.TestCase):
    def test_source_pixel_centers_map_to_destination_centers(self):
        # Destination j averages source centers 2j and 2j+1, whose centroid is 2j+.5.
        K=np.array([[1100.,0,(800-1)/2],[0,900.,(800-1)/2],[0,0,1]])
        small=resize_intrinsics(K,(800,800),(400,400))
        src=np.array([[.5,.5,1],[798.5,798.5,1],[399.5,399.5,1]])
        mapped=(small@np.linalg.inv(K)@src.T).T
        np.testing.assert_allclose(mapped[:,:2],[[0,0],[399,399],[199.5,199.5]],atol=1e-12)

    def test_full_K_jacobian_matches_resized_pixel_mapping(self):
        K=np.array([[1000.,11.,367.2],[0,800.,413.7],[0,0,1]])
        W=np.eye(4);W[:3,3]=[.3,-.2,1.]
        points=np.array([[.2,.1,3.],[1.,-.5,4.]])
        uv,z,J=project_jacobian(points,K,W)
        small=resize_intrinsics(K,(800,1000),(400,250))
        uvs,zs,Js=project_jacobian(points,small,W)
        np.testing.assert_allclose(uvs,(uv+.5)*[.25,.5]-.5,atol=1e-12)
        np.testing.assert_allclose(Js,J*np.array([.25,.5])[None,:,None],atol=1e-12)
        for axis in range(3):
            p=points.copy();p[:,axis]+=1e-6
            fd=(project_jacobian(p,small,W)[0]-uvs)/1e-6
            np.testing.assert_allclose(fd,Js[:,:,axis],atol=2e-5)

    def test_area_filter_exact_blocks_deterministic_and_no_uint8_rounding(self):
        a=np.random.default_rng(123).random((800,800,4)).astype('f4')
        expected=(a[0::2,0::2].astype('f8')+a[0::2,1::2]+a[1::2,0::2]+a[1::2,1::2])/4
        actual=area_downsample(a)
        np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-7)
        np.testing.assert_array_equal(actual,area_downsample(a))
        ramp=np.indices((800,800))[1].astype('f8')
        np.testing.assert_array_equal(area_downsample(ramp)[0],np.arange(400)*2+.5)

    def test_native800_then_area400_is_not_direct400_splatting(self):
        a=asset_fixture();a['mu'][:]=[[0,0,3],[.02,0,3.1],[0,.01,3.2],[.01,-.01,3.3]]
        a['scale'][:]=[.001,.002,.003]
        K=np.array([[1100.,0,399.5],[0,900.,399.5],[0,0,1]])
        expected=area_downsample(native_render(a,K,np.eye(4),800,800,1)['stock_rgb'])
        direct=native_render(a,resize_intrinsics(K,(800,800),(400,400)),np.eye(4),400,400,1)['stock_rgb']
        self.assertGreater(float(np.abs(expected-direct).max()),.01)
        np.testing.assert_array_equal(render_measurement(a,K,np.eye(4),1),expected)


if __name__=='__main__':unittest.main()

class NativeStockTests(unittest.TestCase):
    def test_stock_native800_equality_and_alpha_replay(self):
        from src.corrected_sampling import stock_intrinsics, stock_reference
        from src.foundation import replay_native, calibration_metrics
        a=asset_fixture();a['scale'][:]=[.03,.12,.06]
        fovx,fovy=.72,.83;K=stock_intrinsics(fovx,fovy)
        W=np.eye(4)
        white=native_render(a,K,W,800,800,1);black=native_render(a,K,W,800,800,0)
        stock=stock_reference(a,W,fovx,fovy,1)
        np.testing.assert_allclose(stock,white['stock_rgb'],atol=1e-6,rtol=0)
        replay=replay_native(white,800,800,np.zeros(4,bool),np.zeros(4,bool),1)
        self.assertTrue(calibration_metrics(white,black['stock_rgb'],replay)['passed'])
        np.testing.assert_allclose(area_downsample(stock),area_downsample(white['stock_rgb']),atol=1e-6,rtol=0)
