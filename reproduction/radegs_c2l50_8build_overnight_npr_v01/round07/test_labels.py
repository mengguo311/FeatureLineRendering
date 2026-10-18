from env import *
import unittest
from display_labels import legend
class LabelTests(unittest.TestCase):
 def test_dtu_geometric_proxy_not_semantics(self):
  x=legend('scan24');self.assertIn('peripheral-horizontal',x);self.assertIn('central-nonhorizontal',x);self.assertNotIn('foreground',x);self.assertNotIn('background-prior',x)
 def test_ficus_proxy_unknown(self):
  x=legend('ficus');self.assertIn('pot-prior',x);self.assertIn('UNKNOWN',x)
if __name__=='__main__':unittest.main(verbosity=2)
