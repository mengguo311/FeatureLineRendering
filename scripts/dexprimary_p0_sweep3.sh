#!/usr/bin/env bash
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1 MESH_ORACLE_MAX_ELEMS=1500000
cd ~/3dgs_line/tier1
while pgrep -u u00134 -f "p0_sweep2" >/dev/null 2>&1; do sleep 10; done
echo "############ --scene chair --key ms --halfpix 0.0 --src test --n_src 10 --tag _ms"
python -u scripts/dexprimary_p0.py --scene chair --key ms --halfpix 0.0 --src test --n_src 10 --tag _ms
echo "SWEEP3 DONE"
