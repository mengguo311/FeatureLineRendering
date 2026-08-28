#!/usr/bin/env bash
# TGAP — everything that still needs the GPU after the temporal queue frees it.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1

echo "########## diagnostics (stratified AUC + label dump) ##########"
for spec in "0.30 1.0 1.0 _a1b1" "0.50 1.0 1.0 _a1b1" "1.00 1.0 1.0 _a1b1" "0.50 0.4 0.4 _a04b04"; do
  set -- $spec
  python -u scripts/tgap_diag.py --scene lego --f "$1" --alpha "$2" --beta "$3" --tag "$4" \
    > "logs/tgap_diag_f$1$4.log" 2>&1 || exit 1
  echo "  diag f=$1 $4 done"
done

echo "########## paired per-view A vs B ##########"
python -u scripts/tgap_paired.py || exit 1

echo "########## auxiliary: the spec's 'stronger DT-pull' clause, untuned ##########"
bash scripts/tgap_pullgamma.sh || exit 1
echo "TGAP FINISH DONE"
