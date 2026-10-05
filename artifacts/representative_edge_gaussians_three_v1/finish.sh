#!/bin/bash
set -eu
cd /home/u00134/3dgs_line/representative_edge_gaussians_three_v1
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 CUDA_VISIBLE_DEVICES=0
TASK_PYTHON=/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
TASK_CODE=artifacts/representative_edge_gaussians_three_v1/code
"$TASK_PYTHON" -B "$TASK_CODE/audit_video_ffmpeg.py"
"$TASK_PYTHON" -B "$TASK_CODE/seal_report.py"
"$TASK_PYTHON" -B "$TASK_CODE/ledger.py"
"$TASK_PYTHON" -B "$TASK_CODE/verify_delivery.py"
