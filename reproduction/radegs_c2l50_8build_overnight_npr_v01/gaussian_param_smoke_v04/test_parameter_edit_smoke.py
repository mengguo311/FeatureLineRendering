import unittest
import numpy as np
from parameter_edit_smoke import masked_source_asset, calibration_mae, foreground_mae


class NativeEditSmokeTests(unittest.TestCase):
    def test_opacity_edit_only_changes_selected_original_rows(self):
        a={'means':np.array([[1.,0.,0.],[2.,0.,0.],[3.,0.,0.]]),
           'opacity':np.array([.2,.5,.8]), 'SH':np.zeros((3,3,1))}
        labels=np.array([0,1,0],dtype='u1')
        edited=masked_source_asset(a,labels,1)
        np.testing.assert_array_equal(edited['opacity'],[.2,0.,.8])
        np.testing.assert_array_equal(a['opacity'],[.2,.5,.8])
        self.assertIs(edited['means'],a['means'])
        self.assertIs(edited['SH'],a['SH'])
        with self.assertRaises(ValueError):
            masked_source_asset(a,labels[:2],1)

    def test_calibration_rejects_bad_rgb_alpha(self):
        result={'rgb':np.zeros((2,2,3)), 'alpha':np.zeros((2,2))}
        good={'rgb':np.zeros((2,2,3)), 'alpha':np.zeros((2,2))}
        self.assertEqual(calibration_mae(result,good), (0.,0.))
        bad={'rgb':np.ones((2,2,3)), 'alpha':np.zeros((2,2))}
        self.assertEqual(calibration_mae(result,bad)[0],1.)

    def test_nan_must_never_pass_calibration(self):
        result={'rgb':np.full((2,2,3),np.nan), 'alpha':np.zeros((2,2))}
        good={'rgb':np.zeros((2,2,3)), 'alpha':np.zeros((2,2))}
        with self.assertRaises(ValueError):
            calibration_mae(result,good)

    def test_foreground_mae_rejects_empty_and_uses_only_subject(self):
        reference={'rgb':np.zeros((2,2,3)), 'alpha':np.array([[1.,0.],[0.,0.]])}
        rendered={'rgb':np.zeros((2,2,3)), 'alpha':np.zeros((2,2))}
        rendered['rgb'][1,1]=1.
        self.assertEqual(foreground_mae(rendered,reference), (0.,1.))
        with self.assertRaises(ValueError):
            foreground_mae(rendered,{'rgb':reference['rgb'],'alpha':np.zeros((2,2))})

if __name__=='__main__':
    unittest.main()
