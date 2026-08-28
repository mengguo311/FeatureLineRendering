#!/usr/bin/env bash
# TGAP gate 4, CORRECTED convention — the chainer is fed the RAW half-lengths for every arm,
# so all arms share one chaining operator and differ only in the prune mask (see the docstring
# of scripts/tgap_temporal.py).  Under this convention the VAL-frozen arm B (alpha = 0) has a
# bit-identical carrier to arm A, so only the arms that actually move the prune are run:
#   tgapA   arm A                                   reference
#   tgapS   arm B at a spatial (alpha=0.6, beta=0.6) the arm that exercises the veto
#   tgapC   arm C at the VAL-frozen tau_r = 0.45     TEED-blind control, same keep-count scale
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1

python -u scripts/tgap_temporal.py --scene lego --f 0.50 --alpha 0.0 --beta 0.2 \
  --c_tau_r 0.45 --c_tau_L 0.90 --prefix tgap --stroke_lengths raw || exit 1
python - <<'PY' || exit 1
import sys; sys.path.insert(0, "scripts")
from tgap_temporal import write_variant
write_variant("lego", 0.50, "tgapS", 0.6, 0.6, stroke_lengths="raw")
PY

for V in tgapA tgapS tgapC; do
  [ -f "out/m1b_stroke_temporal_table_${V}.json" ] && { echo "HAVE ${V}"; continue; }
  echo "---------- temporal lego variant $V (raw stroke lengths) ----------"
  python -u scripts/m1b_stroke_temporal.py --scenes lego --variant "$V" \
    --frames 30 60 120 240 --view_a 5 --view_b 15 --tag "_${V}" --viz_tag "_${V}" || exit 1
done
echo "TGAP TEMPORAL(raw) DONE"
