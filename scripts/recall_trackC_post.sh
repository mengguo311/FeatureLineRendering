#!/usr/bin/env bash
# TRACK C post-steps: viz + temporal no-regress. Runs after the M1b extension arms.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
cd ~/3dgs_line/tier1

echo "############ VIZ ############"
python -u scripts/recall_trackC_viz.py --scene chair \
  --canny linelets_chair_tc_canny_f0.30.npz \
  --teed  linelets_chair_tc_teed05_f0.30.npz \
  --views 5 25 --out_prefix teed_chair

echo "############ TEMPORAL NO-REGRESS ############"
# m1b_stroke_temporal.py addresses linelets as linelets_<scene>_<variant>_test.npz
cp out/linelets_chair_tc_canny_f0.30.npz  out/linelets_chair_tccanny_test.npz
cp out/linelets_chair_tc_teed05_f0.30.npz out/linelets_chair_tcteed_test.npz
for V in tccanny tcteed; do
  echo "---------- temporal variant $V ----------"
  python -u scripts/m1b_stroke_temporal.py --scenes chair --variant "$V" \
    --frames 30 60 120 240 --view_a 5 --view_b 15 --tag "_tc_${V}"
done
echo "POST DONE"
