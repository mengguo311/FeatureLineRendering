import unittest
import numpy as np
from hybrid_overlay_video import overlay_ink

class OverlayTests(unittest.TestCase):
    def test_lines_on_same_rgb_without_geometry_change(self):
        rgb=np.full((7,7,3),[100,130,180],dtype=np.uint8)
        obj=np.zeros((7,7),bool); obj[3,3]=True
        image=np.zeros((7,7),bool); image[1,1]=True
        out=overlay_ink(rgb,obj,image)
        self.assertEqual(out.shape,rgb.shape)
        self.assertTrue(np.array_equal(out[6,6],rgb[6,6]))
        self.assertTrue(np.array_equal(out[3,3],[255,90,20]))
        self.assertTrue(np.array_equal(out[1,1],[10,10,10]))
        self.assertTrue(np.array_equal(rgb[3,3],[100,130,180]))
    def test_rejects_size_mismatch(self):
        with self.assertRaises(ValueError):
            overlay_ink(np.zeros((7,7,3),np.uint8),np.zeros((8,8),bool),np.zeros((7,7),bool))

if __name__=='__main__':unittest.main()
