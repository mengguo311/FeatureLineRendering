"""Known CPU limits only; never inspect or report environment contents."""
import os

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '2'
if hasattr(os, 'sched_getaffinity'):
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
