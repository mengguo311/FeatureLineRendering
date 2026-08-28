#!/usr/bin/env bash
# TGAP stage 2 — score arms A/B/C on VAL (selection) and TEST (reporting).
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1
for split in val test; do
  echo "########## split=$split ##########"
  python -u scripts/tgap_eval.py --scene lego --split "$split" || exit 1
done
echo "TGAP EVAL DONE"
