#!/usr/bin/env bash
set -uo pipefail
cd /home/u00134/3dgs_line/gaer_multiview_contour_regions_v01
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMBA_NUM_THREADS=2
exec /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -u experiments/gaer_multiview_contour_regions_v01/run.py "$@"
