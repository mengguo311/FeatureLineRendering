import unittest
import numpy as np
from source_membership import contributions, aggregate, assign, sample_pixels

class SourceMembershipTests(unittest.TestCase):
    def test_full_order_and_transmittance_not_nearest_center(self):
        uv=np.array([[5.,5.],[5.,5.],[5.,5.]])
        z=np.array([3.,1.,2.])
        cov=np.tile(np.eye(2)[None],(3,1,1))
        ids,weights=contributions(uv,z,cov,np.array([.9,.5,.4]),5,5)
        np.testing.assert_array_equal(ids,[1,2,0])
        np.testing.assert_allclose(weights,[.5,.2,.27],atol=1e-12)
    def test_full_footprint_and_absent_support(self):
        ids,w=contributions(np.array([[7.,5.],[5.,5.]]),np.array([1.,2.]),np.tile(np.eye(2)[None],(2,1,1)),np.array([1.,.8]),5,5)
        np.testing.assert_array_equal(ids,[0,1])
        np.testing.assert_allclose(w,[np.exp(-2),.8*(1-np.exp(-2))],atol=1e-12)
        ids,w=contributions(np.array([[10.,5.]]),np.array([1.]),np.eye(2)[None],np.array([1.]),5,5)
        self.assertEqual(len(ids),0)
    def test_unknown_mask_cannot_cast_negative_votes(self):
        observations=[(np.array([0,1]),np.array([.5,.4]),np.array([.9,.1,.0]),1.),(np.array([0]),np.array([.7]),None,1.)]
        score,exposure=aggregate(2,observations,3)
        np.testing.assert_allclose(score,[[.45,.05,0],[.36,.04,0]])
        np.testing.assert_allclose(exposure,[.5,.4])
    def test_no_exposure_and_mixed_kernel_abstain(self):
        score=np.array([[.5,.5,0],[.95,.05,0],[0,0,0]])
        exp=np.array([1.,1.,0.])
        ids,reason=assign(score,exp,min_exposure=.05,min_fraction=.8)
        np.testing.assert_array_equal(ids,[0,1,0])
        self.assertEqual(reason[0],'mixed')
        self.assertEqual(reason[2],'unobserved')

    def test_sampler_excludes_unknown_and_balances_label_populations(self):
        labels=np.array([[1,1,1,2],[2,2,3,0],[3,0,0,0]],dtype=np.uint8)
        unknown=np.zeros(labels.shape,dtype=bool);unknown[0,0]=True
        samples=sample_pixels(labels,unknown,6,seed=12)
        self.assertEqual(len(samples),6)
        self.assertEqual({int(labels[y,x]) for x,y,w in samples},{1,2,3})
        self.assertTrue(all(not unknown[y,x] for x,y,w in samples))
        self.assertAlmostEqual(sum(w for x,y,w in samples),6.)

if __name__=='__main__':unittest.main()
