#!/usr/bin/env bash
# CMEPI — the 2D detector-level numbers the spec asks for per detector:
# miss-set recovery and precision drop (plus the FP triage that makes the precision guard
# readable: occluding contour / sub-30deg fold / actual texture hallucination).
#
# EVAL-ONLY DIAGNOSTIC (recall_trackC_detector.py imports mesh_oracle for GT labelling).
# It is NOT on the go/no-go path -- the CMEPI verdict is decided at M1b -- but the spec
# requires these numbers reported, and they are what tell a precision drop caused by
# hallucinated texture apart from one caused by drawing occluding contours correctly.
#
# Waits for every M1b arm to release the card first: the lego MeshOracle (971k crease points
# @30deg) already OOM'd once on this shared GPU with a second job resident.
#
# --thrs: the historical grid (0.50..0.995) was read off TEED, whose raw sigmoid FLOORS at
# ~0.4377 and never approaches 0.  DexiNed and PiDiNet span the full [0,1] and are already
# sparse at 0.5, so that grid cannot bracket their operating point.  The grid below does.
# --tag / --det_name keep each detector's output in its own file; without --tag this script
# overwrites out/trackC_detector_<scene>.json unconditionally (it has done so once before).
set -u
cd ~/3dgs_line/tier1
while pgrep -f "run_m1b.py" >/dev/null; do sleep 20; done
source ~/bin/miniconda3/etc/profile.d/conda.sh
conda activate vfsdgs
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export MESH_ORACLE_MAX_ELEMS=2000000

THRS="0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9"

for det in pidinet dexined; do
  for sc in chair lego; do
    out="out/trackC_detector_${sc}_cmepi_${det}.json"
    [ -f "$out" ] && { echo "HAVE ${out##*/} — skipped"; continue; }
    echo "################ DETECTOR-2D ${det} / ${sc} ################"
    python -u scripts/recall_trackC_detector.py --scene "$sc" \
      --teed_cache "out/${det}_edges_${sc}" --det_name "$det" \
      --tag "_cmepi_${det}" --thrs $THRS || echo "FAILED $det $sc"
  done
done
echo "CMEPI DETECTOR-2D DONE"
