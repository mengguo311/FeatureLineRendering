from env import *
import unittest
names=['test_core','test_protocol','test_regression','test_hierarchy'];suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in names);result=unittest.TextTestRunner(verbosity=2).run(suite);print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),inherited_tests_counted=0)));raise SystemExit(0 if result.wasSuccessful() else 1)
