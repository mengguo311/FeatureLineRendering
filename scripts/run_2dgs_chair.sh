#!/bin/bash
# STEP A.2 — train 2DGS on chair NeRF-synthetic (100 train views, 800x800).
# Run A = repo-default regularizers (lambda_normal 0.05, lambda_dist 0.0), bounded-object median depth.
# Run B = repo bounded-object geometry recipe (adds lambda_dist 1000, as scripts/dtu_eval.py).
set -e
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
cd ~/3dgs_line/ext/2dgs
export CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4
DATA=/home/u00134/cglib/data/full/chair
OUT=/home/u00134/3dgs_line/tier1/out

echo "=================== RUN A: repo defaults (lambda_dist=0) ==================="
python train.py -s $DATA -m $OUT/2dgs_chair \
  --eval --white_background --depth_ratio 1.0 --data_device cpu \
  --lambda_normal 0.05 --lambda_dist 0.0 \
  --iterations 30000 --test_iterations 7000 15000 30000 \
  --save_iterations 7000 15000 30000 --port 6321

echo "=================== RUN B: + depth distortion (lambda_dist=1000) ==================="
python train.py -s $DATA -m $OUT/2dgs_chair_dist \
  --eval --white_background --depth_ratio 1.0 --data_device cpu \
  --lambda_normal 0.05 --lambda_dist 1000 \
  --iterations 30000 --test_iterations 7000 15000 30000 \
  --save_iterations 7000 15000 30000 --port 6322

echo "=================== BOTH RUNS COMPLETE ==================="
