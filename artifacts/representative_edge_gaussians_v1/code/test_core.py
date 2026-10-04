import unittest
import numpy as np
from scipy import sparse
import representative_core as r

class Vertical(unittest.TestCase):
    def test_raw_denominator_not_topk(self):
        a=sparse.csc_matrix([[.2/.5,.1/.5]])
        u=r.prefix_curve(a,np.array([1.]),[0,1])
        np.testing.assert_allclose(u,[.4,.6])
    def test_saturation_redundancy_and_original_ids(self):
        a=sparse.csc_matrix([[1,1,0],[0,0,.9]])
        ids,gains,us=r.greedy(a,np.array([.5,.5]),np.zeros(3),np.ones(3,bool),3,0)
        self.assertEqual(ids.tolist(),[0,2]);np.testing.assert_allclose(us,[.5,.95])
    def test_leakage_early_stop_no_padding(self):
        a=sparse.csc_matrix([[.5,.1]])
        ids,g,u=r.greedy(a,np.array([1.]),np.array([0,2.]),np.ones(2,bool),2,.3)
        self.assertEqual(ids.tolist(),[0])
    def test_unknown_excluded(self):
        a=sparse.csc_matrix([[1,2]])
        ids,_,_=r.greedy(a,np.array([1.]),np.zeros(2),np.array([True,False]),2,0)
        self.assertEqual(ids.tolist(),[0])
    def test_persistence_retains_short_detail(self):
        x=np.zeros((3,12,12,3),np.float32);x[0,5,2:5,0]=1;x[1,6,2:5,0]=1;x[0,9,8:11,0]=1
        m,d=r.split_scales(x,.1,2)
        self.assertTrue(np.all(m[5,2:5,0]>0));self.assertTrue(np.all(d[9,8:11,0]>0))
    def test_chunks_preserve_short_component_and_equal_weight(self):
        e=np.zeros((12,80),np.float32);e[3,2:5]=1;e[8,20:78]=1
        chunks,w,meta=r.chunks(e,32,3)
        self.assertTrue(np.all(chunks[3,2:5]>0));
        sums=[w[chunks==i].sum() for i in range(1,int(chunks.max())+1)]
        np.testing.assert_allclose(sums,np.repeat(1/len(sums),len(sums)),atol=1e-6)
        self.assertAlmostEqual(w.sum(),1)
    def test_pixel_units_nms(self):
        x=np.zeros((32,32),np.float32);x[:,16:]=1
        raw=dict(alpha=np.ones_like(x),median_depth=np.ones_like(x),rgb=np.repeat(x[:,:,None],3,2))
        fields=r.multiscale(raw)
        self.assertEqual(fields.shape,(3,32,32,3));self.assertTrue(np.isfinite(fields).all())
    def test_greedy_matches_exhaustive_incremental(self):
        rng=np.random.default_rng(1729);a=rng.uniform(0,.4,(15,12));o=np.repeat(1/15,15);cost=rng.uniform(0,.03,12)
        ids,gs,us=r.greedy(sparse.csc_matrix(a),o,cost,np.ones(12,bool),8,.3)
        residual=np.ones(15);chosen=[]
        for _ in range(8):
            g=(np.minimum(a,residual[:,None])*o[:,None]).sum(0)-.3*cost;g[chosen]=-np.inf
            j=int(np.argmax(g))
            if g[j]<=1e-15:break
            chosen.append(j);residual=np.maximum(residual-a[:,j],0)
        self.assertEqual(ids.tolist(),chosen)
if __name__=='__main__':unittest.main(verbosity=2)
