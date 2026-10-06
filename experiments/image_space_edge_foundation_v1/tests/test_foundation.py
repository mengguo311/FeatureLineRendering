"""Independent interface truth: no labels derived from the detector."""
import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from boundary import analyze, control_width, temporal_pair,remap
from fixtures import fixtures, moving_sequence

class FoundationTests(unittest.TestCase):
    def test_full_object_many_profiles_remap(self):
        im=np.full((128,128,3),.55,np.float32)
        x=np.full((40000,19),64,np.float32);y=x.copy()
        self.assertEqual(remap(im,x,y).shape,(40000,19,3))
    def test_constant_plane_has_no_ink(self):
        im,truth=fixtures()['constant']; r=analyze(im)
        self.assertLess(float(r['union'].max()),1e-5)
        self.assertEqual(len(r['profiles']['xy']),0)

    def test_color_opponent_edge_even_when_luminance_equal(self):
        im,t=fixtures()['color_step']; r=analyze(im); x=t['center']
        self.assertGreater(float(r['union'][15:-15,x-2:x+3].max(axis=1).mean()),.25)
        self.assertGreater(np.count_nonzero(r['profiles']['valid']),60)
        p=r['profiles']; keep=p['valid']
        self.assertLess(float(np.median(np.abs(p['center'][keep]))),1.1)
        self.assertLess(float(np.median(np.abs(p['width'][keep]-t['width']))),1.6)
        self.assertGreater(float(np.mean(p['signed_contrast'][keep,0])),.1)

    def test_low_contrast_unknown_is_not_structural(self):
        im,t=fixtures()['low_contrast']; r=analyze(im)
        self.assertEqual(np.count_nonzero(r['profiles']['valid']),0)
        self.assertGreater(float(r['detail'].max()),.02)

    def test_legitimate_stripes_stay_in_union(self):
        im,t=fixtures()['stripes']; r=analyze(im)
        band=t['truth']>0
        self.assertGreater(float(np.mean(r['union'][band])),.2)
        self.assertTrue(np.all(r['union']+1e-6>=r['detail']))

    def test_corner_junction_not_forced_into_profiles(self):
        for k in ['corner','junction']:
            im,t=fixtures()[k]; r=analyze(im)
            self.assertGreater(float(r['union'][t['truth']>0].mean()),.12)
            self.assertEqual(r['normal'].shape,(*im.shape[:2],2))
            self.assertTrue(np.isfinite(r['normal']).all())

    def test_width_control_preserves_band_and_plateaus(self):
        im,t=fixtures()['width']; r=analyze(im)
        a,ga=control_width(im,r,.65); b,gb=control_width(im,r,1.5)
        self.assertGreater(float(np.max(np.abs(a-im))),.005)
        self.assertGreaterEqual(float(a.min()),float(im.min())-1e-6)
        self.assertLessEqual(float(b.max()),float(im.max())+1e-6)
        self.assertTrue(np.array_equal(a[~ga['band']],im[~ga['band']]))
        self.assertEqual(ga['outside_max'],0.)
        self.assertLessEqual(ga['max_delta'],.080001)
        self.assertGreater(float(np.abs(b-im).max()),.005)

    def test_disocclusion_and_vanishing_edges_do_not_ghost(self):
        seq=moving_sequence()
        prev=analyze(seq[0])['union']
        for a,b in zip(seq[:-1],seq[1:]):
            current=analyze(b)['union']; out,meta=temporal_pair(a,b,prev,current)
            self.assertTrue(np.isfinite(out).all())
            self.assertLessEqual(float(out[current==0].max(initial=0)),1e-6)
            self.assertLessEqual(float(np.abs(out-current).max()),.120001)
            prev=out
        self.assertLess(float(prev.max()),1e-4)

if __name__=='__main__': unittest.main()
