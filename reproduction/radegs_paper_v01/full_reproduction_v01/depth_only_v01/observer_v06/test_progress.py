import unittest
from progress import counts,disk_blocked
class Tests(unittest.TestCase):
 def test_wrapper_status_never_inflates_verified_counts(self):
  rows=[{'status':'DONE','train_completed':False,'depth_export_completed':False,'depth_review_passed':False}, {'train_completed':True,'depth_export_completed':True,'depth_review_passed':False},{'train_completed':True,'depth_export_completed':True,'depth_review_passed':True}]
  self.assertEqual(counts(rows),{'train_completed':2,'depth_export_completed':2,'depth_review_passed':1})
 def test_inconsistent_review_rejected(self):
  with self.assertRaises(ValueError):counts([{'depth_review_passed':True}])
 def test_only_real_disk_stop_blocks(self):
  self.assertFalse(disk_blocked(None));self.assertFalse(disk_blocked({'status':'MONITORING'}));self.assertTrue(disk_blocked({'status':'LOW_DISK_STOP_REQUESTED'}))
 def test_no_mesh_counts(self):
  self.assertEqual(counts([{'verified_stages':['tsdf','eval']}]),{'train_completed':0,'depth_export_completed':0,'depth_review_passed':0})
if __name__=='__main__':unittest.main(verbosity=2)
