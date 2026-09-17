import unittest
import numpy as np
from src.stroke_select import Objective,select,mean_lowest

class SelectorTests(unittest.TestCase):
    def test_complementary_low_unary_pair(self):
        relation={'view':0,'bundles':[{'ids':[2,3],'score':1.}]}
        o=Objective([[.30,.29,.10,.10]],np.ones(4),[relation],[1])
        full,_=select(o,2,'D'); no,_=select(o,2,'B')
        self.assertEqual(np.flatnonzero(full).tolist(),[2,3])
        self.assertEqual(np.flatnonzero(no).tolist(),[0,1])
        self.assertEqual(o.parts(np.array([0,0,1,0],bool))[1][0],0)

    def test_tail_protects_minority_view(self):
        o=Objective([[1,.6],[1,.6],[1,.6],[0,.6]],np.ones(2))
        full,_=select(o,1,'D'); average,_=select(o,1,'C')
        self.assertEqual(np.flatnonzero(full).tolist(),[1])
        self.assertEqual(np.flatnonzero(average).tolist(),[0])
        self.assertEqual(mean_lowest([0,1,1,1]),0.)

    def test_alternates_use_max_and_sparse_delta_is_exact(self):
        relations=[{'view':0,'bundles':[{'ids':[0,1],'score':.5},{'ids':[1,2],'score':.8}]},
                   {'view':1,'bundles':[{'ids':[0,2,3],'score':.6}]}]
        o=Objective(np.ones((2,4))*.1,np.ones(4),relations,[2,3],[(0,1,2,.2)])
        for bits in range(16):
            x=np.array([bool(bits&(1<<i)) for i in range(4)])
            for mode in 'ABCD':
                for i in range(4):
                    y=x.copy();y[i]=not y[i]
                    q=o.changed_q(x,o.q(x,mode),[i] if y[i] else [],[] if y[i] else [i],mode)
                    np.testing.assert_allclose(q,o.q(y,mode),atol=1e-12)
        self.assertAlmostEqual(o.parts(np.ones(4,bool))[1][0],.8/2)

    def test_deterministic_budget_and_invisible_not_free(self):
        o=Objective([[.1,.2,.3,.9]],np.array([1.,2.,3.,0.]))
        for mode in 'ABCD':
            x,a=select(o,3,mode); y,b=select(o,3,mode)
            np.testing.assert_array_equal(x,y); self.assertLessEqual(a['cost'],3)
            self.assertFalse(x[3])

if __name__=='__main__': unittest.main()
