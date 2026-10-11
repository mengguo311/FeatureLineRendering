import unittest
from memcheck_gate import validate

class GateTests(unittest.TestCase):
    def test_success_requires_both_1000_finite_and_tool_zero(self):
        self.assertTrue(validate(0,'========= ERROR SUMMARY: 0 errors',{'status':'NO_NONFINITE_FOUND_THROUGH1000','last_completed':1000}))
    def test_error_or_missing_summary_rejected(self):
        for code,text in [(86,'ERROR SUMMARY: 3 errors'),(0,'ERROR SUMMARY: 3 errors'),(0,'no summary')]:
            with self.assertRaises(ValueError):validate(code,text,{'status':'NO_NONFINITE_FOUND_THROUGH1000','last_completed':1000})
    def test_bounded_failure_or_short_run_rejected(self):
        for r in [{'status':'FIRST_FAILURE_CAPTURED','last_completed':803},{'status':'NO_NONFINITE_FOUND_THROUGH1000','last_completed':500}]:
            with self.assertRaises(ValueError):validate(0,'ERROR SUMMARY: 0 errors',r)

if __name__=='__main__':unittest.main()
