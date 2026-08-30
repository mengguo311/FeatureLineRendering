#!/usr/bin/env bash
# The single number the conditional law turns on, measured identically on both scenes:
# WHAT DOES UN-BLURRING DO TO EDGE PURITY?
# On lego it RAISES it (0.637 -> 0.751) while multiplying recall 5x, which is why the cheap
# fix wins there.  The chair side of that comparison currently comes from TRACK A's table,
# which uses a slightly different mask definition, so re-measure it with THIS script.
set -u
cd ~/3dgs_line/tier1
until grep -q "QUEUE2 COMPLETE" logs/teedgen_queue2.log; do sleep 30; done
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export MESH_ORACLE_MAX_ELEMS=2000000
python -u scripts/recall_trackC_detector.py --scene chair --canny_variants \
  > logs/teedgen_M_detector_chair.log 2>&1 && echo "chair detector OK" || echo "chair detector FAILED"
echo "QUEUE3 COMPLETE"
