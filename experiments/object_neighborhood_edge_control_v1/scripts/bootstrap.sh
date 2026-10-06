#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 CUDA_VISIBLE_DEVICES=0
experiment_root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$experiment_root"
stage_out="$experiment_root/out/object_neighborhood_edge_control_v1"
research_python=/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
mkdir -p "$stage_out/vendor" "$stage_out/tmp"
export TMPDIR="$stage_out/tmp"
"$research_python" -c "import sys;sys.path.insert(0,'experiments/object_neighborhood_edge_control_v1/src');from runtime import resource_guard;print(resource_guard())"
clone_pin() {
    local repo_url="$1" destination="$2" commit_sha="$3"
    if [ ! -d "$destination/.git" ]; then git clone --depth 1 "$repo_url" "$destination"; fi
    git -C "$destination" fetch --depth 1 origin "$commit_sha"
    git -C "$destination" checkout --detach "$commit_sha"
}
clone_pin https://github.com/graphdeco-inria/gaussian-splatting.git "$stage_out/vendor/gaussian-splatting" 472689c0dc70417448fb451bf529ae532d32c095
clone_pin https://github.com/lkeab/gaussian-grouping.git "$stage_out/vendor/gaussian-grouping" 0ab60afed3385b717c985af1d30a20f7b0884c89
clone_pin https://github.com/ZestfulJX/COB-GS.git "$stage_out/vendor/COB-GS" 559a9fc11888b06d59969eea9534b1a6f845a585
git -C "$stage_out/vendor/gaussian-splatting" submodule update --init --depth 1 submodules/diff-gaussian-rasterization submodules/simple-knn
"$research_python" -m pip install --target "$stage_out/deps" --no-deps ninja imageio-ffmpeg flip-evaluator==1.7
export PATH="$stage_out/deps/bin:$PATH" PYTHONPATH="$stage_out/deps"
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/build_native.py
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/build_cob.py
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/pin_sources.py
