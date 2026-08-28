#!/usr/bin/env bash
# TGAP gate 4 driver — four linelet sets at the operating f, one temporal run each.
#   tgapA  arm A, the committed tuned+len prune                (reference)
#   tgapB  arm B at the VAL-frozen (alpha, beta)               (the gated arm)
#   tgapC  arm C at the VAL-frozen (tau_r, tau_L)              (TEED-blind control)
#   tgapS  arm B at a genuinely SPATIAL (alpha=0.6, beta=0.6)  (so the veto is actually
#          exercised: the frozen pick has alpha=0, i.e. it does not move the prune at all)
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1
F=0.50

python -u scripts/tgap_temporal.py --scene lego --f $F --alpha 0.0 --beta 0.2 \
  --c_tau_r 0.45 --c_tau_L 0.90 --prefix tgap || exit 1
python - <<'PY' || exit 1
import sys; sys.path.insert(0, "scripts")
from tgap_temporal import write_variant
write_variant("lego", 0.50, "tgapS", 0.6, 0.6)
PY

for V in tgapA tgapB tgapC tgapS; do
  [ -f "out/m1b_stroke_temporal_table_${V}.json" ] && { echo "HAVE ${V}"; continue; }
  echo "---------- temporal lego variant $V ----------"
  python -u scripts/m1b_stroke_temporal.py --scenes lego --variant "$V" \
    --frames 30 60 120 240 --view_a 5 --view_b 15 --tag "_${V}" --viz_tag "_${V}" || exit 1
done
echo "TGAP TEMPORAL DONE"
