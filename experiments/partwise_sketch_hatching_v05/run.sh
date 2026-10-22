#!/usr/bin/env bash
set -euo pipefail
task_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
task_python="${DEMO_PY:-/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python}"
command_name="${1:-}"
if [[ $# -gt 0 ]]; then shift; fi
case "$command_name" in
  replay) task_script=replay_link.py ;;
  query) task_script=query_path.py ;;
  validate) task_script=validate_unit.py ;;
  *) echo 'Usage: run.sh {replay|query|validate} --unit PATH [command options]' >&2; exit 2 ;;
esac
exec "$task_python" "$task_dir/$task_script" "$@"
