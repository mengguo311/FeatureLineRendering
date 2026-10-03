#!/bin/bash
export PATH=/home/u00134/bin/miniconda3/envs/codex-cli/bin:/home/u00134/bin/miniconda3/bin:$PATH
export TERM=xterm-256color
cd /mnt/hdd1/u00134/hybrid_raster_trained_models_v1/mic_fixed3d_standalone || exit 2
mkdir -p out/mic_persistent_line_feasibility_v1
codex exec --sandbox danger-full-access -m gpt-6-astra -c 'model_reasoning_effort="ultra"' --output-last-message out/mic_persistent_line_feasibility_v1/RESUME_FINAL.md - < artifacts/mic_persistent_line_feasibility_v1/RESUME_TASK.txt > out/mic_persistent_line_feasibility_v1/RESUME_AGENT.log 2>&1
rc=$?
printf '%s\n' "$rc" > out/mic_persistent_line_feasibility_v1/RESUME_EXIT.txt
tmux wait-for -S astra-mic-standalone-complete
exit "$rc"
