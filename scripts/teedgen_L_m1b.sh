#!/usr/bin/env bash
# TRACK L — full M1b (pull + chain + prune) on lego, held-out TEST, one arm per edge source.
#
# Identical run_m1b.py flags to the published lego baseline (out/m1b_lego_gated_test.json:
# --gate, edge=sharp, pull_split=train, eval_split=test, steps=100, lr=0.35, delta_max=5,
# len_thr=0.9).  ONLY --score differs, and those scores differ only in which 2D detector
# fed the M1a photometric DT.
#
# The canny arm is a REPRODUCTION control: at f=0.30 it must return n_seeds 29916 and
# seg P@1.5 0.5826 / R@1.5 0.4168 at stage pull+prune[spec].
#
# cannysharp / cannysharplow are NOT decoration here.  On chair they were the arms that
# proved raw 2D recall is useless downstream (LIFT_P -0.16..-0.23).  On lego they LEAD the
# seed-level frontier (+0.10..+0.17), so whether they survive M1b is the whole
# conditional-law question.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1
SYN=scripts/explore/syn
COMMON="--scene lego --gate --eval_split test --no_viz"

run () {   # run <score_name> <f>
  local sc="$1" f="$2"
  local sp="$SYN/finalscore_overall_lego__${sc}.npy"
  local out="out/m1b_lego_tc_${sc}_f${f}.json"
  if [ ! -f "$sp" ]; then echo "MISSING $sp — skipped"; return; fi
  if [ -f "$out" ]; then echo "HAVE $out — skipped"; return; fi
  echo "=================== ARM ${sc} f=${f} ==================="
  python -u scripts/run_m1b.py $COMMON --score "$sp" --f "$f" --tag "_tc_${sc}_f${f}"
}

# the frontier arm first (it defines the interpolant every LIFT_P is read against)
for f in 0.50 0.45 0.40 0.35 0.30 0.22 0.15; do run canny "$f"; done
for f in 0.50 0.45 0.40 0.35 0.30 0.22 0.15; do run teed_native_0.5 "$f"; done
for f in 0.40 0.30 0.22; do
  run cannysharplow "$f"
  run cannysharp "$f"
  run teed_native_0.9 "$f"
  run union_native_0.5 "$f"
done
echo "ALL TRACK-L M1b ARMS DONE"
