#!/bin/bash
# GEOLINE STEP 2 — train 2DGS on cadpartA, REUSING the chair/lego recipe UNCHANGED
# (scripts/run_2dgs_chair.sh Run A, scripts/run_2dgs_lego.sh): lambda_normal 0.05,
# lambda_dist 0.0, depth_ratio 1.0, --eval --white_background --data_device cpu, 30000 iters.
# NO per-scene tuning of anything. Frozen after training.
set -e
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
cd ~/3dgs_line/ext/2dgs
export CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4
DATA=/home/u00134/cglib/data/full/cadpartA
OUT=/home/u00134/3dgs_line/tier1/out
python -u train.py -s $DATA -m $OUT/2dgs_cadpartA \
  --eval --white_background --depth_ratio 1.0 --data_device cpu \
  --lambda_normal 0.05 --lambda_dist 0.0 \
  --iterations 30000 --test_iterations 7000 15000 30000 \
  --save_iterations 7000 15000 30000 --port 6341
echo "2DGS CADPARTA TRAINING COMPLETE"
