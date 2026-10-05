#!/usr/bin/env bash
set -euo pipefail
cd /home/u00134/3dgs_line/representative_edge_gaussians_v1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=0
export TMPDIR="$PWD/out/representative_edge_gaussians_v1/tmp"
mkdir -p "$TMPDIR"
PYTHON_RUNNER=/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
# One authorized invocation is bounded to 90 minutes; per-pose seals survive timeout.
timeout --signal=TERM 5400 "$PYTHON_RUNNER" -B artifacts/representative_edge_gaussians_v1/code/pipeline.py "$@"
