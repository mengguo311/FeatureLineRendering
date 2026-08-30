#!/bin/bash
# RUN C — install-health control. EXACTLY the 2DGS repo's own NeRF-synthetic recipe
# (ext/2dgs/scripts/nerf_eval.py): --lambda_normal 0.0, default lambda_dist 0.0,
# default depth_ratio 0.0.  This run has NO geometry regularisation, so it is NOT a Plan #1
# candidate; its only job is to answer whether the 7.7 dB PSNR gap of Run A is a broken
# install/data path or the price of the normal-consistency + median-depth recipe.
set -e
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
cd ~/3dgs_line/ext/2dgs
export CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4
echo "=================== RUN C: repo nerf_eval recipe (lambda_normal=0) ==================="
python -u train.py -s /home/u00134/cglib/data/full/chair \
  -m /home/u00134/3dgs_line/tier1/out/2dgs_chair_reporecipe \
  --eval --white_background --data_device cpu \
  --lambda_normal 0.0 --lambda_dist 0.0 \
  --iterations 30000 --test_iterations 7000 15000 30000 \
  --save_iterations 30000 --port 6323
echo "=================== RUN C COMPLETE ==================="
