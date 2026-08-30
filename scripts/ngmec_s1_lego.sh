#!/usr/bin/env bash
# lego arm of NG-MEC Stage 1. SAME (K, m, tau, rho) as chair -- no per-scene retuning, and
# the TEED threshold is still chair's VAL 0.5.
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True MESH_ORACLE_MAX_ELEMS=2000000
cd ~/3dgs_line/tier1
python -u scripts/recall_trackC_seeds.py --scene lego --sources teed --thrs 0.5 \
  --arms_json out/ngmec_arms_lego.json --tag _ngmec
bash scripts/ngmec_s1_m1b.sh lego "epi_t1.5_r0_m3 epi_t2.5_r0_m3 epi_t1.5_r0.2_m4 epi_t1.5_r0_m4" "0.50 0.45 0.40 0.35 0.30 0.22"
