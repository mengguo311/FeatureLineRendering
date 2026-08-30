#!/usr/bin/env bash
# TRACK M extension:
#  (a) the SHIFTED-MASK control.  m3_masksharplow shows that intersecting a catastrophic
#      permissive Canny with TEED's binary support turns LIFT_P from -0.23 into +0.05.  The
#      alternative explanation is that the intersection merely REMOVED EDGE PIXELS and any
#      thinning would have done it.  Rolling the same support by 15/40 px keeps its area,
#      shape and statistics and destroys only its REGISTRATION to the image -- and in fact
#      cuts MORE pixels (9.9k/8.0k vs 14.2k per view), so a density story predicts the
#      shifted arms do at least as well.  If they collapse, the operative property is where
#      TEED fires, i.e. selectivity.
#  (b) f=0.45/0.50 for the M arms, so R_max is compared over the SAME f range as teed05
#      (whose R_max 0.7560 came from f=0.50).
set -u
cd ~/3dgs_line/tier1
while pgrep -f "run_m1b.py|recall_trackC_detector.py|teedgen_L_detector_chain.sh|teedgen_L_post.sh|teedgen_M_lego.sh" >/dev/null; do sleep 20; done
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
SYN=scripts/explore/syn

python -u scripts/recall_trackC_seeds.py --scene chair --sources teed --thrs 0.5 \
  --arms_json out/trackM_arms_chair2.json --tag _trackM2

COMMON="--scene chair --gate --eval_split test --no_viz"
run () {
  local sc="$1" f="$2"
  local sp="$SYN/finalscore_overall_chair__${sc}.npy"
  local out="out/m1b_chair_tm_${sc}_f${f}.json"
  [ -f "$sp" ] || { echo "MISSING $sp"; return; }
  [ -f "$out" ] && { echo "HAVE $out"; return; }
  echo "=================== ARM ${sc} f=${f} ==================="
  python -u scripts/run_m1b.py $COMMON --score "$sp" --f "$f" --tag "_tm_${sc}_f${f}"
}
for f in 0.40 0.35 0.30; do run m3_shift15_d2 "$f"; run m3_shift40_d2 "$f"; done
for f in 0.50 0.45; do
  run m3_masksharplow_d2 "$f"; run m1_soft_g1.0 "$f"; run m2_cc25 "$f"
  run m2_cc10 "$f"; run m3_maskM1a_d2 "$f"
done
run m1_soft_g1.0 0.22; run m2_cc10 0.30; run m2_cc10 0.22
echo "ALL TRACK-M EXT ARMS DONE"
