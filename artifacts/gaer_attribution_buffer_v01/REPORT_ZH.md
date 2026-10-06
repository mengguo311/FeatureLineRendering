# GAER 原生 attribution buffer v0.1 — 工程验证

已完成上传原文 section 25 FIRSTTASK，并在此停止。新增 opt-in 原生 CUDA top-K `T_before*alpha` 缓冲区；没有执行边检测、邻域分布差、Gaussian 边评分、移除因果实验、线/笔触渲染或协方差编辑。结果只支持缓冲区工程正确性，不验证 H1 或几何/时间语义。

## 来源和隔离

上传文件 681 行，原始字节 SHA256 为 `64b967ed51c335a4a50a160df516bd3685b6e068b41e078079a14456d9af86a9`。文件未修改，来源与启动提交见 `ORIGINAL_INSTRUCTIONS_SHA256.json`。工作基准为 `b2d562753de6759b1bb2d3ac2034b35dc080d025`，启动提交为 `20f6e4baa4f2c6c90319f8f030da0426154195ab`；目标分支仅 `gaer-attribution-buffer-v01`。

完整读取指定的 `native.py`、旧 `adapter.py` 及其 runtime 的字面路径，确认二者实际加载 `onec_stock_C.so`。源根为 `/home/u00134/3dgs_line/object_neighborhood_edge_control_v1/out/object_neighborhood_edge_control_v1/vendor/gaussian-splatting/submodules/diff-gaussian-rasterization`，rasterizer commit `59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d`，父 3DGS commit `472689c0dc70417448fb451bf529ae532d32c095`；446 个必要源码/GLM 文件的 SHA256 见 `PINNED_SOURCE.json`。源码集合 hash `dc29715803f624c5cff66150e81851c4a80023f71b404bbc02a065db112bd957`。历史 top32/RaDe patch 已检查并记录在 `REUSE_AUDIT.json`，未复用它的深度、法线或 renderer。

源码仅复制到忽略的 `out/gaer_attribution_buffer_v01/native/`；Git 只保存 8 文件的最小 patch、源码哈希、构建 recipe、上游原样 license 和验证证据。独立模块 `gaer_original_C` 与 `gaer_native_C` 使用同一现有 Python/Torch/CUDA 编译器，`MAX_JOBS=2`、sm_86、C++17，沿用实际 stock 编译参数，无 fast-math 或额外优化参数。未安装或覆盖生产模块。Python import 使用独立 `gaer_attribution` 接口。原 stock module、全部源文件、模型及 metadata 的前后 hash 均一致。

## 合成路径与 API

唯一修改的 CUDA 合成 kernel 是 `renderCUDA<3,true>`；关闭路径使用编译期 `renderCUDA<3,false>`。`preprocessCUDA`、排序/point_list、backward kernels 和 `ImageState/GeometryState/BinningState` 布局保留。补丁传递新增指针的函数包括 `FORWARD::render`、`CudaRasterizer::Rasterizer::forward` 和新增 `RasterizeGaussiansAttributionCUDA`。生成后函数/行号见 `SOURCE_LOCATIONS.json`：合成 kernel 起于 forward.cu:263，权重计算于 :367，dispatch 于 :408，C++ debug entry 于 rasterize_points.cu:119，Python debug autograd Function 于 __init__.py:263。

8 个 native 修改文件：`cuda_rasterizer/forward.cu`, `cuda_rasterizer/forward.h`, `cuda_rasterizer/rasterizer.h`, `cuda_rasterizer/rasterizer_impl.cu`, `diff_gaussian_rasterization/__init__.py`, `ext.cpp`, `rasterize_points.cu`, `rasterize_points.h`。实验 harness、测试、重现脚本在 `experiments/gaer_attribution_buffer_v01/`，无需 giant repo 或二进制提交。

```python
import sys
sys.path.insert(0, 'experiments/gaer_attribution_buffer_v01/src')
from gaer_attribution import GaussianRasterizer
renderer = GaussianRasterizer(settings)  # stock settings，full SH3 或 precomputed colors
rgb, radii = renderer(**model)           # 默认关闭，原返回值和 RGB autograd
out = renderer(**model, attribution=True, K=8)
ids = out.gaussian_ids.cpu().numpy()
weights = out.gaussian_weights.cpu().numpy()
alpha = out.accumulated_alpha            # 1 - out.final_T
```

`K` 默认 8，支持任意 Python int 1–32，包含 1/4/8/16；启用时拒绝负数、0、33、非整数及 bool。IDs 为 CUDA contiguous int32 `[H,W,K]`，原始 PLY/model 行编号；weights 为 float32 `[H,W,K]`，非归一化正的 alpha*T。未用槽为 ID=-1、weight=0。float32 `[H,W]` 的 `all_contribution_sum` 与 `final_T` 在 debug 开启时一并返回；dominant_id 为第一槽，accumulated_alpha 为 `1-T`。所有归因输出显式 `mark_non_differentiable`，RGB 保留梯度。

与 stock 完全相同的 power/filter、alpha clamp 0.99、alpha `<1/255` 跳过、`test_T<0.0001` 提前终止。在最后一种情况下，当前 splat 不进入 RGB、T 不更新，本缓冲区也不记录它。只在 RGB 接受后、T 更新前计算 `T*alpha`；从 `collected_id[j]` 获取 original ID。top-K 按实际权重降序，相等 FP32 权重保留已有深度遍历次序。直接对每像素输出槽进行插入，时间复杂度 O(accepted contributions × K)，没有 H×W×N 或 dense fallback，也没有额外 per-pixel 局部 K 数组。RGB backward 的 native ABI、十个 saved tensors 顺序及原始 RGB backward 方法保留。

stock 的 P=0 特例返回零 RGB 而非 background；本阶段保留该行为，同时归因数组初始化为 -1/0，sum=0、T=1。不要用这个空模型特例检查带背景的颜色重建公式。

## RED → GREEN 和梯度/训练验证

`tdd/vertical_RED.log` 在真实实际 stock CUDA 输入上得到缺失新参数的 TypeError；随后相同测试在隔离 native debug 路径通过，日志为 `vertical_GREEN.log`。`PROTOCOL_SEAL.json` 在看结果前固定 FP32 绝对容差 2e-6、RGB 逐位一致要求、测试 hash 与 RED hash，没有事后放宽。

六个 native 验证测试全部通过：中心精确 alpha*T、20 个贡献超过 K、前景遮挡与 opacity/真实权重反向排序、相等权重的稳定次序、alpha 临界值、0.99 clamp、近裁剪、被拒绝的终止 splat、空模型/空 tile、图像边界截断、K 前缀/质量单调、dtype/layout/CPU numpy、默认 8 和非法 K。`all_sum` 累加全部接受项后才检查 top-K；与独立乘积得到的 `1-T` 比较，未把截断 top-K 质量等同于完整 alpha。

actual stock、隔离 unmodified、debug OFF、debug ON：合成 RGB 最大误差 0、radii 一致；xyz、scales、quaternion、opacity、full SH3 或 precomputed color、means2D 梯度逐位一致，最大差值 0。损失是非平凡加权 RGB 二次项加颜色乘积，输入远离 clamp 不连续点，各有效参数组梯度非零。单像素选型避免多像素原子加法顺序噪声。真实 Adam 一步比较了梯度、更新参数及 optimizer state；额外 raw 模型测试使用 log-scale、opacity logit、归一化 quaternion、SH DC/rest，原版/OFF/ON 更新均逐位相同。这些是已测 fixture 的结论，不声称对所有训练任务做过穷尽测试。详见 `results/NATIVE_TESTS.json`。

## 原始模型与四个 800×800 视图

Lego 原始 30k PLY：310,475 个 Gaussian，SHA256 `fa9bea3fa4f8d349fa873a66d892c53cd1263499caec6421c286350a5bb7cbbc`；Chair：256,690 个，SHA256 `13e4ecc9ffe9c5ae2a0656e2e5c56a737cfdc90a62ad04799db3c46b0b442f5d`。两者均保留 16×3 SH3 系数与所有 model 行。摄像机 r_1/r_14 从 DATA_FREEZE 的冻结文件名匹配实际 transforms_train.json；它是 86 帧子集，r_14 的 metadata 行号为 12，不能用 14 直接取行。四个 w2c 与冻结记录 float64 最大误差均为 0；原始图片确为 800×800。

每视图保存 baseline、patched OFF、patched ON 的 PNG 与原始 float32 RGB，native IDs/weights、all_sum/T、alpha/coverage/missing_mass、dominant ID；原始完整数值位于忽略的 `out/.../views/`，由原子目录批次和 `seals/*.json` 封存。tracked 四张小 panel 的顺序为 RGB、dominant ID、alpha、coverage。实际 vanilla 没有公开 depth 输出，状态为 **NOT_AVAILABLE**，未发明 proxy depth。

四视图实际 stock / 隔离原版 / OFF / ON 的 RGB 都逐位相同、最大误差 0。独立 `verify_real.py` 又在全部视图和 K=1/4/8/16 上实际重渲染，验证 RGB、精确前缀、非负权重、质量单调、K 不影响 all_sum/T，以及原始输入和输出 seals。K=8 统计：

| 视图 | max |all_sum-(1-T)| | 全图 top-K/alpha | alpha>0 像素均值 coverage | missing mass 全图均值 | missing mass 最大值 |
| --- | --- | --- | --- | --- | --- |
| lego_r_001 | 1.07e-06 | 0.81214 | 0.81499 | 0.04985 | 0.86427 |
| lego_r_014 | 1.19e-06 | 0.80783 | 0.80968 | 0.06533 | 0.91068 |
| chair_r_001 | 7.15e-07 | 0.76304 | 0.76935 | 0.05150 | 0.73982 |
| chair_r_014 | 8.34e-07 | 0.78846 | 0.79715 | 0.05187 | 0.73375 |


全图比例是 `sum(top-Kmass)/sum(alpha)`，像素 coverage 是 `top-Kmass/alpha`（alpha=0 处定义为 0）；missing_mass=`alpha-top-Kmass`，原始数值保留 FP32 舍入误差。top-K 缺失项不代表真实零贡献。完整质量检查上限 1.1920929e-06 < 2e-6。

## 实测内存与性能

RTX A6000 GPU0，PyTorch 2.3.1+cu121，现有 CUDA 12.6 compiler，CPU affinity 两核。每 unit 检查 GPU0 所有进程，拒绝其他占用而不终止任务；固定 root 4GiB、common Git 1.5GiB reserve 与 stage 5GiB cap。资源记录在忽略的 `logs/resource_checks.jsonl`。

800×800 输出张量的实际 numel×element_size 字节数（非估计峰值）：

| K | IDs+weights bytes | sum+T bytes | debug 总 bytes | MiB |
| --- | --- | --- | --- | --- |
| 1 | 5,120,000 | 5,120,000 | 10,240,000 | 9.76562 |
| 4 | 20,480,000 | 5,120,000 | 25,600,000 | 24.41406 |
| 8 | 40,960,000 | 5,120,000 | 46,080,000 | 43.94531 |
| 16 | 81,920,000 | 5,120,000 | 87,040,000 | 83.00781 |


只算 IDs/weights 为 H×W×K×(4+4)，两张 debug map 再加 H×W×8。alpha 是调用方 `1-T` 派生 map；coverage、missing_mass、图片和 CPU 临时数组不属于 native API 的上述容量。

每场景/相机/参数完全相同，5 次 warmup、20 次 CUDA event 完整 forward、显式 synchronize；另记录 wall 时间与全部样本。CUDA event 完整 forward 包含本 renderer 内部 host prefix readback/调度产生的 GPU 空档。compositor kernel 用独立 20 次 torch.profiler CUDA/CUPTI pass 获取，因 profiler instrumentation 单独标记，不混入主 forward 数字。CPU copy 是另行 20 次把四张 debug 输出转 CPU，包含 pageable CPU 分配；不含磁盘 PNG IO。FPS 的 p95 是 1000/ms 样本的 p95，另在 JSON 记录保守 p05 FPS。

| 视图 | 模式 | forward median ms | p95 ms | median FPS | p95 FPS | kernel median ms | p95 ms | median FPS | p95 FPS | forward peak Δallocated MiB | CPU copy median ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lego_r_001 | actual_stock | 2.4879 | 2.6760 | 401.9 | 416.6 | 1.5470 | 1.7208 | 646.4 | 702.4 | 107.88 | - |
| lego_r_001 | isolated_original | 2.5870 | 2.7551 | 386.5 | 406.7 | 1.5245 | 1.6591 | 656.0 | 685.0 | 107.88 | - |
| lego_r_001 | debug_off | 2.5827 | 2.7289 | 387.2 | 409.7 | 1.5240 | 1.6279 | 656.2 | 690.3 | 107.88 | - |
| lego_r_001 | K1 | 2.8302 | 3.0285 | 353.3 | 365.3 | 1.7200 | 1.9309 | 581.4 | 608.0 | 117.64 | 2.73 |
| lego_r_001 | K4 | 3.2431 | 3.3289 | 308.3 | 320.6 | 2.0660 | 2.1731 | 484.0 | 503.6 | 132.76 | 5.58 |
| lego_r_001 | K8 | 3.7748 | 3.8633 | 264.9 | 270.1 | 2.6285 | 2.7134 | 380.4 | 387.8 | 152.29 | 39.86 |
| lego_r_001 | K16 | 5.6529 | 5.7991 | 176.9 | 180.1 | 4.2715 | 4.4045 | 234.1 | 238.0 | 190.88 | 64.07 |
| lego_r_014 | actual_stock | 2.5918 | 2.6591 | 385.8 | 388.8 | 1.4040 | 1.4325 | 712.3 | 733.2 | 122.35 | - |
| lego_r_014 | isolated_original | 2.6968 | 2.7927 | 370.8 | 374.4 | 1.5010 | 1.5311 | 666.2 | 675.0 | 122.35 | - |
| lego_r_014 | debug_off | 2.6900 | 2.7404 | 371.8 | 377.2 | 1.5000 | 1.6057 | 666.7 | 686.3 | 122.35 | - |
| lego_r_014 | K1 | 2.9303 | 3.0698 | 341.3 | 346.7 | 1.7010 | 1.7824 | 587.9 | 601.7 | 132.11 | 2.87 |
| lego_r_014 | K4 | 3.2266 | 3.2672 | 309.9 | 313.5 | 1.9735 | 2.0438 | 506.7 | 518.7 | 147.23 | 5.63 |
| lego_r_014 | K8 | 3.6916 | 3.7903 | 270.9 | 274.5 | 2.4370 | 2.4911 | 410.3 | 418.4 | 166.76 | 39.48 |
| lego_r_014 | K16 | 5.6298 | 5.7701 | 177.6 | 179.9 | 4.3735 | 4.4551 | 228.7 | 232.7 | 205.36 | 64.51 |
| chair_r_001 | actual_stock | 2.0187 | 2.1439 | 495.4 | 514.2 | 1.1830 | 1.2620 | 845.6 | 910.1 | 82.84 | - |
| chair_r_001 | isolated_original | 2.0287 | 2.1620 | 492.9 | 510.9 | 1.1665 | 1.2823 | 857.3 | 897.8 | 82.84 | - |
| chair_r_001 | debug_off | 2.0251 | 2.1120 | 493.8 | 508.3 | 1.1810 | 1.2386 | 846.7 | 879.4 | 82.84 | - |
| chair_r_001 | K1 | 2.2506 | 2.3719 | 444.3 | 456.4 | 1.3205 | 1.4292 | 757.3 | 790.2 | 93.10 | 2.89 |
| chair_r_001 | K4 | 2.4704 | 2.5676 | 404.8 | 413.8 | 1.5850 | 1.7727 | 630.9 | 659.4 | 107.56 | 5.66 |
| chair_r_001 | K8 | 2.9151 | 3.0361 | 343.0 | 349.2 | 1.9780 | 2.0531 | 505.6 | 515.3 | 127.09 | 38.66 |
| chair_r_001 | K16 | 4.4923 | 4.6302 | 222.6 | 230.8 | 3.5235 | 3.6431 | 283.8 | 288.7 | 166.34 | 64.72 |
| chair_r_014 | actual_stock | 1.9055 | 2.0142 | 524.8 | 547.4 | 1.0640 | 1.0993 | 939.8 | 989.4 | 83.51 | - |
| chair_r_014 | isolated_original | 1.9732 | 2.0707 | 506.8 | 518.2 | 1.1285 | 1.2034 | 886.2 | 915.1 | 83.51 | - |
| chair_r_014 | debug_off | 1.9704 | 2.0803 | 507.5 | 527.0 | 1.1250 | 1.2370 | 888.9 | 935.6 | 83.51 | - |
| chair_r_014 | K1 | 2.2986 | 2.4425 | 435.1 | 459.4 | 1.3155 | 1.4002 | 760.2 | 785.1 | 93.77 | 2.60 |
| chair_r_014 | K4 | 2.6049 | 2.6930 | 383.9 | 390.5 | 1.7160 | 1.8585 | 582.8 | 607.1 | 108.23 | 5.66 |
| chair_r_014 | K8 | 3.2422 | 3.3033 | 308.4 | 316.0 | 2.3385 | 2.4002 | 427.6 | 436.6 | 127.76 | 41.27 |
| chair_r_014 | K16 | 5.2936 | 5.4298 | 188.9 | 194.5 | 4.4050 | 4.5408 | 227.0 | 236.0 | 167.01 | 64.70 |


K=8 对 actual stock 的 forward 中位开销分别为 lego_r_001 51.7%, lego_r_014 42.4%, chair_r_001 44.4%, chair_r_014 70.1%。OFF 相对 actual 的微小实测差异也已列出，没有宣称零性能开销。O(K) 插入开销随 K 增大；当前实现以正确性为目标，没有进入后续 runtime 优化阶段。

上述 peak Δallocated 为 `max_memory_allocated - base_allocated`，重置峰值后实际运行一次 native forward，包含 RGB/radii、debug 输出和原始排序/几何临时 workspace；不是公式推算。输出 byte 总数与 allocator 峰值差别来自分配颗粒及 workspace。例 Lego r_001 的 allocator 数字：

| 模式 | base allocated MiB | peak allocated MiB | base reserved MiB | peak reserved MiB |
| --- | --- | --- | --- | --- |
| actual_stock | 92.51 | 200.39 | 296.00 | 296.00 |
| isolated_original | 92.51 | 200.39 | 296.00 | 296.00 |
| debug_off | 92.51 | 200.39 | 296.00 | 296.00 |
| K1 | 92.51 | 210.15 | 296.00 | 296.00 |
| K4 | 92.51 | 225.27 | 296.00 | 296.00 |
| K8 | 92.51 | 244.80 | 296.00 | 296.00 |
| K16 | 92.51 | 283.40 | 364.00 | 364.00 |


allocated 是活跃 tensor/workspace，reserved 是 PyTorch cache；reserved 依赖固定执行顺序与缓存历史，未当作实际额外 tensor 容量。其他视图同类原始值均在各 unit JSON。没有 H×W×N 的储存。

同一 20-Gaussian 单像素解析 fixture、相机准备位于计时外的性能：

| 模式 | forward median ms | p95 ms | median FPS | p95 FPS | kernel median ms | p95 ms |
| --- | --- | --- | --- | --- | --- | --- |
| actual_stock | 0.19202 | 0.23091 | 5208.2 | 5344.6 | 0.00600 | 0.00600 |
| isolated_original | 0.24258 | 0.29625 | 4122.5 | 4250.4 | 0.00600 | 0.00600 |
| debug_off | 0.25331 | 0.29916 | 3947.7 | 4072.2 | 0.00600 | 0.00600 |
| K1 | 0.31904 | 0.37285 | 3134.5 | 3211.1 | 0.00700 | 0.00700 |
| K4 | 0.32197 | 0.37966 | 3105.9 | 3182.6 | 0.01000 | 0.01000 |
| K8 | 0.31819 | 0.37056 | 3142.8 | 3213.4 | 0.01400 | 0.01400 |
| K16 | 0.31179 | 0.35774 | 3207.3 | 3267.1 | 0.02200 | 0.02200 |


`reproduce.py --benchmark` 已真实执行一次，重建检查、垂直 API、六个 native checks、四视图四个 K 重渲染及完整 benchmark 重复均通过，receipt 见 `results/REPRODUCTION.json`；独立第二次 real 性能在 `results/REBENCHMARK_REAL.json`，保留首次 canonical 结果以展示测量差异。已解决的 PATH/EOF/profiler API/metadata 匹配问题见 `FAILURE_STATES.json`，无现存 blocker 或数值失败。初次完整命令行进程检查意外显示了无关敏感参数；后续检查仅 UUID/PID，Git 交付不含原始进程输出、agent 日志或该敏感值，事件已在同一审计文件说明。

## 科学边界与交付

alpha*T top-K 与多邻居 raster state 机制和 [Hao/Mukai SA2026 作者预印本](https://mukai-lab.org/content/SA2026PosterHao.pdf) §2 重合，不作新颖性声明。未实现论文或上传文档的后续边算法。归一化 L1/支持重叠关系、脊线处 grad(E) 可能为零、top-K 未保留项的未知质量、删除导致 T/空洞变化，以及背景/SH 色彩影响仅写在 `FUTURE_CAVEATS.md`。

`REPRODUCE.md` 给出实际使用的单命令 recipe；`FINAL.json` 汇总 source/patch/module hashes、API、内存、性能、测试与 failure state。仅提交本阶段 experiments/artifacts，ignored out 保留 full arrays、builds、资源/重现日志和 push readback receipt；不提交模型、CUDA dependencies 或 raw agent logs。发布目标为 SSH `git@github.com:mengguo311/FeatureLineRendering.git` 的 `refs/heads/gaer-attribution-buffer-v01`，最终 commit/readback/clean 证明写入 `out/gaer_attribution_buffer_v01/PUBLISH_RECEIPT.json`，避免把自身 commit hash 写入自身内容的循环依赖。基准分支保持原 SHA。
