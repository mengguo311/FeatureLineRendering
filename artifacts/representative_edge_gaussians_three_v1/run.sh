#!/bin/bash
set -eu
cd /home/u00134/3dgs_line/representative_edge_gaussians_three_v1
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 CUDA_VISIBLE_DEVICES=0
export TMPDIR="$PWD/out/representative_edge_gaussians_three_v1/tmp"
mkdir -p "$TMPDIR"
exec /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/representative_edge_gaussians_three_v1/code/pipeline.py "$@"
