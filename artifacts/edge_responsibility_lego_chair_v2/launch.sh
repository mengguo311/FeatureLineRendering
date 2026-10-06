#!/bin/bash
export PATH=/home/u00134/bin/miniconda3/envs/codex-cli/bin:/home/u00134/bin/miniconda3/bin:$PATH
export TERM=xterm-256color CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
cd /home/u00134/3dgs_line/edge_responsibility_lego_chair_v2 || exit 2
mkdir -p out/edge_responsibility_lego_chair_v2/tmp
export TMPDIR="$PWD/out/edge_responsibility_lego_chair_v2/tmp"
if timeout --signal=TERM --kill-after=60 10800 codex exec --sandbox danger-full-access -m gpt-6.1-sol -c 'model_reasoning_effort="xhigh"' --output-last-message out/edge_responsibility_lego_chair_v2/AGENT_FINAL.md - < artifacts/edge_responsibility_lego_chair_v2/TASK.txt > out/edge_responsibility_lego_chair_v2/AGENT.log 2>&1; then rc=0; else rc=$?; fi
printf '%s\n' "$rc" > out/edge_responsibility_lego_chair_v2/AGENT_EXIT.txt
tmux wait-for -S sol-edge-responsibility-complete
exit "$rc"
