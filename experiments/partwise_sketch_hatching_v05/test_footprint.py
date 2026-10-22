"""Full accepted-footprint instrumentation and abstention regression fixtures."""
import runtime
import unittest
import numpy as np
from footprint import FootprintRenderer, resolve_footprint


class FootprintTests(unittest.TestCase):
    def test_all_pixels_match_events_after_culling_and_sort(self):
        r = FootprintRenderer(runtime.ACTIVE_UNIT/'build')
        c = dict(extrinsic=np.eye(4).tolist(), width=16, height=16,
                 fx=12., fy=12., cx=7., cy=7.)
        a = dict(means=np.array([[0,0,2.], [0,0,.1], [0,0,1.]]),
                 covariance=np.tile(np.eye(3)*.01,(3,1,1)),
                 opacity=np.array([.8,.9,.9]), colors=np.eye(3),
                 source_index=np.array([10,2,7]))
        y,x=np.mgrid[:16,:16]; xy=np.column_stack([x.ravel(),y.ravel()])
        category=np.full((16,16),2,np.int32);category[5:10,5:10]=1;category[7,7]=0
        depth=np.ones((16,16));valid=np.ones((16,16),bool)
        f,t,stats=r.footprint(a,c,category,depth,valid,xy)
        off,_=r.render(a,c);baseline=r.baseline(a,c)
        for k in baseline:
            np.testing.assert_array_equal(f[k],off[k])
            np.testing.assert_array_equal(f[k],baseline[k])
        expected=np.zeros((3,5))
        lookup={10:0,2:1,7:2}
        for sid,gid,w,z in zip(t['sample_index'],t['source_index'],t['weight'],t['depth']):
            i=lookup[int(gid)];xx,yy=xy[sid];cat=category[yy,xx]
            expected[i,0]+=w;expected[i,cat+1]+=w
            if cat==0 and abs(z-depth[yy,xx])<=.06:expected[i,4]+=w
        np.testing.assert_allclose(stats,expected,rtol=0,atol=1e-12)
        self.assertEqual(stats[1].sum(),0)
        self.assertGreater(stats[0,1],0)
        self.assertEqual(stats[0,4],0)  # Visible back layer, incompatible depth.
        self.assertGreater(stats[2,4],0)
        np.testing.assert_allclose(stats[:,1:4].sum(1),stats[:,0],atol=1e-12)

    def test_far_footprint_abstains_and_preserves_unknown(self):
        # total / inside / band / far / depth-consistent inside.
        pv=np.array([[[1,.8,.19,.01,.8],[1,.7,.1,.2,.7],[0,0,0,0,0],[1,.9,.1,0,.9]],
                     [[1,.8,.19,.01,.8],[1,.7,.1,.2,.7],[0,0,0,0,0],[1,.9,.1,0,.9]]])
        old=dict(strength=np.array([.8,.8,0.,0.]),unknown=np.array([False,False,True,True]))
        q=resolve_footprint(pv,old)
        np.testing.assert_array_equal(q['strength'],[.8,0,0,0])
        self.assertEqual(q['reason'][1],'far_footprint')
        self.assertEqual(q['reason'][2],'footprint_unobserved')
        self.assertEqual(q['reason'][3],'prior_path_unknown')
        self.assertTrue(q['unknown'][1:].all())


if __name__=='__main__':unittest.main()
