"""BUILD-only suite with every legacy fixture output redirected to the current unit."""
from runtime_io import *
import unittest,importlib,argparse

def main():
 p=argparse.ArgumentParser();p.add_argument('--unit',required=True);args=p.parse_args();u=Path(args.unit)/'tests';u.mkdir(parents=True,exist_ok=True)
 assert u.parent.name=='unit_003','BUILD_TEST_DESTINATION'
 names=['test_port_paths','test_adapter','test_scope','test_paired_delivery','test_runner_fixture','test_ambiguity','test_ambiguity_delivery','test_real_ambiguity']
 modules=[]
 for name in names:
  m=importlib.import_module(name)
  if hasattr(m,'U'):m.U=u
  modules.append(m)
 suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 raise SystemExit(0 if result.wasSuccessful() else 1)
if __name__=='__main__':main()
