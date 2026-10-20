"""Independent toy RED/GREEN checks, not the frozen sequence."""
import round015_common
import sys,unittest
import numpy as np
import planar_temporal_metrics as m
BROKEN='--broken' in sys.argv
if BROKEN:sys.argv.remove('--broken')
class Metrics(unittest.TestCase):
    def setUp(self):
        self.ref=np.zeros((3,24,24),np.uint8);self.ref[:,:,10]=255
        self.uv=np.tile([[10.,10.],[10.,12.]],(3,1,1));self.n=np.array([1.,0.]);self.e=np.ones((3,2),bool);self.o=np.linspace(-2,2,33)
    def call(self,x):
        if BROKEN:x=self.ref # Forbidden coordinate-only/no-output-response surrogate.
        return m.compare(x,self.ref,self.uv,self.n,self.e,self.o,8/255.)[0]
    def test_reference_has_zero_extra_error(self):
        r=self.call(self.ref);self.assertEqual(r['full_frame_L1_uint8'],0);self.assertEqual(r['extra_centroid_abs_px']['max'],0)
    def test_transverse_drift_responds(self):
        x=self.ref.copy();x[1]=m.translated(x[1],1,0);r=self.call(x)
        self.assertGreater(r['extra_centroid_abs_px']['max'],.99);self.assertGreater(r['temporal_residual_L1_uint8'],0)
    def test_dropout_not_silently_excluded(self):
        x=self.ref.copy();x[1]=0;r=self.call(x);self.assertEqual(r['extra_dropout_samples'],2)
    def test_full_frame_detects_unmatched_ink(self):
        x=self.ref.copy();x[1,0,0]=255;self.assertEqual(self.call(x)['full_frame_L1_uint8'],255)
    def test_shift_has_no_wrap(self):
        x=np.zeros((4,4),np.uint8);x[0,3]=255;self.assertEqual(m.translated(x,1,0).sum(),0)
    def test_resize_pixel_center_mapping(self):
        # PIL output sample centers for exact 2x BOX reduction, including origin.
        from PIL import Image
        ramp=np.tile(np.arange(16,dtype=np.float32),(16,1))
        down=np.array(Image.fromarray(ramp).resize((8,8),Image.Resampling.BOX))
        high=2*(np.arange(8)+.5)-.5
        np.testing.assert_array_equal(down[0],high)
        np.testing.assert_array_equal((high+.5)/2-.5,np.arange(8))
if __name__=='__main__':unittest.main(verbosity=2)
