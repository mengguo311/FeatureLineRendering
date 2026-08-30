#!/usr/bin/env bash
# TRACK L post-steps: viz + temporal no-regress on lego.  Runs after the M1b arms.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1
while pgrep -f "run_m1b.py|recall_trackC_detector.py|teedgen_L_detector_chain.sh" >/dev/null; do sleep 20; done

echo "############ VIZ (v0 = VAL, v5/v25 = held-out TEST) ############"
for F in 0.40 0.30; do
  python -u scripts/recall_trackC_viz.py --scene lego \
    --canny "linelets_lego_tc_canny_f${F}.npz" \
    --teed  "linelets_lego_tc_teed_native_0.5_f${F}.npz" \
    --views 0 5 25 --out_prefix "teed_lego_f${F}"
done
# the spec's named artefact
cp out/teed_lego_f0.40_v0.png  out/teed_lego_v0.png
cp out/teed_lego_f0.40_v25.png out/teed_lego_v25.png

echo "############ TEMPORAL NO-REGRESS (lego, TEST 5->15) ############"
for F in 0.40 0.30; do
  T=$(echo $F | tr -d '.')
  cp out/linelets_lego_tc_canny_f${F}.npz              out/linelets_lego_tccanny${T}_test.npz
  cp out/linelets_lego_tc_teed_native_0.5_f${F}.npz    out/linelets_lego_tcteed${T}_test.npz
  if [ -f out/linelets_lego_tc_cannysharplow_f${F}.npz ]; then
    cp out/linelets_lego_tc_cannysharplow_f${F}.npz    out/linelets_lego_tcsharplow${T}_test.npz
  fi
  for V in tccanny${T} tcteed${T} tcsharplow${T}; do
    [ -f "out/linelets_lego_${V}_test.npz" ] || continue
    echo "---------- temporal lego variant $V ----------"
    python -u scripts/m1b_stroke_temporal.py --scenes lego --variant "$V" \
      --frames 30 60 120 240 --view_a 5 --view_b 15 --tag "_tcL_${V}"
  done
done
echo "TRACK L POST DONE"
