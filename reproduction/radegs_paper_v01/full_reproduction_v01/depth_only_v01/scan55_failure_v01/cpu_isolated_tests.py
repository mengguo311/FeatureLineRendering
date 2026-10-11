"""Re-run harness failures with explicit imports and a PRIVATE simulated lock.
Never touch the production common GPU lock; CUDA disabled in the parent command.
"""
import os,sys,tempfile,unittest
from pathlib import Path
path=Path(sys.argv[1]).resolve();base=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(path.parent),str(base/'stage2'),str(base/'gradient_fix_v01')]
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
with tempfile.TemporaryDirectory(dir='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/depth_only_v01') as tmp:
 if path.stem=='test_supervisor':
  import control
  control.runner.GLOBAL_GPU_LOCK_DIR=Path(tmp)/'simulated_gpu_locks'
 suite=unittest.defaultTestLoader.discover(str(path.parent),pattern=path.name)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 raise SystemExit(0 if result.wasSuccessful() else 1)
