#!/usr/bin/env bash
# TGAP robustness — re-sweep arm B on the held-out TEST band under the three alternative
# definitions of E.  Arm A is unchanged (it does not use E), so the reference frontier is the
# 16-point one already measured; only arm B is re-scored.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1
for K in E_max_0p5 E_mean_0p8 E_frac_0p5; do
  for S in test val; do
    echo "##### $K / $S #####"
    python -u scripts/tgap_eval.py --scene lego --split "$S" --arms B --e_key "$K" \
      --f_only 0.22 0.30 0.35 0.40 0.45 0.50 --tag "_$K" || exit 1
  done
done
echo "TGAP ROBUST DONE"
