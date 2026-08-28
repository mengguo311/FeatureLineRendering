#!/usr/bin/env bash
# TGAP stage 1 — dump the METHOD-PATH pull for every f on the densified lego frontier.
# One pull per f; all three arms are post-pull threshold changes, so nothing else is needed.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1
for f in 0.15 0.22 0.30 0.35 0.40 0.45 0.50 0.55 0.60 0.65 0.70 0.80 0.85 0.90 0.95 1.00; do
  python -u scripts/tgap_pull.py --scene lego --f "$f" || exit 1
done
echo "TGAP PULL DUMPS DONE"
