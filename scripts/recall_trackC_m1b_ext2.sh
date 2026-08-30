#!/usr/bin/env bash
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1; cd ~/3dgs_line/tier1
SYN=scripts/explore/syn
COMMON="--scene chair --gate --eval_split test --no_viz"
# match the Canny arm's f range so the RECALL CEILING can be compared at equal f, not just
# the P-vs-R frontier over the overlap.
for f in 0.50 0.45; do
  echo "=================== ARM teed05 f=${f} ==================="
  python -u scripts/run_m1b.py $COMMON --score "$SYN/finalscore_overall_chair__teed_native_0.5.npy" --f "$f" --tag "_tc_teed05_f${f}"
done
echo "EXT2 DONE"
