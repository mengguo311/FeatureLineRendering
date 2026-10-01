import unittest
import numpy as np
from scripts.run_hao_mukai_video import compose_frame

class VideoDisplayTests(unittest.TestCase):
    def test_fixed_gain_and_three_distinct_panels(self):
        rgb=np.zeros((8,8,3),np.float32); rgb[:,:,0]=1.
        s=np.ones((8,8),np.float32)*.25
        frame=compose_frame(rgb,s,.5,frame_index=0,frame_total=1,size=64)
        self.assertEqual(frame.shape,(64+76,64*3,3))
        # RGB proxy, unmodified absolute density and fixed-gain display differ.
        self.assertFalse(np.array_equal(frame[76:,:64],frame[76:,64:128]))
        self.assertFalse(np.array_equal(frame[76:,64:128],frame[76:,128:]))
        self.assertEqual(int(frame[90,90,0]),191)  # raw 1-0.25
        self.assertEqual(int(frame[90,150,0]),127) # fixed gain 1-0.25/0.5

if __name__=='__main__':unittest.main()
