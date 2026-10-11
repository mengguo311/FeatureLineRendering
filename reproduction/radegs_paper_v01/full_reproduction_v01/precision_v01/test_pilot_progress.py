import unittest
from pilot_progress import project


class ProgressTests(unittest.TestCase):
    def test_chain_completion_requires_scientific_review(self):
        x=project({'runner_state_path':'x'},dict(status='PILOT_CHAIN_COMPLETE',runner_pid=8),
                  'x',['smoke','train','export','tsdf','eval'],30000)
        self.assertEqual(x['status'],'PILOT_CHAIN_SEALED_REVIEW_REQUIRED')
        self.assertFalse(x['full_suite_completed']);self.assertFalse(x['scientificdone'])

    def test_actual_train_progress_replaces_old_verified_stages(self):
        x=project({'runner_state_path':'x','verified_stages':['old_train']},
                  dict(status='RUNNING',stage='train',runner_pid=8,child_pid=9),'x',['smoke'],502)
        self.assertEqual(x['completed_iteration_observed'],502)
        self.assertEqual(x['verified_stages'],['smoke']);self.assertEqual(x['childPIDs'],[9])

    def test_failed_stage_never_claims_completion(self):
        x=project({'runner_state_path':'x'},dict(status='ENGINEERING_NOT_READY',stage='tsdf',reason='empty'),
                  'x',['smoke','train','export'],30000)
        self.assertFalse(x['scientificdone']);self.assertEqual(x['status'],'ENGINEERING_NOT_READY')

    def test_wrong_path_does_not_overwrite_active_job(self):
        self.assertIsNone(project({'runner_state_path':'new'},dict(status='RUNNING'),'old',[],0))


if __name__=='__main__':unittest.main(verbosity=2)
