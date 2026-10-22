#!/bin/bash
set -eu
if [ "$#" -lt 2 ]; then
  echo 'Usage: run_footprint.sh UNIT_DIR {stage|replay|query|validate} [arguments]'
  exit 2
fi
unit_dir="$1"
mode="$2"
shift 2
export V05_UNIT_DIR="$unit_dir"
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
task_python=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
case "$mode" in
  stage) exec "$task_python" "$script_dir/run_footprint_unit.py" --unit "$unit_dir" "$@" ;;
  replay) exec "$task_python" "$script_dir/inspect_footprint_link.py" --unit "$unit_dir" "$@" ;;
  query) exec "$task_python" "$script_dir/inspect_footprint_link.py" --unit "$unit_dir" --query "$@" ;;
  validate) exec "$task_python" "$script_dir/validate_footprint_unit.py" --unit "$unit_dir" "$@" ;;
  *) echo 'Unknown command' >&2; exit 2 ;;
esac
