#!/usr/bin/env bash
set -euo pipefail
cd /home/u00134/3dgs_line/gaer_kernel_space_lines_v01
export TERM=xterm-256color PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2 MAX_JOBS=2
export TMPDIR="$PWD/out/gaer_kernel_space_lines_v01/tmp"
export XDG_CACHE_HOME="$PWD/out/gaer_kernel_space_lines_v01/cache"
export CUDA_CACHE_PATH="$XDG_CACHE_HOME/cuda" MPLCONFIGDIR="$XDG_CACHE_HOME/mpl"
export TORCH_HOME="$XDG_CACHE_HOME/torch" HF_HOME="$XDG_CACHE_HOME/hf"
export PYTHONPYCACHEPREFIX="$XDG_CACHE_HOME/pycache"
exec /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B "$@"
