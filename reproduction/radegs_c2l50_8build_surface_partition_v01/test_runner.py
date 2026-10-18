from env import *
import unittest
if __name__=='__main__':
 suite=unittest.TestSuite()
 for name in ['test_round1','test_round2','test_round3']:suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
 result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if result.wasSuccessful() else 1)
