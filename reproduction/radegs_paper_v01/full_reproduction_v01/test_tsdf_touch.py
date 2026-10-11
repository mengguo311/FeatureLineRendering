"""Real Open3D CPU RED/GREEN, including actual failing exported view."""
import json
from pathlib import Path
import unittest
import numpy as np
from PIL import Image
import open3d as o3d
from tsdf_touch import touch_blocks

HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')


def grid():
    return o3d.t.geometry.VoxelBlockGrid(attr_names=('tsdf','weight'),
        attr_dtypes=(o3d.core.float32,o3d.core.float32),attr_channels=(1,1),
        voxel_size=.002,block_resolution=16,block_count=8,device=o3d.core.Device('CPU:0'))


class TouchTests(unittest.TestCase):
    def test_real_view_0025_must_not_lose_22_valid_depth_pixels(self):
        model=HDD/'models/scan24_paper_text_half_30k/depth_normal'
        cam=next(v for v in json.loads((model/'cameras_and_conventions.json').read_text()) if v['view']=='0025')
        with np.load(model/'0025.npz') as z:
            d=z['median_camera_z'][0].copy();alpha=z['alpha'][0]
        mask=np.asarray(Image.open(HDD/'data/prepared/scan24/images/0025.png').split()[3].resize((777,581)))/255
        d[(mask<.5)|(alpha<.5)]=0
        self.assertEqual(int(((d>0)&(d<8)).sum()),22)
        self.assertEqual(int((d[:580:4,:776:4]>0).sum()),0)
        k=np.array([[cam['fx'],0,777/2],[0,cam['fy'],581/2],[0,0,1]],np.float64)
        coords,info=touch_blocks(grid(),d,k,np.asarray(cam['extrinsic'],np.float64))
        self.assertGreater(coords.shape[0],0)
        self.assertEqual(info['valid_pixels'],22)
        print('actual_view_0025',info,flush=True)

    def test_dense_input_keeps_original_native_allocation(self):
        d=np.full((8,8),1.13,np.float32);k=np.array([[40,0,4],[0,41,4],[0,0,1]],np.float64);e=np.eye(4)
        actual,info=touch_blocks(grid(),d,k,e)
        expected=grid().compute_unique_block_coordinates(o3d.t.geometry.Image(d),o3d.core.Tensor(k),o3d.core.Tensor(e),1.,8.)
        self.assertEqual(set(map(tuple,actual.numpy())),set(map(tuple,expected.numpy())))
        self.assertEqual(info['mode'],'C24_NATIVE_STRIDE4')

    def test_single_sparse_ray_uses_same_four_truncation_samples(self):
        d=np.zeros((8,8),np.float32);d[1,1]=1.13
        k=np.array([[1,0,1],[0,1,1],[0,0,1]],np.float64)
        e=np.eye(4);e[:3,3]=[-.005,-.006,-.007]
        coords,info=touch_blocks(grid(),d,k,e)
        expected={(0,0,int(np.floor((.007+t)/.032))) for t in np.linspace(1.13-.016,1.13+.016,4)}
        self.assertEqual(set(map(tuple,coords.numpy())),expected)
        self.assertEqual(info['mode'],'SPARSE_VALID_DEPTH_STRIDE1_FALLBACK')

    def test_truly_empty_view_is_explicit_no_contribution(self):
        coords,info=touch_blocks(grid(),np.zeros((8,8),np.float32),np.eye(3),np.eye(4))
        self.assertIsNone(coords)
        self.assertEqual(info['mode'],'EMPTY_VALID_DEPTH_NO_CONTRIBUTION')
        self.assertEqual(info['valid_pixels'],0)

    def test_nonfinite_input_fails_closed(self):
        d=np.ones((8,8),np.float32);d[1,1]=np.nan
        with self.assertRaises(ValueError):touch_blocks(grid(),d,np.eye(3),np.eye(4))


if __name__=='__main__':unittest.main(verbosity=2)
