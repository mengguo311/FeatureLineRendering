#!/bin/bash
# EPIPOLAR ACCUMULATION TEST runner: stages labels -> gbuf (GPU-light) for one scene.
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1 MESH_ORACLE_MAX_ELEMS=2000000
cd ~/3dgs_line/tier1
SCENE=$1; shift
for st in "$@"; do
  echo "=== $(date) stage $st scene $SCENE ==="
  python -u scripts/epi_accum.py --scene $SCENE --stage $st || { echo "STAGE $st FAILED"; exit 1; }
done
echo "=== $(date) DONE $SCENE ==="
