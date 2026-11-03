"""Explicit small suites; all temporary output confined to unit004."""
import os,tempfile
from pathlib import Path
P=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_free_reassignment_v07_20261101/units/unit_004/tests_tmp');P.mkdir(exist_ok=True)
os.environ['TMPDIR']=str(P);tempfile.tempdir=str(P)
import unittest
from test_free import FreeTests
from test_coverage import CoverageTests
from test_merge import MergeTests
from test_overlap import OverlapTests
if __name__=='__main__':
 suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in [FreeTests,CoverageTests,MergeTests,OverlapTests]);r=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if r.wasSuccessful() else 1)
