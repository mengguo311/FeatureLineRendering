#!/usr/bin/env bash
# TRACK M — rankability mechanism ablation, full M1b on chair, held-out TEST.
#
# All arms are the IDENTICAL run_m1b.py path with the IDENTICAL published-baseline flags;
# only --score differs, and those scores differ only in how the TEED edge map was turned
# into the photometric DT.  The canny and teed05 frontiers are the ones already published
# (copied under the _tm_ prefix so the table reads against the same interpolant).
#
#   M1  m1_soft_g1.0        continuous confidence   vs  teed05 (a hard step at 0.5)
#   M2  m2_cc10/25/50       CC length filter        vs  teed05 (no filter)
#   M3  m3_maskM1a_d2       TEED support masked onto the PUBLISHED blurred Canny
#       m3_masksharplow_d2  TEED support masked onto the PERMISSIVE un-blurred Canny
#                           -- the arm that separates SELECTIVITY from EDGE PLACEMENT,
#                           because cannysharplow alone scores -0.21..-0.23 at M1b.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1
SYN=scripts/explore/syn
COMMON="--scene chair --gate --eval_split test --no_viz"

run () {
  local sc="$1" f="$2"
  local sp="$SYN/finalscore_overall_chair__${sc}.npy"
  local out="out/m1b_chair_tm_${sc}_f${f}.json"
  if [ ! -f "$sp" ]; then echo "MISSING $sp — skipped"; return; fi
  if [ -f "$out" ]; then echo "HAVE $out — skipped"; return; fi
  echo "=================== ARM ${sc} f=${f} ==================="
  python -u scripts/run_m1b.py $COMMON --score "$sp" --f "$f" --tag "_tm_${sc}_f${f}"
}

for f in 0.40 0.35 0.30 0.22; do
  run m3_masksharplow_d2 "$f"      # the money arm first
  run m3_maskM1a_d2 "$f"
  run m1_soft_g1.0 "$f"
  run m2_cc25 "$f"
  run m2_cc10 "$f"
done
for f in 0.30 0.22; do run m2_cc50 "$f"; done
echo "ALL TRACK-M M1b ARMS DONE"
