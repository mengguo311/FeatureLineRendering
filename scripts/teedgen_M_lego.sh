#!/usr/bin/env bash
# TRACK M on LEGO — does the mechanism decomposition transfer, or is "selectivity" itself
# scene-conditional?  On chair the TEED support MASK applied to a permissive un-blurred
# Canny recovers the whole TEED lift, which is the claim that selectivity (not placement,
# not calibrated confidence, not stroke continuity) is the operative property.  Lego's
# native Canny purity is 0.663 vs chair's 0.284, so if the conditional law is right the
# SAME mask should buy little or nothing here -- there is far less texture to suppress.
set -u
cd ~/3dgs_line/tier1
while pgrep -f "run_m1b.py|recall_trackC_detector.py|teedgen_L_detector_chain.sh|teedgen_L_post.sh" >/dev/null; do sleep 20; done
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
SYN=scripts/explore/syn

python -u scripts/recall_trackC_seeds.py --scene lego --sources teed --thrs 0.5 \
  --arms_json out/trackM_arms_lego.json --tag _trackM

COMMON="--scene lego --gate --eval_split test --no_viz"
run () {
  local sc="$1" f="$2"
  local sp="$SYN/finalscore_overall_lego__${sc}.npy"
  local out="out/m1b_lego_tm_${sc}_f${f}.json"
  [ -f "$sp" ] || { echo "MISSING $sp"; return; }
  [ -f "$out" ] && { echo "HAVE $out"; return; }
  echo "=================== ARM ${sc} f=${f} ==================="
  python -u scripts/run_m1b.py $COMMON --score "$sp" --f "$f" --tag "_tm_${sc}_f${f}"
}
for f in 0.50 0.40 0.30 0.22; do
  run m3_masksharplow_d2 "$f"
  run m3_maskM1a_d2 "$f"
  run m1_soft_g1.0 "$f"
  run m2_cc25 "$f"
done
echo "ALL TRACK-M LEGO ARMS DONE"
