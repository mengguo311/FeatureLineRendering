import unittest,numpy as np
from test_geometry import segment
from primitive import associate,sample_graph,compatible
from primitive_reference_before_vectorization import associate as reference
from unittest.mock import patch

class Acceleration(unittest.TestCase):
    def test_bounded_candidate_filter_identical(self):
        rng=np.random.RandomState(81);ss=[]
        for i in range(180):
            s=segment(y=float(rng.randint(0,20))*.018,view=i%3,curve=i%13==0)
            shift=np.array([float(rng.randint(0,10))*.023,0,float(rng.randint(0,4))*.027]);s['control']+=shift;s['points']+=shift;ss.append(s)
        a,aa=associate(ss)
        # This test isolates vectorized candidate enumeration, not an obsolete
        # scientific predicate. Both enumerators must use the current fixed
        # interval predicate; the pre-fix failure is separately retained.
        with patch('primitive_reference_before_vectorization.compatible',compatible):b,bb=reference(ss)
        self.assertEqual(aa,bb);self.assertEqual([g['members'] for g in a],[g['members'] for g in b])
        for k in ('means','covariance','opacity','primitive_id'):
            np.testing.assert_array_equal(sample_graph(a)[k],sample_graph(b)[k])

if __name__=='__main__':unittest.main(verbosity=2)
