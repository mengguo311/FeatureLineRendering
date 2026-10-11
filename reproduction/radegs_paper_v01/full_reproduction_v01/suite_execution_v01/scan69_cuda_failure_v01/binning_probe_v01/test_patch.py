import unittest
from patch import instrument
class Tests(unittest.TestCase):
 def test_no_silent_skip(self):
  s="\t// Generate no key/value pair for invisible Gaussians\n"
  result=instrument(s)
  self.assertIn('asm(\"trap;\");',result)
  self.assertIn('allocated != actual',result)
  self.assertIn('radii[idx] > 0',result)
  self.assertIn('BINNING_MISMATCH',result)
 def test_reject_wrong_anchor(self):
  with self.assertRaises(ValueError):instrument('')
if __name__=='__main__':unittest.main()
