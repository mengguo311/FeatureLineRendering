#!/usr/bin/env bash
# Re-run the raw-TEED temporal baseline IN THIS SESSION. The published 13.12x comes from the
# previous experiment; the gate clause passes by 0.19x, which is too small a margin to rest on
# a cross-run comparison even though the BASELINE column already matches to 0.001.
set -u
cd ~/3dgs_line/tier1
until grep -q "NGMEC POST DONE" logs/ngmec_s1_post.log 2>/dev/null; do sleep 30; done
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
python -u scripts/m1b_stroke_temporal.py --scenes chair --variant tcteed \
  --frames 30 60 120 240 --view_a 5 --view_b 15 --tag _ngbase
echo "NGMEC TEMPBASE DONE"
