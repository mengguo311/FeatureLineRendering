#!/bin/bash
set -e
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
cd /home/u00134/3dgs_line/tier1
for M in vanilla:cadpartA oracle:cadpartB honest:cadpartH; do
  MODE=${M%%:*}; OUT=${M##*:}
  echo "############ $MODE -> $OUT"
  python -u scripts/xy_gs_train.py --mode $MODE --out /home/u00134/cglib/outputs/${OUT}_static
done
echo "ALL DONE"
