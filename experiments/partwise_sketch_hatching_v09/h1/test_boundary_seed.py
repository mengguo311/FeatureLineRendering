import runtime,unittest
import numpy as np
from screen_hatch import generate

class BoundarySeedTest(unittest.TestCase):
    def test_requested_segment_intersects_mask_with_center_outside(self):
        mask=np.zeros((40,40),bool);mask[10:20,10:20]=True
        depth=np.ones((40,40))*3;field=np.zeros((40,40,2));field[:,:,0]=1
        cfg=dict(spacing_px=4.,length_px=30.,gap_px=2.,phase=[0.,0.],step_px=.5,depth_jump=.035)
        paths,record=generate(field,mask,depth,[4.,14.],[1.,0.],cfg)
        self.assertGreater(len(paths),0)
        p=np.concatenate(paths)
        self.assertLessEqual(p[:,0].min(),10.)
        self.assertGreaterEqual(p[:,0].max(),19.)
if __name__=='__main__':unittest.main()
