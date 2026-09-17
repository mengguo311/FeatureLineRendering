# 官方 RGB 核验：最终采用 upstream 原码 + upstream 原始 CUDA 内核

此报告及 official_rgb_verification.json **取代** PHASE0.md/renderer_smoke.json 对原环境 rasterizer 的初步判断。早期 smoke 证明官方 Python 接口能运行，但底层包 direct_url 指向已不存在的旧 SC-GS 源码，不能据此声称已核验官方内核。

已修正：
- Python renderer：从外部 GS 仓库 472689c0dc70417448fb451bf529ae532d32c095 的 Git object 读取未修改源码，在内存加载；不使用工作区的四返回值 ABI 补丁。
- CUDA rasterizer：新取回 GRAPHDECO 原仓库，checkout 该 GS commit 引用的 59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d；源码 diff 为空。glm 也使用其 pinned submodule。
- 独立安装到 out/vrss/vendor/official_site，不改系统包或基线分支。视频强制加载此 kernel，无 RGB fallback。
- CUDA 12.6 首次编译因旧代码缺少 std::uintptr_t/uint32_t 声明失败；第二次仅给 NVCC 预包含 cstdint，未改 RGB 算法。两轮 build logs 均保留。
- 原码/内核 hashes、运行环境、实际 TRAIN 第 1 帧核验见 JSON。PASS；PSNR 28.30756 dB（uint8 resize 的固定诊断），与早期 SC-GS smoke 的 uint8 图像最大差为 0。这是该单帧一致性检查，不是所有视图逐像素等价声明。

## 可重建命令

在仓库根目录：
```
git clone https://github.com/graphdeco-inria/diff-gaussian-rasterization.git out/vrss/vendor/official_rasterizer
git -C out/vrss/vendor/official_rasterizer checkout 59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d
git -C out/vrss/vendor/official_rasterizer submodule update --init --depth 1
CUDA_HOME=/usr/local/cuda-12.6 PATH=/usr/local/cuda-12.6/bin:$PATH NVCC_PREPEND_FLAGS='--pre-include=cstdint' MAX_JOBS=2 TORCH_CUDA_ARCH_LIST=8.6 timeout 600 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m pip install --no-build-isolation --no-deps --target out/vrss/vendor/official_site ./out/vrss/vendor/official_rasterizer
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 timeout 120 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/run_vrss.py official-smoke
```

阶段拒绝覆盖已完成输出。重跑候选/evidence/select/render 时加 `--run-name chair_dev_replay`，输出仍在 out/vrss/ 下；所有阈值和输入不变。已保存的 smoke 不必重复覆盖，stock_rgb 每次渲染均核查 pinned source 和加载路径。

候选提取早于这次底层核验完成，但它从未用 RGB renderer：只用原有 GS G-buffer、vanilla 参数和 16 个 TRAIN 照片。更换 RGB 后没有修改 seed/pull/prune/chaining 源码或候选文件。新的 runner hash 与候选生成的 runner hash 不同；准许的是 RGB 接入/输出诊断修复，不是几何重生成或候选调参。
