from runtime_io import *
import argparse,unittest,importlib
p=argparse.ArgumentParser();p.add_argument('--legacy',action='store_true');a=p.parse_args()
m=importlib.import_module('test_port_scene')
if not a.legacy:m.RUNNER=importlib.import_module('port_scene_runner')
suite=unittest.TestSuite([m.PortSceneTests('test_ficus_paths_and_later_failure_preserve_complete_mappings')]) if a.legacy else unittest.defaultTestLoader.loadTestsFromModule(m)
if not a.legacy:
 
 for name in ['test_port_paths','test_port_scene_scope','test_port_scene_real']:suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name)))
 x=importlib.import_module('test_scene_transfer');x.U=m.U;x.ADAPTER=importlib.import_module('scene_adapter');suite.addTest(x.SceneContract('test_adapter_uses_configured_count'))
r=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if r.wasSuccessful() else 1)
