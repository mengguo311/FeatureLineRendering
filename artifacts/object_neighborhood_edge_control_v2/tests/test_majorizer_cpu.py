import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from REFINE_COLORS import validate_majorizer_dense
class MajorizerTests(unittest.TestCase):
    def test_positive_weight_diagonal_majorizes_coupled_operator(self):
        A=np.array([[.2,.3,0.],[.1,.4,.2],[0,.1,.7]])
        self.assertTrue(validate_majorizer_dense(A))
    def test_negative_weights_are_outside_contract(self):
        with self.assertRaises(ValueError):validate_majorizer_dense(np.array([[.2,-.3]]))
if __name__=='__main__':unittest.main()
