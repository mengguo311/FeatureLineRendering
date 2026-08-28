#!/usr/bin/env bash
# CMEPI — temporal no-regress for the two non-TEED frozen learned detectors.
#
# The spec's invariant is "protect the temporal-coherence win (8.5-13.1x); published stroke
# paths must stay bit-identical".  Bit-identity is checked separately against
# out/CMEPI_protected_manifest.sha256.  This script answers the other half: do the NEW
# detectors' strokes hold up temporally, or did the static f-frontier lift get bought with
# flicker?  On lego that trade was real and decisive -- the un-blurred permissive Canny won
# the static number and LOST temporal coherence (11.61x -> 9.67x at 240 frames), which is why
# TEED was still preferred.  So a static LIFT_P with no temporal number attached is not a
# reportable result here.
#
# ARMS: the CHAIR-VAL-selected threshold per detector (pidinet 0.9, dexined 0.7), at the SAME
# f and the SAME trajectory the published control tables used, so the comparison is direct:
#   chair f=0.30, TEST views 5->15, look-at-corrected orbit
#          -> compare against out/m1b_stroke_temporal_table_tc_{tcteed,tccanny}.md
#   lego  f=0.40, same trajectory
#          -> compare against out/m1b_stroke_temporal_table_tcL_{tcteed040,tccanny040,tcsharplow040}.md
#
# --viz_tag is MANDATORY here.  Without it _dump_vis() overwrites the four PUBLISHED
# out/m1b_vector_<scene>_{A_ours,B_baseline}.{svg,png} figures, which carry no tag of their
# own; that clobber has already happened once in this repo's history.
set -u
cd ~/3dgs_line/tier1
# serialise behind BOTH the M1b sweep and the detector-2D chain: GPU 1 is shared and the
# lego MeshOracle (971k crease pts) already OOM'd once with a second job resident.
while pgrep -f 'run_m1b.py|recall_trackC_detector.py|cmepi_detector_chain.sh|m1b_stroke_temporal.py' >/dev/null; do sleep 20; done
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export MESH_ORACLE_MAX_ELEMS=2000000

run () {   # run <scene> <f> <score_arm> <variant>
  local sn="$1" f="$2" sc="$3" vr="$4"
  local src="out/linelets_${sn}_tc_${sc}_f${f}.npz"
  local tbl="out/m1b_stroke_temporal_table_${vr}.json"
  [ -f "$src" ] || { echo "MISSING $src — skipped"; return; }
  [ -f "$tbl" ] && { echo "HAVE ${tbl##*/} — skipped"; return; }
  cp -f "$src" "out/linelets_${sn}_${vr}_test.npz"
  echo "---------- temporal ${sn} / ${sc} f=${f} (variant ${vr}) ----------"
  python -u scripts/m1b_stroke_temporal.py --scenes "$sn" --variant "$vr" \
    --frames 30 60 120 240 --view_a 5 --view_b 15 \
    --tag "_${vr}" --viz_tag "_${vr}"
}

# NOTE the per-scene variant names.  m1b_stroke_temporal.py writes
# out/m1b_stroke_temporal_table<tag>.{json,md} with NO scene in the template, so reusing one
# variant name for chair and lego makes the lego run silently overwrite the chair table.  The
# published tables avoid this the same way (_tc_tcteed for chair vs _tcL_tcteed040 for lego).
run chair 0.30 pidinet_native_0.9 cmepi_pidinet
run chair 0.30 dexined_native_0.7 cmepi_dexined
run lego  0.40 pidinet_native_0.9 cmepiL_pidinet
run lego  0.40 dexined_native_0.7 cmepiL_dexined

echo "CMEPI TEMPORAL DONE"

# the paired per-view significance runs last, on the same card
bash scripts/cmepi_perview.sh
