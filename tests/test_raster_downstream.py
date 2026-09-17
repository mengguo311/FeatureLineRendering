import unittest
import numpy as np
from scripts.run_raster_candidates import merged_pool
from raster_candidate_outputs import path_order,prefix_mask,orbit
from src.common import Camera


class DownstreamTest(unittest.TestCase):
    def test_preserve_original_linelets_and_empty_null(self):
        p=np.arange(30,dtype=float).reshape(10,3)
        base=dict(p0=p,t=np.tile([1.,0,0],(10,1)),l=np.ones(10))
        empty=dict(p=np.empty((0,3)),t=np.empty((0,3)),l=np.empty(0))
        a=merged_pool(base,empty)
        extra=dict(p=np.array([[2.,3.,9.]]),t=np.array([[0.,1.,0.]]),l=np.array([.25]))
        b=merged_pool(base,extra)
        for k in ['p0','t','l']:np.testing.assert_array_equal(a[k],b[k][:10])
        self.assertEqual(b['knn'].shape,(11,8))

    def test_global_hash_order_and_nested_budgets(self):
        paths=[np.array([[i,0.,0.],[i,1.,0.]]) for i in range(8)]
        order=path_order(paths,3)
        np.testing.assert_array_equal(order,path_order(paths,3))
        self.assertTrue(np.all(~prefix_mask(order,3)|prefix_mask(order,4)))
        self.assertEqual(prefix_mask(order,3).sum(),3)

    def test_nonpolar_continuous_orbit(self):
        ref=Camera(np.array([[300.,0,200],[0,400,200],[0,0,1]]),np.eye(4),400,400)
        ref.center=np.array([0.,0.,5.])
        cfg=dict(frames=120,reference_train_index=0,resolution=400,elevation_deg=25.,elevation_swing_deg=8.)
        cs=orbit(dict(trajectory=cfg),[ref],dict(mu=np.zeros((2,3))),np.ones(2,bool))
        el=np.rad2deg([np.arcsin(c.center[2]/np.linalg.norm(c.center)) for c in cs])
        self.assertAlmostEqual(min(el),17);self.assertAlmostEqual(max(el),33)
        self.assertGreater(np.linalg.norm(cs[0].center-cs[60].center),5)
        self.assertEqual(cs[0].K[1,1],400)


if __name__=='__main__':unittest.main()
