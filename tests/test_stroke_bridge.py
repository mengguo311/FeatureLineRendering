import unittest
import numpy as np
from src.stroke_bridge import hermite, propose, choose, DEFAULTS


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.g=np.stack([np.arange(-1.,1.001,.01),np.zeros(201),np.zeros(201)],axis=1)
        self.paths=[np.array([[-.3,0,0],[-.2,0,0],[-.05,0,0]]),
                    np.array([[.05,0,0],[.2,0,0],[.3,0,0]])]

    def test_good_continuation_and_determinism(self):
        a,log,scale=propose(self.paths,self.g)
        b,_,_=propose(self.paths,self.g)
        self.assertEqual(len(a),1)
        np.testing.assert_allclose(a[0]['points'],b[0]['points'])
        self.assertEqual(a[0]['endpoints'],[[0,1],[1,0]])
        self.assertGreater(a[0]['gaussian_supported_fraction'],.99)

    def test_hermite_endpoints(self):
        p=hermite(np.array([0.,0,0]),np.array([1.,0,0]),[1,0,0],[-1,0,0])
        np.testing.assert_allclose(p[[0,-1]],[[0,0,0],[1,0,0]])
        self.assertTrue(np.all(np.diff(p[:,0])>0))

    def test_G3_nearby_parallel_structures_rejected(self):
        paths=[self.paths[0],self.paths[0]+[0,.04,0]]
        a,log,_=propose(paths,self.g)
        self.assertFalse(a)
        self.assertTrue(any(r['reason']=='G3_incompatible_tangents' for r in log))

    def test_air_gap_rejected(self):
        g=self.g[abs(self.g[:,0])>.04]
        a,log,_=propose(self.paths,g)
        self.assertFalse(a)
        self.assertTrue(any(r['reason']=='unsupported_3d_space' for r in log))

    def test_budget_and_endpoint_capacity(self):
        b=[dict(bridge_id=i,endpoint_ids=[i,i+1],length_3d=.1) for i in range(3)]
        selected,a=choose(b,[3,2,1],np.array([[3,1,3],[1,1,1]]),[100,100],100)
        self.assertEqual(selected,[0])  # 1 shares endpoint, 2 exceeds view-0 budget


if __name__=='__main__': unittest.main()
