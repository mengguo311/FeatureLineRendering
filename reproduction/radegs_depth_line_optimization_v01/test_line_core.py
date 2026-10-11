import unittest
import numpy as np
from line_core import soft_distance, normalized_inverse, features, trace, optimize, visibility_confidence

def cam(h=96,w=128):
    return dict(fx=180.,fy=180.,width=w,height=h,extrinsic=np.eye(4).tolist())

class CoreTests(unittest.TestCase):
    def test_nonfinite_safe_and_invalid_excluded(self):
        z=np.full((96,128),2.,np.float32);a=np.ones_like(z)
        z[40,30]=np.nan;z[30,30]=np.inf;z[20,30]=0;a[50,30]=np.nan
        r=optimize(z,a,cam())
        for key in ['response','confidence','distance_weight']:
            self.assertTrue(np.isfinite(r[key]).all(),key)
        self.assertFalse(r['lines'][40,30]);self.assertFalse(r['lines'][50,30])
        self.assertLess(r['confidence'][40,31],r['confidence'][40,70])
    def test_empty_input(self):
        z=np.full((96,128),np.nan);r=optimize(z,np.zeros_like(z),cam())
        self.assertFalse(r['lines'].any());self.assertTrue(np.isfinite(r['response']).all())
    def test_object_crosses_old_cut_without_zero_support(self):
        z=np.tile(np.linspace(1,2.5,128),(96,1));v=np.ones_like(z,bool)
        oldcut=np.percentile(z[20:76,26:102],20)*1.15
        self.assertTrue((z>oldcut).any())
        w=soft_distance(z,v)
        self.assertTrue((w[z>oldcut]>=.25).all());self.assertTrue((w>0).all())
        self.assertLess(np.max(np.abs(np.diff(w,axis=1))),.04)
    def test_perspective_plane_no_cutoff_contour(self):
        u=np.indices((96,128))[1];z=1/(.4+.003*u)
        r=optimize(z,np.ones_like(z),cam())
        self.assertLess(np.max(r['response'][18:-18,18:-18]),1e-4)
        self.assertFalse(r['lines'][18:-18,18:-18].any())
    def test_missing_sample_does_not_pollute_fit(self):
        z=np.full((96,128),2.);v=np.ones_like(z,bool);z[48,64]=np.nan;v[48,64]=False
        q,c=normalized_inverse(z,v,2.)
        np.testing.assert_allclose(q,.5,atol=1e-7)
        self.assertLess(c[48,64],1.);self.assertGreater(c[48,65],0.)
    def test_strong_seed_keeps_continuous_weak_segment(self):
        r=np.zeros((40,80),np.float32);r[20,10:65]=.025;r[20,10:18]=.1
        d=np.full_like(r,np.pi/2);v=np.ones_like(r,bool);c=np.ones_like(r)
        a=trace(r,d,v,c)
        self.assertTrue(a[20,10:65].all())
        r[20,10:18]=.025
        self.assertFalse(trace(r,d,v,c).any())
    def test_confidence_never_draws_its_boundary(self):
        r=np.zeros((40,80),np.float32);c=np.zeros_like(r);c[:,:40]=1
        self.assertFalse(trace(r,r,np.ones_like(r,bool),c).any())
    def test_confidence_scores_whole_fragment(self):
        r=np.zeros((40,80),np.float32);r[20,10:65]=.08
        d=np.full_like(r,np.pi/2);c=np.ones_like(r);c[:,40:]=.5
        a=trace(r,d,np.ones_like(r,bool),c)
        self.assertTrue(a[20,10:65].all())
    def test_same_camera_deterministic(self):
        u=np.indices((96,128))[1];z=2+.08*np.tanh((u-64)/3)
        a=optimize(z,np.ones_like(z),cam());b=optimize(z,np.ones_like(z),cam())
        self.assertTrue(a['lines'].any())
        for k in a:np.testing.assert_array_equal(a[k],b[k])
    def test_visibility_agreement_occlusion_contradiction(self):
        z=np.full((96,128),2.);v=np.ones_like(z,bool);c=cam()
        equal=visibility_confidence(z,v,c,[(z,v,c)])
        occluded=visibility_confidence(z,v,c,[(z*.5,v,c)])
        conflict=visibility_confidence(z,v,c,[(z*1.5,v,c)])
        self.assertGreater(equal['weight'][48,64],occluded['weight'][48,64])
        self.assertGreater(occluded['weight'][48,64],conflict['weight'][48,64])
        self.assertEqual(occluded['observations'][48,64],0)

if __name__=='__main__':unittest.main()
