import unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from REFINE_EXACT_L1 import cp_norm_bound
class CPTests(unittest.TestCase):
    def test_nonnegative_row_column_preconditioning_is_contracting(self):
        A=np.array([[.2,.3,0.],[.1,.4,.2],[0,.1,.7]])
        self.assertLess(cp_norm_bound(A),1)
if __name__=='__main__':unittest.main()
