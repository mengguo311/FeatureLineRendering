from env import *
import unittest
from test_policy import ConflictTests
from test_random import RandomTests
from test_binding import BindingTests
from test_integration import IntegrationTests

def run():
 suite=unittest.TestSuite()
 for cls,names in [(ConflictTests,None),(RandomTests,['test_random_budget_each_class','test_random_determinism','test_original_unmodified','test_zero_withdrawal_unchanged']),(BindingTests,None),(IntegrationTests,None)]:
  suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls) if names is None else [cls(n) for n in names])
 r=unittest.TextTestRunner(verbosity=2).run(suite);return r
if __name__=='__main__':raise SystemExit(not run().wasSuccessful())
