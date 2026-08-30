#!/usr/bin/env bash
# TRACK L extension — the control the lego frontier SHAPE forces.
#
# On chair the canny f-frontier is a normal trade-off (P falls as R rises), so a TEED arm
# sitting above it is unambiguous.  On lego it is NOT: canny's P *rises* with f together
# with R (0.5985@R0.183 -> 0.6257@R0.383), i.e. the M1a canny score orders lego gaussians so
# weakly that keeping MORE of them helps both axes.  A frontier whose best point is its own
# endpoint cannot be interpolated against at any recall above that endpoint, and quoting
# "beyond canny's reach" without first pushing f up would be scoring TEED against a dial
# that was simply never turned far enough.  So: extend every arm upward, to f=1.00 where
# the keep-fraction selects EVERYTHING and the two arms are provably the same seed set.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1
SYN=scripts/explore/syn
COMMON="--scene lego --gate --eval_split test --no_viz"
run () {
  local sc="$1" f="$2"
  local sp="$SYN/finalscore_overall_lego__${sc}.npy"
  local out="out/m1b_lego_tc_${sc}_f${f}.json"
  [ -f "$sp" ] || { echo "MISSING $sp"; return; }
  [ -f "$out" ] && { echo "HAVE $out"; return; }
  echo "=================== ARM ${sc} f=${f} ==================="
  python -u scripts/run_m1b.py $COMMON --score "$sp" --f "$f" --tag "_tc_${sc}_f${f}"
}
while pgrep -f "teedgen_L_m1b.sh" >/dev/null; do sleep 20; done
for f in 0.60 0.70 0.85 1.00; do run canny "$f"; done
for f in 0.60 0.70; do run teed_native_0.5 "$f"; done
for sc in cannysharplow cannysharp teed_native_0.9 union_native_0.5; do run "$sc" 0.50; done
for f in 0.60 0.70; do run cannysharplow "$f"; done
echo "ALL TRACK-L EXT ARMS DONE"
