#!/usr/bin/env bash
# THE DECISIVE CONTROL: is a LEARNED detector needed, or does un-blurring the existing
# Canny buy the same recall?  TRACK A showed a permissive Canny recovers 90% of the M1a
# Canny's miss-set in 2D; this puts that through the SAME pipeline so the claim
# "TEED is the lever" is tested against its cheapest possible alternative.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1; cd ~/3dgs_line/tier1
SYN=scripts/explore/syn
echo "########## seed frontier with re-tuned Canny arms ##########"
python -u scripts/recall_trackC_seeds.py --scene chair --key native --thrs 0.5 \
  --sources teed --canny_variants
echo "########## M1b for the re-tuned Canny arms ##########"
COMMON="--scene chair --gate --eval_split test --no_viz"
for arm in cannysharp cannysharplow; do
  for f in 0.40 0.30 0.22; do
    echo "=================== ARM ${arm} f=${f} ==================="
    python -u scripts/run_m1b.py $COMMON --score "$SYN/finalscore_overall_chair__${arm}.npy" --f "$f" --tag "_tc_${arm}_f${f}"
  done
done
echo "CONTROL DONE"
