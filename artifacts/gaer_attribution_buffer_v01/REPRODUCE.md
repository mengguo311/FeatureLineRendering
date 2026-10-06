# 重现已验证的原生缓冲区

在本服务器使用已有依赖，无需安装、全局配置修改或生产 renderer 替换：

```bash
cd /home/u00134/3dgs_line/gaer_attribution_buffer_v01
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B \
  experiments/gaer_attribution_buffer_v01/reproduce.py --benchmark
```

这条命令已经真实运行成功，receipt 为 `results/REPRODUCTION.json`，每步完整日志及唯一 receipt 位于其指向的 ignored `out/.../reproductions/`。省略 `--benchmark` 可只运行构建检查、垂直 API 测试、六个 CUDA 正确性/梯度/Adam 测试、四视图所有 K 的实际重渲染。测试失败会返回非零状态，不会用 stub 或跳过 GPU 来宣布通过。

`runtime.py` 把 process-local PATH 指向现有 vfsdgs/CUDA，限制 CPU affinity 和 Torch/BLAS/MAX_JOBS 为 2，固定 GPU0，并在每个 unit 前检查其他 GPU0 PID、4GiB root/1.5GiB common Git reserve/5GiB stage cap。发现别的 GPU0 工作会失败并保留证据，不杀任何任务。所有缓存、编译和临时文件在本阶段 ignored out 中。应在 GPU0 空闲时运行。

## 构建和来源

`build.py` 按 `PINNED_SOURCE.json` 逐文件验证实际 stock 源码，复制最小需要的源码及 GLM 到 scoped out；原版编译为 `gaer_original_C`，最小 patch 用 `patch --fuzz=0` 应用后编译为 `gaer_native_C`。CUDA source path 来自指定旧 adapter 的 runtime 字面路径。源码 commit 为 `59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d`，parent 3DGS commit 为 `472689c0dc70417448fb451bf529ae532d32c095`。需要本服务器已有的 pinned source、onec_stock_C binary、冻结 PLY 与相机 metadata；这些是只读外部输入，未随 Git 分发。

`TORCH_EXTENSIONS_DIR` 为 `out/gaer_attribution_buffer_v01/torch_extensions`，CUDA_HOME 为 `/usr/local/cuda`，sm_86，MAX_JOBS=2；参数沿用实际 `build/stock/build.ninja`，包括 `-include cstdint`，没有 fast-math。当前 Torch 为 2.3.1+cu121，compiler 为 CUDA 12.6。原始 Graphdeco license 原样保存在 `experiments/.../UPSTREAM_LICENSE.md` 与 isolated source 的 LICENSE.md。首次缺失 PATH 的 Ninja 故障通过使用已有 executable 修复，没有安装。

已有相同 source/patch build 会验证缓存与 binary hash，保持 canonical BUILD.json，不重新写 build 时长；检查 receipt 在 `out/.../last_rebuild.json`。不同 source/patch 不覆盖已有 build。原始 diff 缺少末尾换行的文件已使用正确 EOF marker。

## 单独执行和 API

```bash
PY=/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
$PY -B experiments/gaer_attribution_buffer_v01/build.py
$PY -B experiments/gaer_attribution_buffer_v01/tests/test_api_vertical.py
$PY -B experiments/gaer_attribution_buffer_v01/tests/test_native.py
$PY -B experiments/gaer_attribution_buffer_v01/verify_real.py
```

RED 历史测试命令使用 `GAER_TEST_BACKEND=actual`，在实际旧 stock 的真实 CUDA 输入上得到 `TypeError: unexpected keyword argument attribution`；`tdd/vertical_RED.log` 原样保留。不要把这条预期失败命令当作最终 GREEN 测试。

```python
import sys
sys.path.insert(0, 'experiments/gaer_attribution_buffer_v01/src')
from gaer_attribution import GaussianRasterizer, GaussianRasterizationSettings
renderer = GaussianRasterizer(settings)
rgb, radii = renderer(**model)  # stock 设置/参数；默认原 RGB autograd 路径
out = renderer(**model, attribution=True, K=8)
ids_cpu = out.gaussian_ids.cpu().numpy()       # int32 H,W,K
weights_cpu = out.gaussian_weights.cpu().numpy()  # float32 H,W,K
sum_all_cpu = out.all_contribution_sum.cpu().numpy()  # float32 H,W
T_cpu = out.final_T.cpu().numpy()             # float32 H,W
alpha = out.accumulated_alpha                # 1-final_T，非梯度输出
```

K 默认为 8，任意 Python int 1–32；仅启用时校验 K。只保留 RGB 接受的正 alpha*T，按权重降序；同权重保留原 depth traversal 次序。未用 ID=-1/weight=0。低层 `_C.rasterize_gaussians_attribution` 另外做 K/FP32 CUDA means3D/正图像尺寸校验。不要把 top-K sum 与完整 alpha 相等作为通过条件；all_contribution_sum 才累加所有接受项。诊断容差在 RED 后、GREEN 前固定为绝对 2e-6。RGB、梯度和一步 Adam 检查使用严格逐位相等。

## 真实数据、封存与性能

`CAMERA_FREEZE.json` 从完整 DATA_FREEZE 与实际 86 帧 transforms_train.json 文件名匹配得到 r_1、r_14；两场景实际 metadata index 为 1 和 12，分辨率为原始 800×800。原始 PLY 的所有行和完整 SH3 均加载，white background。真实 vanilla 没有公开 depth，记录 NOT_AVAILABLE。

首次生成每相机完整 native arrays、RGB/alpha/coverage/dominant ID 与 benchmark 的命令为：

```bash
$PY -B experiments/gaer_attribution_buffer_v01/run_real.py
```

已执行且四 unit 全部封存；相同 config 再执行会核对 hashes 并 SEALED_SKIP。原子 `.partial_*` 目录遇到失败会被保留；既有 sealed config 不匹配会明确失败，不覆盖唯一证据。`verify_real.py` 始终重新进行 GPU rendering，读取已保存 baseline float32 RGB，验证所有 K 和全部 seals。若在干净新输出目录重建 canonical views，必须具有相同 pinned read-only 输入；本次文件及其 hashes 不应为重跑而删除。

`--benchmark` 另执行 synthetic benchmark 和 `rebenchmark_real.py`，保留第一次各视图 canonical 测量，第二轮数字在 REBENCHMARK_REAL.json。5 warmup + 20 event-timed forward + synchronize；kernel 用另一轮 20 次 CUPTI profiler 测量；CPU 四 map copy 单独计时。每个 JSON 保留全部样本、median/p95 ms、median/p95/p05 FPS，以及 base/peak allocated/reserved。PNG、磁盘和 CPU copy 不进入 forward 计时。内存公式只计算实际 debug tensors，不伪装成 peak allocated。

数值证据、compact CPU JSON fixture、源代码函数行号和中文测量表在 `CPU_FIXTURE.json`、`SOURCE_LOCATIONS.json`、`REPORT_ZH.md`、`FINAL.json`。未来 caveats 只在 FUTURE_CAVEATS.md，没有算法实现。

## Git readback

发布使用显式 SSH，不改 origin HTTPS、不读 credentials。父级可独立比对：

```bash
git rev-parse HEAD
git ls-remote git@github.com:mengguo311/FeatureLineRendering.git \
  refs/heads/gaer-attribution-buffer-v01 refs/heads/image-space-edge-foundation-v1
git status --porcelain
```

任务分支 remote SHA 必须等于 HEAD；基准分支仍须为 `b2d562753de6759b1bb2d3ac2034b35dc080d025`。完成后的确切 SHA、readback、scoped commit 文件清单和 clean 状态保存到 ignored `out/gaer_attribution_buffer_v01/PUBLISH_RECEIPT.json`。FINAL.json 用 receipt 路径引用它，避免自身 commit hash 的循环引用。
