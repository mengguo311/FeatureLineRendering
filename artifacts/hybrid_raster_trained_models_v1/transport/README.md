# 四场景冻结 NPR transport：复现与产物索引

本目录只封装既有 v2 科学计算。hotdog、materials、mic、ship 各固定 8F + 8C + 33 arc，共49帧；四场景合计196帧。先以 seed1729、30000次标准 vanilla3DGS 光度训练获得模型，再冻结 checkpoint 与精确相机，最后执行 NPR。C 本身属于 GS TRAIN，**只对 NPR 参数拟合留出，绝不是盲测或训练外泛化评估**。本轮 NPR 完全不重新拟合。

`SOURCE_MANIFEST.json` 固定 producer、相机适配器及其测试的源码哈希。`summarize_results.py` 是另行跟踪的离线报告汇总器，既不参与 producer，也不改变任何科学参数或生成图像。`REVIEW_PLAN.json` 预声明固定评审路径；路径出现不代表实际产物已经存在。

## 冻结科学来源

旧目录 `/home/u00134/3dgs_line/hybrid_raster_evidence_v2` 及其六个锁定源码、patched/unpatched 原生二进制均只读。每次生产核验旧源码、二进制和 LOCK；旧文件 SHA256 为 `d5ec038e8ebc8a7160bc9e31ebb6ac8ce755fdbf1677a32ad55102a48c6a0926`，科学 parameter hash 为 `6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9`。

A 是既定灰度 RGB、median-depth、alpha 边缘；B 是 OUR dense 六通道读出；C 是 `1-(1-A)*(1-B)`。AUTHOR 是 Hao–Mukai Eq.1–5 的独立重建，**NOT official**，固定作者增益分母，另存原始 `S_L`。所有臂共用同一次 native traversal 的白背景 SH0 RGB；vanilla训练可为 fullSH3，NPR按继承约定只读 SH0。缺少训练时 filter3D；原生 splat/ray-plane normals 不是表面真值法线。墨量和支持增加均不等于更多有用线条，不作 fixed3D 或时序收益声明。

F=`[1,14,27,41,53,67,79,93]`，C=`[7,21,33,47,59,73,86,99]`。`PREDECLARED_CAMERAS.json` 在 GPU 前记录准确 F/C 相机和目标 checkpoint 路径：800×800，主点399.5，Materials 使用其自身 FoV。arc 固定 C7→C33、33个不同 pose；严格采用旧球面位置插值、线性半径及旋转 Slerp。中心由30000次 checkpoint 的 float64 坐标 .001/.999 分位边界均值确定。训练完成后先把全部精确 arc pose 写入 `CAMERAS.json` 并 commit/push，再渲染。

## 执行顺序

所有命令从授权 worktree 运行，解释器为 `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`。设置 `PYTHONDONTWRITEBYTECODE=1`，缓存、TMP、日志均写本轮授权输出。磁盘、训练和 freeze 条件由根任务协议管理。

1. GPU 前：`adapters.py --predeclare` 只读 TRAIN 元数据及 F1 PNG 24字节尺寸头；不解码数据集图像。协议、训练输入清单和相机声明先 commit/push。
2. 完成 vanilla acquisition 后：对每个场景运行 `adapters.py --resolve SCENE`。它要求 `CHECKPOINT_LOCK.json` 状态 COMPLETE、seed1729、30000次、7000和30000两套 checkpoint 记录，核对最终 PLY 路径与 SHA、训练 manifest 和 TRAIN syscall audit。
3. commit/push 四个 `transport/SCENE/CAMERAS.json`。写入 `transport/RENDER_FREEZE.json`：`{"commit":"已推送冻结SHA","camera_manifest_sha256":{"hotdog":"...","materials":"...","mic":"...","ship":"..."}}`。producer 会逐文件核对该提交内容，并检查冻结提交位于当前远端分支历史中。
4. 全部 acquisition 停止后串行运行四场景 `run_transport.py --phase render --scene SCENE`。通过 `strace -f -q -yy -s 4096 -e trace=open,openat,openat2,creat` 包裹实际进程，将 trace/标准输出写本轮日志。保留旧 native GPU guard：每次 render 查询 nvidia-smi 和 PID 归属，任何其他 GPU compute PID 均拒绝启动，不修改 guard、不重叠外来作业。
5. 每场景运行 `run_transport.py --phase media --scene SCENE`。此阶段仅编码已有输出，不启动 renderer。
6. 执行独立 verifier 的实际产物、完整视频解码与访问审计。最后运行 `summarize_results.py` 生成 `transport/DIAGNOSTIC_SUMMARY.json`，按 `REVIEW_PLAN.json` 检查固定代表帧和完整 contact sheets。

默认四场景示意命令（scene逐个执行，freeze和设备占用检查必须已经满足）：

```bash
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/hybrid_raster_trained_models_v1/transport/adapters.py --resolve hotdog
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/hybrid_raster_trained_models_v1/transport/run_transport.py --phase render --scene hotdog
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/hybrid_raster_trained_models_v1/transport/run_transport.py --phase media --scene hotdog
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/hybrid_raster_trained_models_v1/transport/summarize_results.py
```

render 前先对每场景全部8F做 patched/unpatched 校准。一般字段 max_abs≤3e-6；depth/median-depth 另允许 max_abs≤1e-5 且 max_rel≤3e-6。两版数组、SHA和逐字段误差均保留；未通过记 ENGINEERING_INVALID，不能解释为科学负结果。8F只做校准与固定参数渲染，不承担新尺度拟合。

## 路径与数据结构

| 路径（相对本轮 transport） | 内容 |
|---|---|
| artifacts `SCENE/CAMERAS.json` | 精确 checkpoint lineage、F/C/arc49个相机、中心、预声明哈希 |
| artifacts `SCENE/CALIBRATION.json` | 8F同输入两版校准、误差、两版 NPZ 路径和 SHA |
| out `calibration/SCENE/F_001.npz` | patched原始输出；同目录 `_unpatched.npz` 为对应基线 |
| out `raw/SCENE/KEY/` | `native.npz`、camera、checkpoint qualification、seal |
| out `frames/SCENE/KEY/` | native、typed、responses、provenance、diagnostics、PNG、seal |
| artifacts `SCENE/FRAMES.json` | 49个 frame 的 context、seal SHA 和精确计数 |
| out `media/SCENE/` | 六个视频、15张contact、九张首中末panel、媒体manifest与seal |
| artifacts `SCENE/MEDIA.json` | 每个视频全解码33帧/33 distinct/尺寸/SHA，contact和首中末路径 |
| out `RUNTIME.json` | 逐进程阶段、PID、墙钟、失败原因；GPU阶段合计限制4小时 |
| artifacts `STATUS.json` | transport进度；同步更新本轮顶层STATUS |

KEY 是 `F_001` 等8个 F、`C_007` 等8个 C，以及 `arc0_000`…`arc0_032`。帧的 `SEAL.json` 绑定完整 camera、checkpoint、继承科学哈希、封装源码哈希及每个 payload SHA；`SEAL.sha256` 绑定 seal 本体。写 staging、完成所有输出后原子发布。已有损坏、部分或上下文不同的产物拒绝静默覆盖；只有完整匹配 seal 才能恢复跳过。

`native.npz` 保存原始 Gaussian 行 ID、未归一化 alpha*T top4 权重、对应 depth/normal、RGB、alpha、depth/median-depth、normal、moment2、normal_len。`typed.npz` 保存作者原值和几何/贡献统计；`responses.npz` 保存 A/B/C、逐通道、作者原值/固定增益、三臂等连续墨量结果；`provenance.npz` 保存 A-only/B-only/shared、连续 overlap、B argmax/channel bits、A channel bits 与 foreground。raw ID、空槽、排序、贡献质量和有限性检查全部继承。

`line_panel.png`、`overlay_panel.png`、`matched_panel.png` 均为五列4000×832，原图800×800不裁切。顺序 RGB | A | B | C | AUTHOR。matched仅对 A/B/C 等墨量缩放；AUTHOR仍是固定增益，标签明示不参与匹配。每帧还保留单臂 ink/overlay、作者 absolute/gain 和 response panel。

每场景有 native comparison/overlay/matched 三个视频，及对应 `_telegram1600.mp4` 三个版本。native尺寸4000×832；Telegram1600×368、H264/yuv420p/faststart，并在1600宽版本重新绘制标签。全部保留33帧、12fps、33个不同解码帧，不挑帧、不静态动画。contact按 F/C/arc × RGB/A/B/C/AUTHOR 共15张；固定首中末000/016/032 × line/overlay/matched 共九张。

## 报告汇总与人类评审

`summarize_results.py` 只读取封存 diagnostics/provenance 和 manifest，不读取数据集源 RGB、TEST或mesh，不调用 renderer、不计算新 normalization。按 F/C/arc/all 汇总 A/B/C 连续墨量、非零支持、背景/轮廓/内部区域诊断、B-only argmax通道计数与 top4 coverage。coverage给出像素数加权均值；每帧P05的均值/最小值明确不是 pooled-pixel P05。各组是图像统计，不是独立样本推断。

汇总器检查 seal 封套、文件清单存在性和实际消费 payload 哈希；它不冒充完整独立 verifier，不重复解码所有图像/视频。数量不完整或损坏时报告 PARTIAL_OR_INVALID 并退出2；不能将缺失场景当作空集合成功。质量结论始终依赖实际检查，不能把更多墨量、更多B-only像素或某通道占比直接解释为优越。

固定检查 F1/F41、C7/C47、arc首/中/末，并提供所有C与完整arc contact。中文报告应逐场景描述真实可见的内部密纹、碎线、轮廓、细结构遮挡或训练缺陷；Materials等反光/折射误差应如实披露。实现代理检查不等于独立 human GO，最终人类 review 保留 pending。
