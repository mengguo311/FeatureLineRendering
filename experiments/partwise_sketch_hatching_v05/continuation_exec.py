"""Run one existing script with continuation-local temporary storage only."""
import os
import sys
from pathlib import Path
import runpy

UNIT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_005')
SCRATCH=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/orchestration/continuation_001/scratch')


def configure(script):
    os.environ['CUDA_VISIBLE_DEVICES']=''
    os.environ['V05_UNIT_DIR']=str(UNIT)
    os.environ['PYTHONDONTWRITEBYTECODE']='1'
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(Path(script).resolve().parent))
    import runtime
    assert runtime.ACTIVE_UNIT==UNIT
    assert SCRATCH.is_dir()
    os.environ['TMPDIR']=str(SCRATCH)
    import tempfile
    tempfile.tempdir=str(SCRATCH)
    assert len(os.sched_getaffinity(0))<=2


if __name__=='__main__':
    script=Path(sys.argv[1]).resolve()
    configure(script)
    sys.argv=[str(script)]+sys.argv[2:]
    runpy.run_path(str(script),run_name='__main__')
