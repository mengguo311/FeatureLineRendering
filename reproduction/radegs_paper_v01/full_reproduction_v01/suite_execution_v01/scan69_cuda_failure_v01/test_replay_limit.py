import unittest
from replay_limit import ReplayLimit,ReplayComplete
class Limit(unittest.TestCase):
 def test_exact_prefix_and_hard_stop(self):
  x=ReplayLimit(500,1000)
  for i in range(501,1000):x.completed(i)
  with self.assertRaises(ReplayComplete):x.completed(1000)
  self.assertEqual(x.last,1000)
 def test_duplicate_or_skipped_step_rejected(self):
  for value in [500,502]:
   with self.assertRaises(ValueError):ReplayLimit(500,1000).completed(value)
 def test_resource_resume_remains_bounded(self):
  x=ReplayLimit(500,1000);x.resume(803);x.completed(804);self.assertEqual(x.last,804)
  with self.assertRaises(ReplayComplete):x.resume(1000)
  with self.assertRaises(ValueError):x.resume(1001)
 def test_future_excess_not_allowed(self):
  with self.assertRaises(ValueError):ReplayLimit(500,500)
if __name__=='__main__':unittest.main(verbosity=2)
