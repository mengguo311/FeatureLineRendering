#!/usr/bin/env bash
# TGAP auxiliary — the spec's prose clause "stronger DT-pull", untuned, two gamma values.
# Widens the DT-pull trust region where the frozen TEED prior agrees; no gate is decided on it.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd ~/3dgs_line/tier1
for G in 0.5 1.0; do
  for f in 0.22 0.30 0.35 0.40 0.45 0.50; do
    python -u scripts/tgap_pull.py --scene lego --f "$f" --pull_gamma "$G" || exit 1
  done
  T=$(python -c "print('' if float('$G')==0 else '_g%g'%float('$G'))")
  for S in val test; do
    python -u scripts/tgap_eval.py --scene lego --split "$S" --arms A,B --pull_tag "$T" \
      --f_only 0.22 0.30 0.35 0.40 0.45 0.50 --tag "$T" || exit 1
  done
done
echo "TGAP PULLGAMMA DONE"
