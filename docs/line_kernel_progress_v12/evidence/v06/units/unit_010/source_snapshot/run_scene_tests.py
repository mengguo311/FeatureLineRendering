"""Only bounded fixtures; never invokes a full-asset producer or renderer."""
from runtime_io import *
import argparse,unittest,importlib
p=argparse.ArgumentParser();p.add_argument('--unit',required=True);p.add_argument('--legacy',action='store_true');a=p.parse_args();u=Path(a.unit);assert u.name=='unit_008'
m=importlib.import_module('test_scene_transfer');m.U=u/'tests';m.U.mkdir(exist_ok=True)
if not a.legacy:
 m.RUNNER=importlib.import_module('scene_runner');m.ADAPTER=importlib.import_module('scene_adapter');m.STAGES=importlib.import_module('scene_stages')
names=['test_fresh_scene_bootstrap_and_paths','test_adapter_uses_configured_count'] if a.legacy else unittest.defaultTestLoader.getTestCaseNames(m.SceneContract)
suite=unittest.TestSuite(m.SceneContract(n) for n in names)
if not a.legacy:
 for name in ['test_observation_model','test_pair_model','test_overlap_model','test_scene_real']:
  suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name)))
r=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if r.wasSuccessful() else 1)
