#!/usr/bin/env bash
# Phase 0 fairness sweep: every arm that could plausibly rescue the idea.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1 MESH_ORACLE_MAX_ELEMS=1500000
cd ~/3dgs_line/tier1
run () {  # scene key halfpix src n_src tag
  echo "############ $1 key=$2 halfpix=$3 src=$4 n_src=$5 tag=$6"
  python -u scripts/dexprimary_p0.py --scene "$1" --key "$2" --halfpix "$3" \
      --src "$4" --n_src "$5" --tag "$6"
}
for sc in lego chair; do
  run $sc native 0.5 test  10 _hp05        # A: grid-offset correction
  run $sc ms     0.0 test  10 _ms          # B: multi-scale detector (more edges)
  run $sc native 0.0 train 20 _srctrain    # C: URS-comparable (20 TRAIN views, no leakage)
  run $sc ms     0.5 train 20 _best        # D: every knob set in the idea's favour
done
echo "ALL DONE"
