#!/usr/bin/env bash
set -euo pipefail
export V05_UNIT_DIR=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_005
export CUDA_VISIBLE_DEVICES=''
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$V05_UNIT_DIR/scratch"
V05_STAGE_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
V05_STAGE_SRC="$(cd "$(dirname "$0")" && pwd)"
name="$1"
stage="$2"
shift 2
case "$stage" in
  build|budget|match|evaluate)
    exec "$V05_STAGE_PY" "$V05_STAGE_SRC/run_logged.py" --unit "$V05_UNIT_DIR" --name "$name" -- "$V05_STAGE_PY" "$V05_UNIT_DIR/source_snapshot/run_expanded_unit.py" --unit "$V05_UNIT_DIR" --stage "$stage" "$@" ;;
  validate)
    exec "$V05_STAGE_PY" "$V05_STAGE_SRC/run_logged.py" --unit "$V05_UNIT_DIR" --name "$name" -- "$V05_STAGE_PY" "$V05_STAGE_SRC/validate_expanded_unit.py" --unit "$V05_UNIT_DIR" "$@" ;;
  media)
    exec "$V05_STAGE_PY" "$V05_STAGE_SRC/run_logged.py" --unit "$V05_UNIT_DIR" --name "$name" -- "$V05_STAGE_PY" "$V05_UNIT_DIR/source_snapshot/make_footprint_media.py" --unit "$V05_UNIT_DIR" ;;
  replay|query)
    exec "$V05_STAGE_PY" "$V05_STAGE_SRC/run_logged.py" --unit "$V05_UNIT_DIR" --name "$name" -- bash "$V05_STAGE_SRC/run_expanded_demo.sh" "$V05_UNIT_DIR" "$stage" "$@" ;;
  *) echo 'Unknown stage' >&2; exit 2 ;;
esac
