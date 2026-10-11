import unittest
from observer_state import classify

class StateTests(unittest.TestCase):
    def test_running_diagnostic_never_training_complete(self):
        self.assertEqual(classify('RUNNING',True,False),'BOUNDED_MEMCHECK_RUNNING')
    def test_waiting(self):
        self.assertEqual(classify('WAITING_FOR_LOW_LOAD_GPU',True,False),'WAITING_FOR_LOW_LOAD_GPU')
    def test_success_needs_seal_and_still_not_scientific(self):
        self.assertEqual(classify('CUDA_REPLAY_DIAGNOSTIC_COMPLETE',False,True),'REPLAY_PASSED_OFFICIAL_NATIVE_GPU_VALIDATION_PENDING')
        self.assertEqual(classify('CUDA_REPLAY_DIAGNOSTIC_COMPLETE',False,False),'ENGINEERING_NOT_READY_UNVERIFIED_DIAGNOSTIC')
    def test_fail_is_fail(self):
        self.assertEqual(classify('ENGINEERING_NOT_READY',False,False),'ENGINEERING_NOT_READY')
    def test_dead_running_not_success(self):
        self.assertEqual(classify('RUNNING',False,False),'ENGINEERING_NOT_READY_DEAD_RUNNER')

if __name__=='__main__':unittest.main()
