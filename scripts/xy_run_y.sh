#!/bin/bash
set -e
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1 MESH_ORACLE_MAX_ELEMS=1500000
cd /home/u00134/3dgs_line/tier1
# wait for the A/B/B' training chain to finish
while ! grep -q "ALL DONE" logs/xy_abc.log 2>/dev/null; do
  if ! pgrep -u u00134 -f xy_gs_train.py >/dev/null && ! grep -q "ALL DONE" logs/xy_abc.log; then
    echo "TRAINING DIED"; tail -20 logs/xy_abc.log; exit 1
  fi
  sleep 20
done
echo "=== training done, running frozen extraction ==="
for S in cadpartA cadpartB cadpartH; do
  echo "############ p1b $S"
  python -u scripts/dexprimary_p1b.py --scene $S --n_ref 40 --K 6 --halfpix 0 --tag _ref40
done
echo "=== extraction done, running Experiment Y eval ==="
python -u scripts/xy_expY.py
echo "Y ALL DONE"
