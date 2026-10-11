import unittest
from train_records import validate_records
class Tests(unittest.TestCase):
 def rows(self):return [{'iteration':i,'geometry_active':i>=15000,'optimizer_updated':i<30000,'wn':.05 if i>=15000 else 0,'wd':100 if i>=15000 else 0} for i in range(1,30001)]
 def test_exact_C24_full_count(self):self.assertEqual(validate_records(self.rows()),{'records':30000,'optimizer_updates':29999,'geometry_records':15001})
 def test_duplicate_missing_paper_text_boundary_and_last_update_rejected(self):
  for kind in ('duplicate','missing','boundary','final_update'):
   r=self.rows()
   if kind=='duplicate':r.insert(0,r[0])
   if kind=='missing':r.pop(500)
   if kind=='boundary':r[14999]['geometry_active']=False
   if kind=='final_update':r[-1]['optimizer_updated']=True
   with self.assertRaises(ValueError):validate_records(r)
if __name__=='__main__':unittest.main(verbosity=2)
