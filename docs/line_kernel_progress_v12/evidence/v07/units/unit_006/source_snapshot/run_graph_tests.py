"""Explicit unit005 suites; no legacy runners or old output paths."""
from pathlib import Path
import os,tempfile,unittest
P=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_free_reassignment_v07_20261101/units/unit_005/tests_tmp');P.mkdir(exist_ok=True);tempfile.tempdir=str(P);os.environ['TMPDIR']=str(P)
from test_graph_birth import GraphBirthTests
from test_free import FreeTests
from test_coverage import CoverageTests
from test_merge import MergeTests
from test_overlap import OverlapTests
if __name__=='__main__':
 suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in [FreeTests,CoverageTests,MergeTests,OverlapTests,GraphBirthTests]);r=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if r.wasSuccessful() else 1)
