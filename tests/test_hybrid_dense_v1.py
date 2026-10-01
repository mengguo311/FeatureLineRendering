import unittest
import numpy as np
from hybrid_dense_v1 import compose

class DenseHybridTests(unittest.TestCase):
    def test_keeps_distinct_image_and_object_ink(self):
        obj=np.zeros((9,9),dtype=np.float32); obj[4,1:4]=1
        rgb=np.zeros((9,9),dtype=np.uint8); rgb[4,7]=1
        depth=np.zeros((9,9),dtype=np.uint8)
        alpha=np.ones((9,9),dtype=np.float32)
        layers=compose(obj,rgb,depth,alpha)
        self.assertTrue(layers['object'][4,2]);self.assertTrue(layers['image'][4,7]);self.assertTrue(layers['hybrid'][4,7]);self.assertGreater(layers['hybrid'].sum(),layers['object'].sum())
    def test_alpha_masks_background_texture_and_dedupes_near_object(self):
        obj=np.zeros((9,9),dtype=np.float32);obj[4,4]=1
        rgb=np.zeros((9,9),dtype=np.uint8);rgb[4,4]=1;rgb[0,0]=1
        depth=np.zeros((9,9),dtype=np.uint8);alpha=np.zeros((9,9),dtype=np.float32);alpha[2:7,2:7]=1
        layers=compose(obj,rgb,depth,alpha)
        self.assertFalse(layers['image'][0,0]);self.assertFalse(layers['image'][4,4]);self.assertTrue(layers['hybrid'][4,4])

if __name__=='__main__':unittest.main()
