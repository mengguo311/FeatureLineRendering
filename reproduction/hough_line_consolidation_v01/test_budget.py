from pilotio import *
from core import run_backend
import unittest
class BudgetContract(unittest.TestCase):
    def test_final_refiner_budget_on_actual_scan24(self):
        z=load_np(OUT/'real/scan24/input.npz')
        data={k:z[k] for k in ['xyz','tangent','fragment_id','confidence','tangent_reliable','eligible','protected']}
        for method in ['B2','H0','H1']:
            with self.subTest(method=method):
                result=run_backend(data,method,0)
                self.assertLessEqual(result['stats']['refiner_calls'],CFG['max_hypotheses'])
                self.assertLessEqual(result['stats']['max_displacement_h'],2+1e-9)
                self.assertEqual(result['stats']['confirmed_links'],0)
if __name__=='__main__': unittest.main(verbosity=2)
