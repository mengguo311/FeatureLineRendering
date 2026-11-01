"""Explicit isolated suites only; no discovery of old producer scripts."""
from free_io import *
import unittest
from test_free import FreeTests
from test_coverage import CoverageTests
if __name__=='__main__':
 suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(FreeTests),unittest.defaultTestLoader.loadTestsFromTestCase(CoverageTests)])
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 raise SystemExit(0 if result.wasSuccessful() else 1)
