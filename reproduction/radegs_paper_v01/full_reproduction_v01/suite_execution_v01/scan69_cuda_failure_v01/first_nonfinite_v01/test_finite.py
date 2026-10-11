import unittest,torch
from finite import bad_tensors
class TestFinite(unittest.TestCase):
 def test_finite_and_empty(self):
  self.assertEqual(bad_tensors({'a':torch.tensor([1.]),'empty':torch.empty(0),'none':None}),{})
 def test_negative_controls(self):
  r=bad_tensors({'a':torch.tensor([[0.,float('nan')],[float('inf'),2.]])});self.assertEqual(r['a']['nonfinite'],2);self.assertEqual(r['a']['point_ids'],[0,1])
if __name__=='__main__':unittest.main()
