#!/bin/bash
export PATH=/home/u00134/bin/miniconda3/envs/codex-cli/bin:/home/u00134/bin/miniconda3/bin:$PATH
export TERM=xterm-256color
cd /mnt/hdd1/u00134/hybrid_raster_trained_models_v1/gaussian_edge_attribution_v1 || exit 2
mkdir -p out/gaussian_edge_attribution_v1
codex exec --sandbox danger-full-access -m gpt-6-astra -c 'model_reasoning_effort="ultra"' --output-last-message out/gaussian_edge_attribution_v1/AGENT_FINAL.md - < artifacts/gaussian_edge_attribution_v1/TASK.txt > out/gaussian_edge_attribution_v1/AGENT.log 2>&1
rc=$?
printf '%s\n' "$rc" > out/gaussian_edge_attribution_v1/AGENT_EXIT.txt
tmux wait-for -S astra-gaussian-attribution-complete
exit "$rc"
