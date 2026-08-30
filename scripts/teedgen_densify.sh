#!/usr/bin/env bash
# Densify the chair canny frontier between f=0.50 and f=1.00.
#
# Several TRACK M arms reach recalls above canny's f=0.50 point (0.7224).  With the frontier
# sampled only at 0.50 / 0.70 / 1.00 up there, the Pareto-envelope estimator becomes a coarse
# STEP function and reports jumps (m2_cc10 at f=0.40: +0.070 -> +0.166) that are artefacts of
# the sampling, not of the arm.  Five extra canny points remove the artefact.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1
SYN=scripts/explore/syn
for f in 0.55 0.60 0.65 0.80 0.90; do
  out="out/m1b_chair_tc_canny_f${f}.json"
  [ -f "$out" ] && { echo "HAVE $out"; continue; }
  echo "=================== chair canny f=${f} ==================="
  python -u scripts/run_m1b.py --scene chair --gate --eval_split test --no_viz \
    --score "$SYN/finalscore_overall_chair__canny.npy" --f "$f" --tag "_tc_canny_f${f}"
  cp -f "$out" "out/m1b_chair_tm_canny_f${f}.json"
done
# lego is already sampled at 11 points and its envelope is flat, but match the density anyway
for f in 0.55 0.65 0.80 0.90 0.95; do
  out="out/m1b_lego_tc_canny_f${f}.json"
  [ -f "$out" ] && { echo "HAVE $out"; continue; }
  echo "=================== lego canny f=${f} ==================="
  python -u scripts/run_m1b.py --scene lego --gate --eval_split test --no_viz \
    --score "$SYN/finalscore_overall_lego__canny.npy" --f "$f" --tag "_tc_canny_f${f}"
done
echo "DENSIFY DONE"
