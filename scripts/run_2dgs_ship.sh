#!/bin/bash
# CONDLAW-3-PRE Stage 2 step 1 — train 2DGS on ship, REUSING the chair pivot's Run A recipe
# UNCHANGED, exactly as scripts/run_2dgs_lego.sh did: lambda_normal 0.05, lambda_dist 0.0,
# depth_ratio 1.0, --eval --white_background --data_device cpu, 30000 iterations.
#
# NO PER-SCENE TUNING. This is the recipe both calibration anchors were measured on
# (chair 0.986 and lego' 0.4334), so ship must use it verbatim or the Stage-2 measurement is
# not comparable to the frozen band [0.692, 0.852]. Any tuning here would be a forking path
# on the very quantity being predicted.
set -e
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
cd ~/3dgs_line/ext/2dgs
export CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4
DATA=/home/u00134/cglib/data/full/ship
OUT=/home/u00134/3dgs_line/tier1/out
python -u train.py -s $DATA -m $OUT/2dgs_ship \
  --eval --white_background --depth_ratio 1.0 --data_device cpu \
  --lambda_normal 0.05 --lambda_dist 0.0 \
  --iterations 30000 --test_iterations 7000 15000 30000 \
  --save_iterations 7000 15000 30000 --port 6341
echo "2DGS SHIP TRAINING COMPLETE"
