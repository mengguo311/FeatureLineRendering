#!/usr/bin/env bash
# ECO — M1b for the epipolar-consensus arms.
#
# Identical run_m1b.py path and identical published-baseline flags to every CMEPI/TEED arm;
# ONLY --score differs, and every ECO score is the SAME base carrier vector re-ranked by the
# consensus channel.  n_seeds is therefore bit-identical to the base arm at every f.
#
# Arms are tagged under a PRIVATE _ec_ prefix, NOT under _tc_.  Reason: cmepi_table.py and
# teedgen_verdict.py glob m1b_<scene>_tc_*.json, and the CMEPI table is a committed artifact
# (329b65e).  Putting ECO arms under _tc_ would silently change it.  scripts/eco_table.py
# instead pulls the PUBLISHED canny frontier from the _tc_ glob explicitly and the ECO arms
# from _ec_, so LIFT_P is read against the same frontier without polluting anything.
#
# f grid: the chair band is [0.30,0.50] and the lego band [0.15,0.50] per eco_spec.md; 0.22 and
# 0.15 are swept on chair too so the sign below the band is visible (CMEPI's lift was band-local).
set -u
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export MESH_ORACLE_MAX_ELEMS=2000000
cd ~/3dgs_line/tier1
SYN=scripts/explore/syn
SPLIT="${1:-test}"
PX="ec"; [ "$SPLIT" = val ] && PX="ecv"

m1b () {   # m1b <scene> <arm> <f>
  local sn="$1" sc="$2" f="$3"
  local sp="$SYN/finalscore_overall_${sn}__${sc}.npy"
  local out="out/m1b_${sn}_${PX}_${sc}_f${f}.json"
  [ -f "$sp" ] || { echo "MISSING $sp — skipped"; return; }
  [ -f "$out" ] && { echo "HAVE ${out##*/} — skipped"; return; }
  echo "=================== ${sn}/${SPLIT} ARM ${sc} f=${f} ==================="
  python -u scripts/run_m1b.py --scene "$sn" --gate --eval_split "$SPLIT" --no_viz \
    --score "$sp" --f "$f" --tag "_${PX}_${sc}_f${f}"
}

ARMS="eco_dex_add_l0p25_K3 eco_dex_veto_c0p9_K3 eco_dex_add_l0p25_K1 eco_dex_add_l0p25_K5 eco_teed_add_l0p25_K3"
if [ "$SPLIT" = val ]; then
  # M1b-level VAL confirmation of the chair-VAL selection (CMEPI never did this; it was a
  # documented weakness there).  Base carriers included so the comparison is like-for-like.
  for sc in eco_dex_add_l0p25_K3 dexined_native_0.7 eco_dex_veto_c0p9_K3; do
    for f in 0.50 0.45 0.40 0.35 0.30; do m1b chair "$sc" "$f"; done
  done
else
  for sc in $ARMS; do
    for f in 0.50 0.45 0.40 0.35 0.30 0.22 0.15; do m1b chair "$sc" "$f"; done
  done
  for sc in $ARMS; do
    for f in 0.50 0.45 0.40 0.35 0.30 0.22 0.15; do m1b lego "$sc" "$f"; done
  done
fi
echo "ECO M1b DONE ($SPLIT)"
