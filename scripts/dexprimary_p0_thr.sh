#!/usr/bin/env bash
# Does DexiNed see the lego miss-set at ANY threshold?  Precision is Phase 1's job, so this
# arm buys recall with precision deliberately: NMS + ms + half-pixel + 20 TRAIN source views.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1 MESH_ORACLE_MAX_ELEMS=1500000
cd ~/3dgs_line/tier1
for sc in lego chair; do
  for t in 0.20 0.05; do
    echo "############ $sc thr=$t (ms, hp0.5, TRAIN20)"
    python -u scripts/dexprimary_p0.py --scene $sc --key ms --halfpix 0.5 \
        --src train --n_src 20 --thr $t --tag "_thr${t/./}"
  done
done
echo "THR SWEEP DONE"
