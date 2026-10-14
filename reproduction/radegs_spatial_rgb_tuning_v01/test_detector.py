import unittest,inspect,hashlib
import numpy as np
import boundary
from detector import mix_fields,candidate,analyze_rgb,rgb_from_npz

class DetectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Analytic image, not a claimed scene or ground-truth segmentation.
        y,x=np.mgrid[:96,:128]
        cls.rgb=np.repeat((.45+.05*(x>36)+.09*np.sin(x*.75)*(x>72))[...,None],3,-1).astype(np.float32)
        cls.fields=boundary.analyze(cls.rgb)
    def test_original_union_bitexact(self):
        np.testing.assert_array_equal(mix_fields(self.fields,1.),self.fields['union'])
    def test_structural_only_exact(self):
        np.testing.assert_array_equal(mix_fields(self.fields,0.),self.fields['structural'])
    def test_detail_not_silently_structural_filtered(self):
        f={'structural':np.array([[0,.6]],np.float32),'detail':np.array([[.8,.2]],np.float32)}
        np.testing.assert_array_equal(mix_fields(f,1),np.array([[.8,.6]],np.float32))
    def test_strict_not_greater_equal_threshold(self):
        s=np.array([[0,.2,.4,.8]],np.float32)
        r=candidate(s,.2,sigma=0)
        self.assertFalse(r['marked'][0,1]);self.assertTrue(r['marked'][0,2])
    def test_masks_nested_at_six_thresholds(self):
        previous=np.ones(self.rgb.shape[:2],bool)
        for t in [.1,.15,.2,.3,.4,.5]:
            out=candidate(self.fields['union'],t)
            self.assertFalse(np.any(out['marked']&~previous));previous=out['marked']
    def test_decreasing_lambda_never_adds_candidate(self):
        previous=np.ones(self.rgb.shape[:2],bool)
        for lam in [1,.75,.5,.25,0]:
            m=candidate(mix_fields(self.fields,lam),.2)['marked']
            self.assertFalse(np.any(m&~previous));previous=m
    def test_finite_and_range(self):
        for lam in [0,.25,.5,.75,1]:
            r=candidate(mix_fields(self.fields,lam),.2)
            for key in ['soft','darkness','candidate_darkness']:
                a=r[key];self.assertTrue(np.isfinite(a).all());self.assertTrue((a>=0).all() and (a<=1).all())
    def test_constant_background_no_false_lines(self):
        f=analyze_rgb(np.full((40,52,3),.3,np.float32),'native')
        self.assertEqual(int(candidate(f['union'],.1)['marked'].sum()),0)
    def test_fixed_gain_not_threshold_renormalization(self):
        a=candidate(self.fields['union'],.1);b=candidate(self.fields['union'],.4)
        np.testing.assert_array_equal(a['darkness'],b['darkness'])
        np.testing.assert_array_equal(b['candidate_darkness'][b['marked']],a['darkness'][b['marked']])
    def test_skeleton_subset(self):
        r=candidate(self.fields['union'],.2)
        self.assertFalse(np.any(r['skeleton']&~r['marked']))
    def test_repeat_deterministic(self):
        a=analyze_rgb(self.rgb,'native');b=analyze_rgb(self.rgb.copy(),'native')
        for k in ['detail','structural','union']:np.testing.assert_array_equal(a[k],b[k])
    def test_rgb_only_interface_and_no_input_mutation(self):
        a=self.rgb.copy();before=hashlib.sha256(a.tobytes()).hexdigest();analyze_rgb(a,'native')
        self.assertEqual(before,hashlib.sha256(a.tobytes()).hexdigest())
        self.assertEqual(list(inspect.signature(analyze_rgb).parameters),['rgb','analysis'])
        with self.assertRaises(TypeError):analyze_rgb(a,'native',depth=np.ones(a.shape[:2]))
    def test_npz_loader_only_queries_rgb(self):
        class RGBOnly:
            def __getitem__(self,key):
                if key!='rgb':raise AssertionError('Accessed non-RGB input')
                return DetectorTests.rgb
        np.testing.assert_array_equal(rgb_from_npz(RGBOnly()),self.rgb)
    def test_original_source_sha(self):
        from pathlib import Path
        self.assertEqual(hashlib.sha256(Path(boundary.__file__).read_bytes()).hexdigest(),'11bbb41a762f252d9eeb4ea3f0a8399ed026139d9490bb8cf161bc815e05dd30')
    def test_preserve_float32_hdr_values(self):
        r=np.ones((40,52,3),np.float32);r[:,26:]=1.1
        a=analyze_rgb(r,'native');b=boundary.analyze(r)
        np.testing.assert_array_equal(a['union'],b['union'])
        self.assertGreater(float(a['magnitude'].max()),0)
    def test_display_exact_candidate_gate(self):
        r=candidate(self.fields['union'],.2)
        np.testing.assert_array_equal(r['candidate_darkness'],r['darkness']*r['marked'])

if __name__=='__main__':unittest.main(verbosity=2)
