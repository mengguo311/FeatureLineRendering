#!/usr/bin/env bash
set -uo pipefail
cd /home/u00134/3dgs_line/gaer_multiview_contour_lift_v01
export PATH="/home/u00134/bin/miniconda3/envs/codex-cli/bin:/home/u00134/bin/miniconda3/bin:$PATH"
export TERM=xterm-256color PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 MAX_JOBS=2
export TMPDIR="$PWD/out/gaer_multiview_contour_lift_v01/tmp" CUDA_CACHE_PATH="$PWD/out/gaer_multiview_contour_lift_v01/cache/cuda" MPLCONFIGDIR="$PWD/out/gaer_multiview_contour_lift_v01/cache/mpl" XDG_CACHE_HOME="$PWD/out/gaer_multiview_contour_lift_v01/cache"
mkdir -p "$TMPDIR" "$CUDA_CACHE_PATH" "$MPLCONFIGDIR" "$XDG_CACHE_HOME" out/gaer_multiview_contour_lift_v01/logs
set +e
timeout --signal=TERM --kill-after=60 7200 codex --search exec --sandbox danger-full-access -m gpt-6-astra -c 'model_reasoning_effort="ultra"' - < artifacts/gaer_multiview_contour_lift_v01/TASK.txt > out/gaer_multiview_contour_lift_v01/logs/CODEX.stdout.log 2> out/gaer_multiview_contour_lift_v01/logs/CODEX.stderr.log
status=$?
printf '%s\n' "$status" > out/gaer_multiview_contour_lift_v01/logs/CODEX.exitcode
exit "$status"
