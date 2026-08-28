#!/usr/bin/env bash
# ECO — build the per-gaussian consensus C over the band grid, CHAIR ONLY.
#
# Every knob here is selected on chair VAL and then transferred to lego unchanged, exactly as
# CMEPI selected its detector threshold. rho=7 (the depth-free reading of "epipolar band") is
# deliberately excluded: NG-MEC measured it to remove 0.7% of pixels, i.e. it is vacuous.
set -u
cd ~/3dgs_line/tier1
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export MESH_ORACLE_MAX_ELEMS=2000000
DET="${1:-dexined}"
SCENE="${2:-chair}"
for K in 1 3 5; do
  for TAU in 1.5 2.5; do
    for RHO in 0 0.2; do
      for SG in 4 8 16; do
        TAG="${DET}$([ "$DET" = dexined ] && echo 0.7 || echo 0.5)_K${K}_t${TAU}_r${RHO}_s${SG}"
        if [ -f "out/eco_C_${SCENE}__${TAG}.npy" ]; then echo "HAVE $TAG"; continue; fi
        python -u scripts/eco_consensus.py --scene "$SCENE" --det "$DET" --K "$K" \
          --tau "$TAU" --rho "$RHO" --sigma_c "$SG" 2>&1 | grep -E "^\[eco\] (C mean|edge px)" \
          | sed "s|^|  ${TAG}: |"
      done
    done
  done
done
echo "ECO BAND SWEEP DONE ($DET/$SCENE)"
