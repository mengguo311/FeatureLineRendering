"""Actual corrected view0033: original API RED, frozen sparse bridge GREEN."""
import json,sys,unittest
from pathlib import Path
import numpy as np
from PIL import Image
import open3d as o3d
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tsdf_touch import touch_blocks
BRIDGE='--bridge' in sys.argv
if BRIDGE:sys.argv.remove('--bridge')
class RealSparseView(unittest.TestCase):
    def test_original_threshold_valid_depth_must_allocate(self):
        h=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');m=h/'models/scan24_paper_text_precision_v01_half_30k'
        cam=next(c for c in json.loads((m/'depth_normal/cameras_and_conventions.json').read_text()) if c['view']=='0033')
        w,hh=cam['width'],cam['height']
        with np.load(m/'depth_normal/0033.npz') as z:d=z['median_camera_z'][0].copy();a=z['alpha'][0]
        mask=np.asarray(Image.open(h/'data/prepared/scan24/images/0033.png').split()[3].resize((w,hh)))/255
        d[(mask<.5)|(a<.5)]=0
        valid=(d>0)&(d<8)&np.isfinite(d)
        self.assertGreater(int(valid.sum()),0);self.assertEqual(int(valid[:hh//4*4:4,:w//4*4:4].sum()),0)
        k=np.array([[cam['fx'],0,w/2],[0,cam['fy'],hh/2],[0,0,1]],np.float64);e=np.asarray(cam['extrinsic'],np.float64)
        v=o3d.t.geometry.VoxelBlockGrid(attr_names=('tsdf','weight'),attr_dtypes=(o3d.core.float32,o3d.core.float32),attr_channels=(1,1),voxel_size=.002,block_resolution=16,block_count=50000,device=o3d.core.Device('CPU:0'))
        if BRIDGE:coords,detail=touch_blocks(v,d,k,e);self.assertEqual(detail['mode'],'SPARSE_VALID_DEPTH_STRIDE1_FALLBACK')
        else:coords=v.compute_unique_block_coordinates(o3d.t.geometry.Image(d),o3d.core.Tensor(k),o3d.core.Tensor(e),1.,8.)
        self.assertGreater(len(coords),0)
if __name__=='__main__':unittest.main()
