"""Bounded build regressions only. No real full-asset adapter or renderer."""
from runtime_io import *
import unittest,importlib,argparse
p=argparse.ArgumentParser();p.add_argument('--unit',required=True);a=p.parse_args();u=Path(a.unit);assert u.name=='unit_007';root=u/'tests';root.mkdir(exist_ok=True)
legacy=root.parent.parent/'unit_003/tests/REAL_COMPONENT.npz';target=root/'REAL_COMPONENT.npz'
if not target.exists():target.write_bytes(legacy.read_bytes())
mods=[]
for name in ['test_coverage_policy','test_coverage_runner','test_observation_model','test_pair_model','test_overlap_model','test_real_ambiguity']:
 m=importlib.import_module(name)
 if hasattr(m,'U'):m.U=root
 if name=='test_real_ambiguity':m.PREV=u.parent/'unit_002'
 mods.append(m)
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in mods)
r=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if r.wasSuccessful() else 1)
