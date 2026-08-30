#!/usr/bin/env bash
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1 MESH_ORACLE_MAX_ELEMS=1500000
cd ~/3dgs_line/tier1
R () { echo "############ $*"; python -u scripts/dexprimary_p0.py "$@"; }
R --scene chair --key ms --halfpix 0.0 --src test --n_src 10 --tag _ms
R --scene lego  --key native --halfpix 0.0 --src train --n_src 20 --budget 89748 --tag _urscap
R --scene chair --key native --halfpix 0.0 --src train --n_src 20 --budget 85325 --tag _urscap
echo "SWEEP5 DONE"
