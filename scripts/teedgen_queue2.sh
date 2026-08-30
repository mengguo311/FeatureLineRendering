#!/usr/bin/env bash
# Follow-on queue: the two robustness controls a sceptic gets to demand.
#  (a) chair's canny frontier extended to f=0.70/1.00.  Lego's LIFT_P was read against a
#      frontier swept to f=1.00 (it had to be -- lego's canny P RISES with f).  Chair's was
#      only swept to 0.50.  Chair's P falls with f so extending cannot help canny, but the
#      asymmetry has to be closed by measurement, not by argument.
#  (b) PAIRED PER-VIEW tests for every headline ordering.  All M1b P/R here are means over
#      10 TEST views and the per-view sd on chair is 0.05-0.12.
set -u
cd ~/3dgs_line/tier1
until grep -q "QUEUE COMPLETE" logs/teedgen_queue4.log 2>/dev/null; do sleep 30; done
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export MESH_ORACLE_MAX_ELEMS=2000000
SYN=scripts/explore/syn

echo "########## (a) chair canny frontier extension ##########"
for f in 0.70 1.00; do
  out="out/m1b_chair_tc_canny_f${f}.json"
  [ -f "$out" ] && { echo "HAVE $out"; continue; }
  python -u scripts/run_m1b.py --scene chair --gate --eval_split test --no_viz \
    --score "$SYN/finalscore_overall_chair__canny.npy" --f "$f" --tag "_tc_canny_f${f}"
  cp -f "$out" "out/m1b_chair_tm_canny_f${f}.json"
done

echo "########## (b) paired per-view tests — LEGO ##########"
python -u scripts/teedgen_perview.py --scene lego --pairs \
  tc_teed_native_0.5_f0.30:tc_canny_f0.30 \
  tc_cannysharplow_f0.30:tc_canny_f0.30 \
  tc_cannysharplow_f0.30:tc_teed_native_0.5_f0.30 \
  tc_cannysharplow_f0.40:tc_teed_native_0.5_f0.40 \
  tc_teed_native_0.5_f0.40:tc_canny_f0.40

echo "########## (b) paired per-view tests — CHAIR ##########"
python -u scripts/teedgen_perview.py --scene chair --pairs \
  tm_m3_masksharplow_d2_f0.40:tc_cannysharplow_f0.40 \
  tm_m3_masksharplow_d2_f0.40:tc_canny_f0.40 \
  tc_teed05_f0.40:tc_canny_f0.40 \
  tm_m1_soft_g1.0_f0.40:tc_teed05_f0.40 \
  tm_m2_cc25_f0.40:tc_teed05_f0.40 \
  tm_m3_shift15_d2_f0.40:tm_m3_masksharplow_d2_f0.40
echo "QUEUE2 COMPLETE"
