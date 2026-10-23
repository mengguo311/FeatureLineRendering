#!/usr/bin/env bash
set -euo pipefail
export CUDA_VISIBLE_DEVICES=''
export V05_UNIT_DIR=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_005
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$V05_UNIT_DIR/scratch"
V05_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
V05_SRC="$(cd "$(dirname "$0")" && pwd)"
if [[ "${1:-}" == pipeline ]]; then
  for scene in chair lego; do
    "$V05_PY" "$V05_SRC/run_logged.py" --unit "$V05_UNIT_DIR" --name "build_$scene" -- "$V05_PY" "$V05_UNIT_DIR/source_snapshot/run_expanded_unit.py" --unit "$V05_UNIT_DIR" --stage build --scene "$scene"
    for index in 0 1 2 3; do
      "$V05_PY" "$V05_SRC/run_logged.py" --unit "$V05_UNIT_DIR" --name "budget_${scene}_$index" -- "$V05_PY" "$V05_UNIT_DIR/source_snapshot/run_expanded_unit.py" --unit "$V05_UNIT_DIR" --stage budget --scene "$scene" --index "$index"
    done
    "$V05_PY" "$V05_SRC/run_logged.py" --unit "$V05_UNIT_DIR" --name "match_$scene" -- "$V05_PY" "$V05_UNIT_DIR/source_snapshot/run_expanded_unit.py" --unit "$V05_UNIT_DIR" --stage match --scene "$scene"
    for index in 0 1 2 3; do
      "$V05_PY" "$V05_SRC/run_logged.py" --unit "$V05_UNIT_DIR" --name "evaluate_${scene}_$index" -- "$V05_PY" "$V05_UNIT_DIR/source_snapshot/run_expanded_unit.py" --unit "$V05_UNIT_DIR" --stage evaluate --scene "$scene" --index "$index"
    done
  done
else
  exec "$V05_PY" "$V05_SRC/run_expanded_unit.py" --unit "$V05_UNIT_DIR" "$@"
fi
