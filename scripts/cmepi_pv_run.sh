#!/usr/bin/env bash
# CMEPI — paired PER-VIEW significance, headline arms, matched f=0.40.
#
# Every M1b P/R is a MEAN over the 10 held-out TEST views and the per-view spread on chair is
# 0.05-0.12, wide enough that a +0.02..+0.06 LIFT_P could in principle be carried by one or two
# views.  So the CMEPI orderings are re-read as PAIRED per-view differences at MATCHED f: same
# view, same protocol, same seed count, only the frozen 2D detector differs.  The published TEED
# result quoted exactly this test (lego: t=+9.88, 10/10 views), so the comparison is symmetric.
#
# f=0.40 is the middle of the CMEPI GO band [0.30,0.50] and is where every arm exists on both
# scenes.  --out is passed so the published out/teedgen_perview_<scene>.json is not touched.
#
# NO pgrep wait-guard here, deliberately: `pgrep -f <pattern>` also matches the harness shells
# whose own command line quotes the pattern, which makes such a guard wait forever.  The card is
# checked to be free before this is launched instead.
set -u
cd ~/3dgs_line/tier1
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export MESH_ORACLE_MAX_ELEMS=2000000

echo "################ PER-VIEW PAIRED — CHAIR f=0.40 ################"
python -u scripts/teedgen_perview.py --scene chair --out out/cmepi_perview_chair.json --pairs \
  tc_teed05_f0.40:tc_canny_f0.40 \
  tc_dexined_native_0.7_f0.40:tc_canny_f0.40 \
  tc_dexined_native_0.5_f0.40:tc_canny_f0.40 \
  tc_pidinet_native_0.9_f0.40:tc_canny_f0.40 \
  tc_pidinet_native_0.5_f0.40:tc_canny_f0.40

echo "################ PER-VIEW PAIRED — LEGO f=0.40 ################"
python -u scripts/teedgen_perview.py --scene lego --out out/cmepi_perview_lego.json --pairs \
  tc_teed_native_0.5_f0.40:tc_canny_f0.40 \
  tc_dexined_native_0.7_f0.40:tc_canny_f0.40 \
  tc_dexined_native_0.5_f0.40:tc_canny_f0.40 \
  tc_pidinet_native_0.9_f0.40:tc_canny_f0.40 \
  tc_pidinet_native_0.7_f0.40:tc_canny_f0.40 \
  tc_pidinet_native_0.5_f0.40:tc_canny_f0.40

echo "CMEPI PER-VIEW DONE"
