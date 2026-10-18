from env import *
import unittest
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(CODE),pattern='test_*.py'));raise SystemExit(not result.wasSuccessful())
