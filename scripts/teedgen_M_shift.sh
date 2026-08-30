#!/usr/bin/env bash
# TRACK M shifted-mask control, run ahead of the main queue (it is the decisive control and
# the queue's temporal step is CPU-bound, so the card has room).  Arms already produced are
# skipped, so the queue re-running this later is a no-op.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1
SYN=scripts/explore/syn
python -u scripts/recall_trackC_seeds.py --scene chair --sources teed --thrs 0.5 \
  --arms_json out/trackM_arms_chair2.json --tag _trackM2
for f in 0.40 0.35 0.30; do
  for sc in m3_shift15_d2 m3_shift40_d2; do
    out="out/m1b_chair_tm_${sc}_f${f}.json"
    [ -f "$out" ] && { echo "HAVE $out"; continue; }
    echo "=================== chair/tm ARM ${sc} f=${f} ==================="
    python -u scripts/run_m1b.py --scene chair --gate --eval_split test --no_viz \
      --score "$SYN/finalscore_overall_chair__${sc}.npy" --f "$f" --tag "_tm_${sc}_f${f}"
  done
done
echo "SHIFT CONTROL DONE"
