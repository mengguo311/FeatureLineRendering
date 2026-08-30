#!/usr/bin/env bash
# Extend the Canny f-frontier upward so the TEED arms whose recall EXCEEDS it can be scored
# against a real interpolant rather than being reported as an un-comparable NaN.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
cd ~/3dgs_line/tier1
SYN=scripts/explore/syn
COMMON="--scene chair --gate --eval_split test --no_viz"
for f in 0.50 0.45 0.40; do
  echo "=================== ARM canny f=${f} ==================="
  python -u scripts/run_m1b.py $COMMON --score "$SYN/finalscore_overall_chair__canny.npy" --f "$f" --tag "_tc_canny_f${f}"
done
echo "=================== ARM teed05 f=0.40 ==================="
python -u scripts/run_m1b.py $COMMON --score "$SYN/finalscore_overall_chair__teed_native_0.5.npy" --f 0.40 --tag "_tc_teed05_f0.40"
echo "EXT DONE"
