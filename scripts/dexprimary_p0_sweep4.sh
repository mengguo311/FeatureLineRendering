#!/usr/bin/env bash
# BUDGET-MATCHED arm: URS's own protocol (voxel-dedup to a fixed cap), applied to EVERY cloud
# including the chance control -- the control URS did not have.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1 MESH_ORACLE_MAX_ELEMS=1500000
cd ~/3dgs_line/tier1
while pgrep -u u00134 -f "p0_sweep[23]" >/dev/null 2>&1; do sleep 10; done
echo "############ lego budget=89748 (URS cap), src=TRAIN20, native thr0.5 hp0"
python -u scripts/dexprimary_p0.py --scene lego --key native --halfpix 0.0 --src train \
    --n_src 20 --budget 89748 --tag _urscap
echo "############ chair budget=85325 (URS chair baseline carrier), src=TRAIN20"
python -u scripts/dexprimary_p0.py --scene chair --key native --halfpix 0.0 --src train \
    --n_src 20 --budget 85325 --tag _urscap
echo "SWEEP4 DONE"
