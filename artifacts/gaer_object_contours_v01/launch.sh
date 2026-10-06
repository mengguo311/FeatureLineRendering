#!/usr/bin/env bash
set -uo pipefail
export PATH=/home/u00134/bin/miniconda3/envs/codex-cli/bin:/home/u00134/bin/miniconda3/bin:$PATH
export TERM=xterm-256color
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 MAX_JOBS=2
cd /home/u00134/3dgs_line/gaer_object_contours_v01
mkdir -p out/gaer_object_contours_v01/{logs,tmp,cache}
export TMPDIR="$PWD/out/gaer_object_contours_v01/tmp"
timeout --signal=TERM --kill-after=60 10800 codex exec --sandbox danger-full-access -m gpt-6.1-sol -c 'model_reasoning_effort="xhigh"' - < artifacts/gaer_object_contours_v01/TASK.txt > out/gaer_object_contours_v01/logs/CODEX.stdout.log 2> out/gaer_object_contours_v01/logs/CODEX.stderr.log
rc=$?
printf '%s\n' "$rc" > out/gaer_object_contours_v01/logs/CODEX.exitcode
exit "$rc"
