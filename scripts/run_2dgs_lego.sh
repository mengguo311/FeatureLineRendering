#!/bin/bash
# DIAG-2DGS step 1 — train 2DGS on lego, REUSING the chair pivot's Run A recipe unchanged
# (scripts/run_2dgs_chair.sh): lambda_normal 0.05, lambda_dist 0.0, depth_ratio 1.0,
# --eval --white_background --data_device cpu, 30000 iterations.
#
# Run A is the recipe the chair result the diagnostic is built on came from: it is the model
# src/gate2dgs.py gates with and the one that scored ribbon-normal AUC 0.967 / fabric p95
# 7.29 deg on chair (PLAN1_RESULTS.md STEP A).  lambda_dist=1000 was measured WORSE there
# (normal AUC 0.851, crease p05 collapses to 0.29), so it is deliberately not run.
# Frozen after training; no per-scene tuning.
set -e
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
cd ~/3dgs_line/ext/2dgs
export CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4
DATA=/home/u00134/cglib/data/full/lego
OUT=/home/u00134/3dgs_line/tier1/out
python -u train.py -s $DATA -m $OUT/2dgs_lego \
  --eval --white_background --depth_ratio 1.0 --data_device cpu \
  --lambda_normal 0.05 --lambda_dist 0.0 \
  --iterations 30000 --test_iterations 7000 15000 30000 \
  --save_iterations 7000 15000 30000 --port 6331
echo "2DGS LEGO TRAINING COMPLETE"
