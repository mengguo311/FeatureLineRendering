import tempfile,unittest
from pathlib import Path
import torch
from capture import snapshot_args
class TestCapture(unittest.TestCase):
 def test_values_types_and_no_alias(self):
  x=torch.tensor([1.,2.],requires_grad=True);r=snapshot_args((x,3,2.5,True))
  torch.testing.assert_close(r[0],x);self.assertFalse(r[0].requires_grad);self.assertEqual(r[1:],(3,2.5,True));r[0][0]=8;self.assertEqual(float(x[0]),1.)
 def test_unknown_rejected(self):
  with self.assertRaises(TypeError):snapshot_args((object(),))
if __name__=='__main__':unittest.main()
