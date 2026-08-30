#!/usr/bin/env bash
# Arms the first sweep could not run (n_per_view_mean bug) + the threshold probe.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1 MESH_ORACLE_MAX_ELEMS=1500000
cd ~/3dgs_line/tier1
# wait for the first sweep to clear the GPU
while pgrep -u u00134 -f "dexprimary_p0_sweep.sh" >/dev/null 2>&1; do sleep 10; done
run () { echo "############ $*"; python -u scripts/dexprimary_p0.py "$@"; }
for sc in lego chair; do
  run --scene $sc --key native --halfpix 0.0 --src train --n_src 20 --tag _srctrain
  run --scene $sc --key ms     --halfpix 0.5 --src train --n_src 20 --tag _best
  # does DexiNed see the miss-set at ANY threshold?  precision is Phase 1's job.
  run --scene $sc --key ms --halfpix 0.5 --src train --n_src 20 --thr 0.20 --tag _thr020
  run --scene $sc --key ms --halfpix 0.5 --src train --n_src 20 --thr 0.05 --tag _thr005
done
echo "ALL DONE"
