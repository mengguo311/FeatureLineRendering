import unittest
from suite_progress import project
class Progress(unittest.TestCase):
 def test_other_scene_state_cannot_overwrite_master(self):
  self.assertIsNone(project({'runner_config_path':'new'}, {'config':'old'},[],0))
 def test_iteration_and_no_false_completion(self):
  m={'runner_config_path':'new'};s={'config':'new','status':'RUNNING','runner_pid':1,'child_pid':2,'stage':'train'}
  r=project(m,s,['smoke'],321);self.assertEqual(r['completed_iteration_observed'],321);self.assertFalse(r['full_suite_completed']);self.assertEqual(r['childPIDs'],[2])
 def test_chain_requires_all_verified_seals_and_review(self):
  m={'runner_config_path':'new'};s={'config':'new','status':'PILOT_CHAIN_COMPLETE','runner_pid':1,'child_pid':None,'stage':None}
  self.assertEqual(project(m,s,['smoke'],30000)['status'],'ENGINEERING_NOT_READY')
  r=project(m,s,['smoke','train','export','tsdf','eval'],30000);self.assertEqual(r['status'],'SCENE_CHAIN_SEALED_REVIEW_REQUIRED');self.assertFalse(r['scientificdone'])
if __name__=='__main__':unittest.main(verbosity=2)
