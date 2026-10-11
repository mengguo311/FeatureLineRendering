import unittest
from track_diagnostic import project

class TrackerTests(unittest.TestCase):
    def test_running_records_real_child_and_never_scientific_completion(self):
        d=project({'runner_state_path':'x'},{'status':'RUNNING','child_pid':123,'runner_pid':12,'selected_gpu_uuid':'GPU0'},'x')
        self.assertEqual(d['childPIDs'],[123]);self.assertFalse(d['scientificdone'])
    def test_diagnostic_completion_requires_followup_not_suite_success(self):
        d=project({'runner_state_path':'x'},{'status':'DIAGNOSTIC_COMPLETE','child_pid':None,'runner_pid':12},'x')
        self.assertEqual(d['status'],'DIAGNOSTIC_EVIDENCE_READY_REVIEW_REQUIRED')
        self.assertFalse(d['full_suite_completed']);self.assertEqual(d['childPIDs'],[])
    def test_does_not_overwrite_another_continuation(self):
        self.assertIsNone(project({'runner_state_path':'new'},{'status':'RUNNING'},'old'))

if __name__=='__main__':unittest.main(verbosity=2)
