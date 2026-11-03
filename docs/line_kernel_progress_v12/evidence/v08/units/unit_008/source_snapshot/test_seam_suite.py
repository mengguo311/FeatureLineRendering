"""Explicit bounded tests; every mutable fixture root is redirected to unit007."""
import runtime_io
from pathlib import Path
import unittest
import test_overlap,test_switch,test_loader_fixture,test_seam,test_seam_runner
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102/units/unit_007/tests')
for mod in (test_overlap,test_switch,test_loader_fixture,test_seam_runner):mod.ROOT=ROOT
ROOT.mkdir(parents=True,exist_ok=True)
if __name__=='__main__':
 suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in [test_seam.SeamTests,test_seam.IntegrationTests,test_overlap.OverlapTests,test_overlap.PipelineTests,test_switch.SwitchTests,test_seam_runner.RunnerFixture])
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 raise SystemExit(0 if result.wasSuccessful() else 1)
