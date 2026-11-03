"""Explicit bounded suite; current-unit outputs only, no test discovery."""
import runtime_io
from pathlib import Path
import unittest
import test_paired_history,test_paired_loader,test_paired_runner,test_derivative_history,test_contact,test_overlap,test_switch,test_loader_fixture,test_seam
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102/units/unit_010/tests')
for mod in (test_paired_runner,test_overlap,test_switch,test_loader_fixture):mod.ROOT=ROOT
ROOT.mkdir(parents=True,exist_ok=True)
if __name__=='__main__':
 classes=[test_paired_history.PairedTests,test_paired_loader.SchemaTests,test_paired_runner.RunnerFixture,test_derivative_history.DerivativeTests,test_contact.ContactTests,test_loader_fixture.Fixture,test_overlap.OverlapTests,test_overlap.PipelineTests,test_switch.SwitchTests,test_seam.SeamTests,test_seam.IntegrationTests]
 result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in classes))
 raise SystemExit(0 if result.wasSuccessful() else 1)
