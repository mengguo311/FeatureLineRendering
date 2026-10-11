import unittest
from progress import counts
class Tests(unittest.TestCase):
 def test_status_label_does_not_count_unrun_training(self):
  self.assertEqual(counts([{'status':'RUNNING','iteration_records':0,'verified_stages':[]}])['train_started'],0)
 def test_actual_records_and_verified_stages_count_once(self):
  a={'iteration_records':30000,'verified_stages':['train','export','tsdf','eval','quality_review']}
  b={'iteration_records':123,'verified_stages':['smoke']}
  self.assertEqual(counts([a,b]),{'train_started':2,'train_completed':1,'export_completed':1,'mesh_completed':1,'official_metrics':1,'quality_review_passed':1})
 def test_empty_status_not_completed(self):
  self.assertEqual(counts([{'status':'TRAIN_COMPLETED','iteration_records':0,'verified_stages':[]}])['train_completed'],0)
if __name__=='__main__':unittest.main(verbosity=2)
