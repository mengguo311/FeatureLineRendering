#!/usr/bin/env bash
# NG-MEC Stage 1 — M1b on held-out TEST for the epipolar-consensus arms vs raw TEED.
# Identical run_m1b.py path and published-baseline flags for every arm; only --score differs,
# and those scores differ only in whether the TEED edge map was epipolar-consensus filtered.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export MESH_ORACLE_MAX_ELEMS=2000000
cd ~/3dgs_line/tier1
SYN=scripts/explore/syn
SCENE="${1:?scene}"; shift
ARMS="${1:?arms}"; shift
FS="${1:?fs}"; shift
for sc in $ARMS; do
  for f in $FS; do
    sp="$SYN/finalscore_overall_${SCENE}__${sc}.npy"
    out="out/m1b_${SCENE}_ng_${sc}_f${f}.json"
    [ -f "$sp" ] || { echo "MISSING $sp"; continue; }
    [ -f "$out" ] && { echo "HAVE ${out##*/}"; continue; }
    echo "=================== ${SCENE} ARM ${sc} f=${f} ==================="
    python -u scripts/run_m1b.py --scene "$SCENE" --gate --eval_split test --no_viz \
      --score "$sp" --f "$f" --tag "_ng_${sc}_f${f}"
  done
done
echo "NGMEC M1B DONE ${SCENE}"
