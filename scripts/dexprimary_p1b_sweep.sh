#!/usr/bin/env bash
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1 MESH_ORACLE_MAX_ELEMS=1500000
cd ~/3dgs_line/tier1
until grep -q "wrote out/dexprimary_p1b_paired.json\|Traceback" logs/dexp1b_paired.log; do sleep 10; done
R () { echo "############ $*"; python -u scripts/dexprimary_p1b.py "$@"; }
# budget-matched to Phase 0's chair cap -> tri vs single-view at identical point count
R --n_ref 20 --K 6 --budget 85325 --tag _cap
# rho: 0.02 is essentially the single-view lift; 0.5 is a wide search that must find depth itself
R --n_ref 20 --K 6 --rho 0.02 --tag _rho002
R --n_ref 20 --K 6 --rho 0.50 --tag _rho050
# how many neighbour views does the consensus need?
R --n_ref 20 --K 2  --tag _K2
R --n_ref 20 --K 12 --tag _K12
# more reference views = more coverage
R --n_ref 40 --K 6 --tag _ref40
echo "P1B SWEEP DONE"
