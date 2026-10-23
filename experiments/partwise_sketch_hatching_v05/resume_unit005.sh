#!/usr/bin/env bash
set -euo pipefail
V05_RESUME_SRC="$(cd "$(dirname "$0")" && pwd)"
V05_RESUME_UNIT=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_005
V05_RESUME_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
name="$1"
stage="$2"
shift 2
case "$stage" in
  build|budget|match|evaluate)
    target="$V05_RESUME_UNIT/source_snapshot/run_expanded_unit.py"
    args=(--unit "$V05_RESUME_UNIT" --stage "$stage" "$@") ;;
  validate)
    target="$V05_RESUME_SRC/validate_expanded_unit.py"
    args=(--unit "$V05_RESUME_UNIT" "$@") ;;
  media)
    target="$V05_RESUME_UNIT/source_snapshot/make_footprint_media.py"
    args=(--unit "$V05_RESUME_UNIT" "$@") ;;
  replay|query)
    target="$V05_RESUME_UNIT/source_snapshot/inspect_footprint_link.py"
    args=(--unit "$V05_RESUME_UNIT" "$@")
    if [[ "$stage" == query ]]; then args+=(--query); fi ;;
  custom)
    target="$1"
    shift
    args=("$@") ;;
  *) echo 'Unknown stage' >&2; exit 2 ;;
esac
exec "$V05_RESUME_PY" "$V05_RESUME_SRC/continuation_exec.py" "$V05_RESUME_UNIT/source_snapshot/run_logged.py" --unit "$V05_RESUME_UNIT" --name "$name" -- "$V05_RESUME_PY" "$V05_RESUME_SRC/continuation_exec.py" "$target" "${args[@]}"
