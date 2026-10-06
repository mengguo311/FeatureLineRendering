import unittest
from pathlib import Path

class RuntimeTests(unittest.TestCase):
 def test_confined_and_no_old_writes(self):
  import runtime
  self.assertEqual(runtime.ROOT,Path('/home/u00134/3dgs_line/gaer_object_contours_v01'))
  self.assertEqual(runtime.EXP.name,'gaer_object_contours_v01')
  with self.assertRaises(ValueError):runtime.scoped(runtime.ROOT/'artifacts/gaer_attribution_capacity_v02/forbidden.txt')
  with self.assertRaises(PermissionError):
   with open(runtime.ROOT/'out/gaer_attribution_capacity_v02/forbidden.txt','w'):pass
  runtime.guard('runtime-test',False)

if __name__=='__main__':unittest.main()
