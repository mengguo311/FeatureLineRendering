import unittest
from pilot_progress import progress
class Tests(unittest.TestCase):
 def test_iteration_is_not_completed_train_or_metric(self):
  r=progress({'status':'RUNNING','stage':'train'},15,set());self.assertEqual(r['actual_counts']['train_started'],1);self.assertEqual(r['actual_counts']['train_completed'],0);self.assertFalse(r['scientificdone'])
 def test_only_verified_seals_count(self):
  r=progress({'status':'OFFICIAL_PILOT_EVALUATED_REVIEW_REQUIRED'},30000,{'train','export','tsdf','eval'});self.assertEqual(r['actual_counts']['official_metrics'],1);self.assertFalse(r['full_suite_completed']);self.assertEqual(r['next_action'],'Review actual scan24 geometry, metric and visuals before any scene expansion')
 def test_failure_does_not_disappear(self):
  r=progress({'status':'ENGINEERING_NOT_READY','stage':'tsdf'},30000,{'train','export'});self.assertEqual(r['status'],'ENGINEERING_NOT_READY');self.assertEqual(r['actual_counts']['mesh_completed'],0);self.assertIn('failure',r['next_action'])
if __name__=='__main__':unittest.main(verbosity=2)
