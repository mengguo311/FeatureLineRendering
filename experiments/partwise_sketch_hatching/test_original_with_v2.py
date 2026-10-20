"""Run the unchanged nine original contracts against the repaired module."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "2"
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
import sys
import unittest
import core_walk_v2
sys.modules["core"] = core_walk_v2
import test_p0

if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(test_p0))
    sys.exit(not result.wasSuccessful())
