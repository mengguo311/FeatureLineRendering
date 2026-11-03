import runtime_io
import unittest
from test_whole import WholeTests
from test_loader import LoaderTests,ROOT
ROOT.mkdir(parents=True,exist_ok=True)
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in [WholeTests,LoaderTests]));raise SystemExit(0 if r.wasSuccessful() else 1)
