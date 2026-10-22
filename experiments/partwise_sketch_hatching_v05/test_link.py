"""Focused acceptance/ID/visibility and saved-binding tests; no GPU."""
import runtime
import unittest
import tempfile
from pathlib import Path
import numpy as np
from link_renderer import Renderer, prepare
from membership import accumulate, resolve, save_binding, load_binding, tint_copy

BUILD=runtime.ACTIVE_UNIT/'build'

def camera():
    return dict(extrinsic=np.eye(4).tolist(),width=16,height=16,fx=12.,fy=12.,cx=7.,cy=7.)

def fixture():
    # Row 0 culled; surviving order is 2,3,1,4,5. Opaque early stop rejects row 4.
    z=np.array([.1,3.,1.,2.,4.,5.])
    means=np.zeros((6,3));means[:,2]=z
    return dict(means=means,covariance=np.tile(np.eye(3)*.01,(6,1,1)),
        opacity=np.array([.5,.99,.99,.99,.7,.5]),
        colors=np.arange(18).reshape(6,3)/20.)

class TraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=Renderer(BUILD)

    def test_identity_culling_sort_and_early_stop(self):
        a=fixture();c=camera();f,t=self.r.render(a,c,[[7,7]])
        np.testing.assert_array_equal(t['source_index'],[2,3])
        np.testing.assert_allclose(t['weight'],[.99,.0099],atol=1e-15)
        np.testing.assert_allclose(t['T'],[1.,.01],atol=1e-15)
        self.assertNotIn(0,t['source_index']);self.assertNotIn(1,t['source_index'])

    def test_trace_on_off_original_outputs_and_rgb(self):
        a=fixture();c=camera();xy=np.array([[7,7],[6,7],[0,0]])
        f,t=self.r.render(a,c,xy);off,_=self.r.render(a,c)
        ref=self.r.baseline(a,c)
        for k in ref:
            np.testing.assert_array_equal(f[k],off[k]);np.testing.assert_array_equal(f[k],ref[k])
        for s,(x,y) in enumerate(xy):
            mask=t['sample_index']==s;ids=t['source_index'][mask];w=t['weight'][mask]
            self.assertAlmostEqual(w.sum(),float(f['alpha'][y,x]),places=6)
            rgb=(w[:,None]*a['colors'][ids]).sum(0)+1-w.sum()
            np.testing.assert_allclose(rgb,f['rgb'][y,x],atol=6e-8)

    def test_explicit_permuted_ids_and_capture_bound(self):
        a=fixture();a['source_index']=np.array([55,12,92,8,1,64],np.int64)
        _,t=self.r.render(a,camera(),[[7,7]])
        np.testing.assert_array_equal(t['source_index'],[92,8])
        with self.assertRaisesRegex(RuntimeError,'overflow'):
            self.r.render(a,camera(),[[7,7]],max_events=1)
        with self.assertRaises(ValueError):self.r.render(a,camera(),[[7,7],[7,7]])

    def test_alpha_cutoff_and_cap(self):
        a=fixture();a['opacity'][:]=.001
        f,t=self.r.render(a,camera(),[[7,7]])
        self.assertEqual(len(t['weight']),0);self.assertEqual(f['alpha'][7,7],0.)
        a['opacity'][2]=1.
        _,t=self.r.render(a,camera(),[[7,7]])
        self.assertEqual(t['alpha'][0],.99)

class BindingTests(unittest.TestCase):
    def test_mixed_depth_unknown_and_conflict(self):
        # Two samples: one target layer, one non-target layer; back kernel rejected.
        trace=dict(sample_index=np.array([0,0,1]),source_index=np.array([0,1,0]),
                   weight=np.array([.7,.2,.8]),depth=np.array([1.,2.,1.]))
        score,exposure,reasons=accumulate(3,trace,np.array([4,2]),np.array([1.,1.]),
                                       np.array([True,True]),np.ones(2),.06)
        self.assertAlmostEqual(score[0,4],.7);self.assertAlmostEqual(score[0,2],.8)
        self.assertEqual(score[1,0],.2);self.assertEqual(reasons['depth_rejected_mass'],.2)
        s=np.stack([score,score]);out=resolve(s,.02,2,.7,.002)
        self.assertEqual(out['region_id'][0],0);self.assertEqual(out['region_id'][1],0)
        self.assertTrue(out['unknown'][2]);self.assertEqual(out['exposure'][2],0)
        s=np.zeros((2,3,6));s[0,0,4]=1;s[1,0,2]=1
        self.assertTrue(resolve(s,.02,2,.7,.002)['conflict'][0])

    def test_save_load_source_lock_and_reversible_tint(self):
        s=np.zeros((2,3,6));s[:,0,4]=1;s[:,1,2]=1
        out=resolve(s,.02,2,.7,.002)
        a=dict(means=np.zeros((3,3)),covariance=np.tile(np.eye(3),(3,1,1)),
               opacity=np.ones(3),SH=np.ones((3,3,16)))
        edited=tint_copy(a,np.array([.8,0,0]),[.05,.35,1.])
        np.testing.assert_array_equal(a['SH'],np.ones((3,3,16)))
        np.testing.assert_array_equal(a['SH'][1:],edited['SH'][1:])
        self.assertIs(edited['means'],a['means']);self.assertIs(edited['opacity'],a['opacity'])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'binding.npz';save_binding(p,out,{'source_sha256':'abc','source_count':3})
            b,m=load_binding(p,'abc',3)
            np.testing.assert_array_equal(b['membership'],out['membership'])
            with self.assertRaises(ValueError):load_binding(p,'wrong',3)

if __name__=='__main__':unittest.main()
