#!/usr/bin/env bash
# The lego MeshOracle is heavy (971k crease pts @30deg) and OOM'd once with a second job
# on the card, so this waits until every M1b sweep has released its slot and runs ALONE.
set -u
cd ~/3dgs_line/tier1
while pgrep -f "run_m1b.py" >/dev/null; do sleep 20; done
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
python -u scripts/recall_trackC_detector.py --scene lego --canny_variants \
  > logs/teedgen_L_detector_lego.log 2>&1
echo "DETECTOR DONE rc=$?"
