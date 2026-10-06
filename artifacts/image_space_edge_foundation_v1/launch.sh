#!/bin/bash
export PATH=/home/u00134/bin/miniconda3/envs/codex-cli/bin:/home/u00134/bin/miniconda3/bin:$PATH
export TERM=xterm-256color CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
cd /home/u00134/3dgs_line/image_space_edge_foundation_v1 || exit 2
mkdir -p out/image_space_edge_foundation_v1/tmp
export TMPDIR="$PWD/out/image_space_edge_foundation_v1/tmp"
if timeout --signal=TERM --kill-after=60 7200 codex exec --sandbox danger-full-access -m gpt-6.1-sol -c 'model_reasoning_effort="xhigh"' --output-last-message out/image_space_edge_foundation_v1/AGENT_FINAL.md - < artifacts/image_space_edge_foundation_v1/TASK.txt > out/image_space_edge_foundation_v1/AGENT.log 2>&1; then rc=0; else rc=$?; fi
printf '%s\n' "$rc" > out/image_space_edge_foundation_v1/AGENT_EXIT.txt
tmux wait-for -S sol-image-space-complete
exit "$rc"
