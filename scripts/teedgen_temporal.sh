#!/usr/bin/env bash
# TRACK L temporal no-regress on lego, three arms at f=0.40 (the in-band operating point).
# Trimmed from six arms because each variant costs ~24 min (30/60/120/240-frame trajectories)
# and it must not block the remaining M1b sweeps -- it is CPU-bound, so it runs alongside them.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1
for V in tccanny040 tcteed040 tcsharplow040; do
  [ -f "out/linelets_lego_${V}_test.npz" ] || { echo "missing linelets for $V"; continue; }
  echo "---------- temporal lego $V ----------"
  python -u scripts/m1b_stroke_temporal.py --scenes lego --variant "$V" \
    --frames 30 60 120 240 --view_a 5 --view_b 15 --tag "_tcL_${V}" || true
done
echo "TEMPORAL DONE"
