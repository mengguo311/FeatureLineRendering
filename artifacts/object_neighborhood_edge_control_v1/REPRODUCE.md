# 重现与恢复

在本分支工作区运行，旧 TEST 与旧 checkpoint 从不作为输入。大产物只在 `out/object_neighborhood_edge_control_v1`。公共磁盘至少留 1.5GiB、根盘留 4GiB，新 stage 不超过 16GiB；GPU0 外来进程会让 runner 等待。运行配置的 seed=1729、24/6/12、512×512、原生 GS 7000 次迭代与 336 次局部控制属于 pilot。

本工作区已打开高对比 TEST，不能再用训练命令重建它。已完成单元恢复只校验/跳过封印，或重复只读评分：

```bash
cd /home/u00134/3dgs_line/object_neighborhood_edge_control_v1
export CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
research_python=/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/heldout_runner.py
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/runner.py --scenes panels_low
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/far_readonly.py
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/deliver.py
cat artifacts/object_neighborhood_edge_control_v1/FINAL.json
```

从空的新 stage 复现训练，必须创建独立副本并使用 TEST 前代码版本。以下只共享 Git 对象，不复制旧模型/数据，不启用完整 checkout；不要在当前目录移除 TEST seal：

```bash
source_checkout=/home/u00134/3dgs_line/object_neighborhood_edge_control_v1
replica_checkout=/home/u00134/3dgs_line/object_neighborhood_edge_control_v1_reproduction
git clone --shared --no-checkout "$source_checkout" "$replica_checkout"
git -C "$replica_checkout" sparse-checkout init --cone
git -C "$replica_checkout" sparse-checkout set artifacts/object_neighborhood_edge_control_v1 experiments/object_neighborhood_edge_control_v1
git -C "$replica_checkout" checkout --detach 305952e353a767afa72cef1a448031873c122476
cd "$replica_checkout"
```

然后在该副本里执行（现有冻结合成数据会只核查、不会覆盖）：

```bash
bash experiments/object_neighborhood_edge_control_v1/scripts/bootstrap.sh
export CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
export PYTHONPATH="$PWD/experiments/object_neighborhood_edge_control_v1/src:$PWD/out/object_neighborhood_edge_control_v1/deps"
research_python=/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
"$research_python" -m unittest discover -s experiments/object_neighborhood_edge_control_v1/tests -v
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/generate_scenes.py
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/runner.py --scenes panels_high
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/budget_curves.py
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/refresh_coverage.py
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/run_diagnostics.py
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/freeze_test.py --scenes panels_high
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/heldout_runner.py
```

源码仓库、CUDA submodule、许可证和精确参数绑定在 `source_bindings/upstream.json`。扩展通过本地 JIT 构建，Ninja/FFmpeg/FLIP 通过 `--target` 安装在本 stage；现有 Python 环境、全局配置和既有扩展不改。LPIPS 读取既有公开 AlexNet 权重；若不存在，下载到新 stage 的 cache，记录权重 SHA。

runner 必须单实例。它会核对已封印输出的 SHA，跳过完成单元，并将当前工作写到 `STATUS.json`；失败单元在同一数据/config 下可从头重跑，已成功模型不会重训练。单元不是无训练占位进程，封印指向实际 checkpoint、指标与日志 hash。生产进程用 `subprocess.Popen(start_new_session=True, stdin=DEVNULL)` 启动，PID 在 out 的 runner.pid；coding agent 退出不会结束该进程。禁止为恢复杀掉其他 tmux、Claude 或 GPU job。

低对比、远背景扩展只有在高对比 pilot 的完整闭环可核查后运行。以下是原生产命令，远背景 C1 实际发生证书拒绝，不能预期它成功完成：

```bash
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/runner.py --scenes panels_low far_background
```

远背景错误区间跨越 ε=0.02，配置未放宽、源码未修补；`far_readonly.py` 仅继续原模型 B0 评分与原 C0 数学诊断，不绕过 C1，也不封印失败单元。恢复当前交付应使用开头的只读命令。预算曲线必须在新副本打开 TEST **之前**运行。

本次 TEST 打开后，同场景的训练/选择/控制入口会拒绝覆盖。不能把恢复命令用于 TEST 后调参；需要复现训练时，应在新的隔离 checkout/out 路径重建同样输入，而不是移除本次 TEST seal 来继续调参。

只读评分与交付程序的完整实际命令、执行状态在结果 manifests/unit seals 中。TEST/path evaluator 先验证冻结 checkpoint 与评价源码 SHA，随后才读 TEST 目标。路径视频从所有已渲染 PNG 编码为 H264/yuv420p/faststart，另逐帧完整解码、检验实际帧数、不同相机与 decoded frame SHA。任务 A 的时间残差仅用评价器中的 GT 表面点和遮挡深度重投影；没有从训练器回读几何 oracle。

```bash
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/evaluate.py panels_high B1 --split test
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/evaluate.py panels_high B1 --split path
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/temporal.py panels_high B1
"$research_python" experiments/object_neighborhood_edge_control_v1/scripts/make_video.py panels_high B1
```

上述只读评分命令需要实际存在的 `test_freeze.json` 和对应模型，不应在验证未完成时手工提前打开 TEST。最终可运行状态、未完成项与可继续范围以 `FINAL.json` 与 `REPORT_ZH.md` 为准。
