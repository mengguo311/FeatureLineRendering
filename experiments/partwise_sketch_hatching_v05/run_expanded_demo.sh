#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 2 ]]; then
  echo 'Usage: bash run_expanded_demo.sh UNIT_DIR {replay|query|validate} [--scene chair|lego ...]'
  exit 2
fi
export V05_UNIT_DIR="$1"
mode="$2"
shift 2
export CUDA_VISIBLE_DEVICES=''
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$V05_UNIT_DIR/scratch"
V05_DEMO_SRC="$(cd "$(dirname "$0")" && pwd)"
V05_DEMO_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
"$V05_DEMO_PY" -c 'import sys,json; from pathlib import Path; sys.path.insert(0,sys.argv[1]); import runtime; u=runtime.output_guard(Path(sys.argv[2])); (u/"scratch").mkdir(exist_ok=True); p=json.loads((u/"PROTOCOL.json").read_text()); assert p["unit"]=="unit_005"; [(lambda root: [(_ for _ in ()).throw(ValueError("binding hash mismatch")) if runtime.sha(root/name)!=h else None for name,h in json.loads((root/"BINDING_LOCK.json").read_text())["files"].items()])(u/"results"/scene) for scene in p["scenes"]]' "$V05_DEMO_SRC" "$V05_UNIT_DIR"
case "$mode" in
  replay) exec "$V05_DEMO_PY" "$V05_DEMO_SRC/inspect_footprint_link.py" --unit "$V05_UNIT_DIR" "$@" ;;
  query) exec "$V05_DEMO_PY" "$V05_DEMO_SRC/inspect_footprint_link.py" --unit "$V05_UNIT_DIR" --query "$@" ;;
  validate) exec "$V05_DEMO_PY" "$V05_DEMO_SRC/validate_expanded_unit.py" --unit "$V05_UNIT_DIR" "$@" ;;
  *) echo 'Unknown mode' >&2; exit 2 ;;
esac
