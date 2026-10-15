"""Run only this delivery's 17 tests with the same two-CPU policy."""
from common import *
import unittest
if __name__ == '__main__':
    suite = unittest.defaultTestLoader.discover(str(CODE), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
